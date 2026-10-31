# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from datetime import date
from os import path

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMTBankImport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Get or create BYN currency
        cls.currency_byn = (
            cls.env["res.currency"]
            .with_context(active_test=False)
            .search([("name", "=", "BYN")], limit=1)
        )
        if not cls.currency_byn:
            cls.currency_byn = cls.env["res.currency"].create(
                {
                    "name": "BYN",
                    "symbol": "Br",
                    "rounding": 0.01,
                    "position": "after",
                    "active": True,
                }
            )
        elif not cls.currency_byn.active:
            cls.currency_byn.active = True
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "name": "MTBank Test",
                "code": "MTBK",
                "type": "bank",
                "currency_id": cls.currency_byn.id,
                "bank_acc_number": "BY49MTBK30120001111100000000",
            }
        )

    def test_mtbank_xml_import(self):
        """Test importing MTBank XML format."""
        testfile = path.join(path.dirname(__file__), "files", "test_mtbank.xml")
        with open(testfile, "rb") as datafile:
            datafile_contents = datafile.read()

        wizard = self.env["account.statement.import"].create(
            {
                "statement_file": base64.b64encode(datafile_contents),
                "statement_filename": "test_mtbank.xml",
            }
        )

        # Import the file
        result = wizard._import_file()

        # Verify result structure
        self.assertTrue(result)
        self.assertIn("statement_ids", result)
        self.assertTrue(len(result["statement_ids"]) > 0)

        # Get created statement
        statement = self.env["account.bank.statement"].browse(
            result["statement_ids"][0]
        )

        # Verify statement data
        self.assertEqual(statement.journal_id, self.bank_journal)
        self.assertEqual(statement.balance_start, 22053.01)
        self.assertEqual(statement.balance_end_real, 22340.66)

        # Verify transactions
        self.assertTrue(len(statement.line_ids) > 0)

        # Check debit transaction
        debit_line = statement.line_ids.filtered(lambda line: line.amount < 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.amount, -712.35)
        self.assertEqual(debit_line.date, date(2025, 6, 12))

        # Check credit transaction
        credit_line = statement.line_ids.filtered(lambda line: line.amount > 0)
        self.assertEqual(len(credit_line), 1)
        self.assertEqual(credit_line.amount, 1000.00)
        self.assertEqual(credit_line.date, date(2025, 6, 15))

    def test_mtbank_xml_parse(self):
        """Test parsing MTBank XML format directly."""
        testfile = path.join(path.dirname(__file__), "files", "test_mtbank.xml")
        with open(testfile, "rb") as datafile:
            datafile_contents = datafile.read()

        wizard = self.env["account.statement.import"].create(
            {
                "statement_file": base64.b64encode(datafile_contents),
                "statement_filename": "test_mtbank.xml",
            }
        )

        # Parse the file
        result = wizard._parse_file(datafile_contents)

        # Verify it returns a list of tuples
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        # Verify tuple structure
        currency_code, account_number, stmts_vals = result[0]
        self.assertEqual(currency_code, "BYN")
        self.assertEqual(account_number, "BY49MTBK30120001111100000000")
        self.assertIsInstance(stmts_vals, list)
        self.assertEqual(len(stmts_vals), 1)

        # Verify statement values
        stmt_vals = stmts_vals[0]
        self.assertIn("balance_start", stmt_vals)
        self.assertIn("balance_end_real", stmt_vals)
        self.assertIn("transactions", stmt_vals)
        self.assertEqual(stmt_vals["balance_start"], 22053.01)
        self.assertEqual(stmt_vals["balance_end_real"], 22340.66)

        # Verify transactions
        transactions = stmt_vals["transactions"]
        self.assertEqual(len(transactions), 2)  # 1 debit + 1 credit

        # Check debit transaction
        debit_tx = next(t for t in transactions if t["amount"] < 0)
        self.assertEqual(debit_tx["amount"], -712.35)
        self.assertEqual(debit_tx["date"], date(2025, 6, 12))
        self.assertIn("unique_import_id", debit_tx)

        # Check credit transaction
        credit_tx = next(t for t in transactions if t["amount"] > 0)
        self.assertEqual(credit_tx["amount"], 1000.00)
        self.assertEqual(credit_tx["date"], date(2025, 6, 15))
        self.assertIn("unique_import_id", credit_tx)

    def _import_fixture(self, filename):
        """Import a statement fixture through the wizard."""
        testfile = path.join(path.dirname(__file__), "files", filename)
        with open(testfile, "rb") as datafile:
            datafile_contents = datafile.read()

        wizard = self.env["account.statement.import"].create(
            {
                "statement_file": base64.b64encode(datafile_contents),
                "statement_filename": filename,
            }
        )
        return wizard._import_file()

    def test_mtbank_bad_date_rejected(self):
        """Test that a row with a missing date is not imported."""
        with self.assertRaises(UserError):
            self._import_fixture("test_mtbank_bad_date.xml")

    def test_mtbank_bad_balance_rejected(self):
        """Test that a row whose balances do not match is not imported."""
        with self.assertRaises(UserError):
            self._import_fixture("test_mtbank_bad_balance.xml")

    def test_mtbank_corrected_amount_conflict(self):
        """Test that a period re-imported with a new amount is refused."""
        self._import_fixture("test_mtbank.xml")

        with self.assertRaises(UserError) as cm:
            self._import_fixture("test_mtbank_corrected_turnover.xml")
        self.assertIn("BY49MTBK30120001111100000000-20250612-DEBIT", str(cm.exception))

    def test_mtbank_reimport_same_file(self):
        """Test that re-importing the same file does not duplicate lines."""
        self._import_fixture("test_mtbank.xml")
        # Must not raise: the base module filters out known transactions
        self._import_fixture("test_mtbank.xml")

        line_model = self.env["account.bank.statement.line"]
        for unique_import_id in (
            "BY49MTBK30120001111100000000-20250612-DEBIT",
            "BY49MTBK30120001111100000000-20250615-CREDIT",
        ):
            self.assertEqual(
                line_model.search_count([("unique_import_id", "=", unique_import_id)]),
                1,
            )
