# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime
from xml.etree import ElementTree as ET

from odoo import models
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        """Parse MTBank XML statement file format."""
        try:
            root = ET.fromstring(data_file)
            # Check if this is MTBank format
            if root.tag == "Export" and root.find(".//StatementByDay") is not None:
                return self._parse_mtbank_xml(root)
        except ET.ParseError as error:
            _logger.debug("Not a valid XML file: %s", error)
        return super()._parse_file(data_file)

    def _parse_mtbank_xml(self, root):
        """
        Parse MTBank XML format.

        Structure:
        Export/StatementAnswer/StatementBy/StatementByDay/StatementByDayRow

        Each StatementByDayRow contains:
        - Account: bank account number (BY IBAN)
        - CurrIso: currency code (BYN, USD, EUR, etc.)
        - OpeningBalance/ClosingBalance: balances
        - OpeningBalanceDate/ClosingBalanceDate: dates (DD/MM/YYYY)
        - DEBETTURNOVER/CREDITTURNOVER: transaction totals
        - DEBETDOCUMENTSCNT/CREDITDOCUMENTSCNT: document counts

        A row covers a period, not necessarily a single day, and periods may
        overlap (e.g. a whole-month row next to weekly rows).
        """
        statement_by_day = root.find(".//StatementByDay")
        if statement_by_day is None:
            raise UserError(
                self.env._("Invalid MTBank XML file: StatementByDay not found")
            )

        rows = statement_by_day.findall("StatementByDayRow")
        if not rows:
            raise UserError(self.env._("No statement data found in MTBank XML file"))

        # Group rows by account
        accounts_data = {}
        for row in rows:
            account = self._get_xml_text(row, "Account")
            if not account:
                continue

            if account not in accounts_data:
                accounts_data[account] = {
                    "currency": self._get_xml_text(row, "CurrIso"),
                    "rows": [],
                }
            accounts_data[account]["rows"].append(row)

        # Parse each account's data
        result = []
        for account, data in accounts_data.items():
            result.append(self._parse_mtbank_account(account, data))

        return result

    def _parse_mtbank_account(self, account_number, data):
        """Parse statement data for a single account."""
        currency_code = data["currency"]
        rows = data["rows"]

        # Sort rows by closing date. Rows are periods that may overlap, so the
        # opening balance of a row is deliberately not checked against the
        # closing balance of the preceding one.
        rows.sort(
            key=lambda r: self._parse_mtbank_date(
                self._get_xml_text(r, "ClosingBalanceDate"), "ClosingBalanceDate"
            )
        )

        transactions = []
        balance_start = None
        balance_end = None
        statement_date = None

        for row in rows:
            opening_date = self._parse_mtbank_date(
                self._get_xml_text(row, "OpeningBalanceDate"), "OpeningBalanceDate"
            )
            closing_date = self._parse_mtbank_date(
                self._get_xml_text(row, "ClosingBalanceDate"), "ClosingBalanceDate"
            )
            opening_balance = float(self._get_xml_text(row, "OpeningBalance") or 0)
            closing_balance = float(self._get_xml_text(row, "ClosingBalance") or 0)
            debit_turnover = float(self._get_xml_text(row, "DEBETTURNOVER") or 0)
            credit_turnover = float(self._get_xml_text(row, "CREDITTURNOVER") or 0)
            debit_count = int(self._get_xml_text(row, "DEBETDOCUMENTSCNT") or 0)
            credit_count = int(self._get_xml_text(row, "CREDITDOCUMENTSCNT") or 0)

            # The balances of a period must match its turnovers
            expected_closing = opening_balance + credit_turnover - debit_turnover
            if float_compare(expected_closing, closing_balance, precision_digits=2):
                raise UserError(
                    self.env._(
                        "MTBank statement for %(account)s: closing balance of "
                        "the period from %(start)s to %(end)s does not match "
                        "its turnovers: expected %(expected)s, got "
                        "%(actual)s.",
                        account=account_number,
                        start=opening_date.strftime("%d/%m/%Y"),
                        end=closing_date.strftime("%d/%m/%Y"),
                        expected=f"{expected_closing:.2f}",
                        actual=f"{closing_balance:.2f}",
                    )
                )

            # Set starting balance from first row
            if balance_start is None:
                balance_start = opening_balance

            # Update ending balance
            balance_end = closing_balance
            statement_date = closing_date

            # Create transactions for debit and credit if there are movements
            if debit_count > 0 and debit_turnover != 0:
                transactions.append(
                    {
                        "date": closing_date,
                        "payment_ref": self.env._(
                            "Debit transactions (%(count)s)", count=debit_count
                        ),
                        "amount": -abs(debit_turnover),  # Debit is negative
                        "unique_import_id": (
                            f"{account_number}-{closing_date.strftime('%Y%m%d')}-DEBIT"
                        ),
                    }
                )

            if credit_count > 0 and credit_turnover != 0:
                transactions.append(
                    {
                        "date": closing_date,
                        "payment_ref": self.env._(
                            "Credit transactions (%(count)s)", count=credit_count
                        ),
                        "amount": abs(credit_turnover),  # Credit is positive
                        "unique_import_id": (
                            f"{account_number}-{closing_date.strftime('%Y%m%d')}-CREDIT"
                        ),
                    }
                )

        # The movements must reconcile the statement balances. This also
        # rejects files whose overlapping periods would count a turnover
        # twice.
        expected_end = balance_start + sum(t["amount"] for t in transactions)
        if float_compare(expected_end, balance_end, precision_digits=2):
            raise UserError(
                self.env._(
                    "MTBank statement for %(account)s: the movements do not "
                    "reconcile the balances: starting balance %(start)s plus "
                    "the movements of the file gives %(expected)s, but the "
                    "closing balance is %(actual)s (difference %(diff)s).",
                    account=account_number,
                    start=f"{balance_start:.2f}",
                    expected=f"{expected_end:.2f}",
                    actual=f"{balance_end:.2f}",
                    diff=f"{balance_end - expected_end:.2f}",
                )
            )

        # The de-duplication of account_statement_import_file silently drops
        # the transactions whose unique_import_id was already imported, so a
        # period re-issued by the bank with a corrected amount has to be
        # reported here.
        self._mtbank_check_conflicts(transactions)

        # Create statement data
        first_date_text = self._get_xml_text(rows[0], "ClosingBalanceDate")
        stmt_vals = [
            {
                "name": f"{account_number}/{first_date_text}",
                "date": statement_date,
                "balance_start": balance_start or 0.0,
                "balance_end_real": balance_end or 0.0,
                "transactions": transactions,
            }
        ]

        return (currency_code, account_number, stmt_vals)

    def _mtbank_check_conflicts(self, transactions):
        """Refuse periods already imported with a different amount.

        The de-duplication of account_statement_import_file drops the
        transactions whose unique_import_id was already imported without any
        notification, so an amount corrected by the bank would be lost
        silently. Re-importing the very same amounts stays allowed: those
        transactions are simply filtered out by the base module.
        """
        conflicts = []
        for transaction in transactions:
            unique_import_id = transaction.get("unique_import_id")
            if not unique_import_id:
                continue
            line = (
                self.env["account.bank.statement.line"]
                .sudo()
                .search([("unique_import_id", "=", unique_import_id)], limit=1)
            )
            if not line:
                continue
            if float_compare(line.amount, transaction["amount"], precision_digits=2):
                conflicts.append(
                    self.env._(
                        "%(ref)s: amount in Odoo %(odoo_amount)s, amount in "
                        "the file %(file_amount)s",
                        ref=unique_import_id,
                        odoo_amount=f"{line.amount:.2f}",
                        file_amount=f"{transaction['amount']:.2f}",
                    )
                )
        if conflicts:
            raise UserError(
                self.env._(
                    "These MTBank periods were already imported with a "
                    "different amount:\n%(conflicts)s",
                    conflicts="\n".join(conflicts),
                )
            )

    def _parse_mtbank_date(self, date_str, field_name):
        """Parse MTBank date format (DD/MM/YYYY) to date object."""
        if not date_str:
            raise UserError(
                self.env._(
                    "Missing %(field)s in MTBank XML statement.",
                    field=field_name,
                )
            )
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError as error:
            raise UserError(
                self.env._(
                    "Invalid %(field)s in MTBank XML statement: %(value)s",
                    field=field_name,
                    value=date_str,
                )
            ) from error

    def _get_xml_text(self, element, tag):
        """Safely get text from XML element."""
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""
