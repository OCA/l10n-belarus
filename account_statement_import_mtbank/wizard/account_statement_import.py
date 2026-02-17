# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime
from xml.etree import ElementTree as ET

from odoo import models
from odoo.exceptions import UserError

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

        # Sort rows by date
        rows.sort(
            key=lambda r: self._parse_mtbank_date(
                self._get_xml_text(r, "ClosingBalanceDate")
            )
        )

        transactions = []
        balance_start = None
        balance_end = None

        for row in rows:
            closing_date = self._parse_mtbank_date(
                self._get_xml_text(row, "ClosingBalanceDate")
            )
            opening_balance = float(self._get_xml_text(row, "OpeningBalance") or 0)
            closing_balance = float(self._get_xml_text(row, "ClosingBalance") or 0)
            debit_turnover = float(self._get_xml_text(row, "DEBETTURNOVER") or 0)
            credit_turnover = float(self._get_xml_text(row, "CREDITTURNOVER") or 0)
            debit_count = int(self._get_xml_text(row, "DEBETDOCUMENTSCNT") or 0)
            credit_count = int(self._get_xml_text(row, "CREDITDOCUMENTSCNT") or 0)

            # Set starting balance from first row
            if balance_start is None:
                balance_start = opening_balance

            # Update ending balance
            balance_end = closing_balance

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

        # Create statement data
        first_date_text = rows[0].find("ClosingBalanceDate").text if rows else ""
        last_date_text = rows[-1].find("ClosingBalanceDate").text if rows else None
        stmt_vals = [
            {
                "name": f"{account_number}/{first_date_text}",
                "date": (
                    self._parse_mtbank_date(last_date_text)
                    if last_date_text
                    else datetime.now().date()
                ),
                "balance_start": balance_start or 0.0,
                "balance_end_real": balance_end or 0.0,
                "transactions": transactions,
            }
        ]

        return (currency_code, account_number, stmt_vals)

    def _parse_mtbank_date(self, date_str):
        """Parse MTBank date format (DD/MM/YYYY) to date object."""
        if not date_str:
            return datetime.now().date()
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            _logger.warning("Invalid date format in MTBank XML: %s", date_str)
            return datetime.now().date()

    def _get_xml_text(self, element, tag):
        """Safely get text from XML element."""
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""
