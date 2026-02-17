# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from datetime import date
from os import path

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMTBankImport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_byn = cls.env.ref("base.BYN")
        cls.bank_journal = cls.env["account.journal"].create({
            "name": "MTBank Test",
            "code": "MTBK",
            "type": "bank",
            "currency_id": cls.currency_byn.id,
            "bank_acc_number": "BY09MTBK30120001093300069943",
        })

    def test_mtbank_xml_import(self):
        """Test importing MTBank XML format."""
        testfile = path.join(path.dirname(__file__), "files", "test_mtbank.xml")
        with open(testfile, "rb") as datafile:
            datafile_contents = datafile.read()

        wizard = self.env["account.statement.import"].create({
            "statement_file": base64.b64encode(datafile_contents),
            "statement_filename": "test_mtbank.xml",
        })

        # Import the file
        result = wizard._import_file()

        # Verify result structure
        self.assertTrue(result)
        self.assertIn("statement_ids", result)
        self.assertTrue(len(result["statement_ids"]) > 0)

        # Get created statement
        statement = self.env["account.bank.statement"].browse(result["statement_ids"][0])

        # Verify statement data
        self.assertEqual(statement.journal_id, self.bank_journal)
        self.assertEqual(statement.balance_start, 22053.01)
        self.assertEqual(statement.balance_end_real, 22340.66)

        # Verify transactions
        self.assertTrue(len(statement.line_ids) > 0)

        # Check debit transaction
        debit_line = statement.line_ids.filtered(lambda l: l.amount < 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.amount, -712.35)
        self.assertEqual(debit_line.date, date(2025, 6, 12))

        # Check credit transaction
        credit_line = statement.line_ids.filtered(lambda l: l.amount > 0)
        self.assertEqual(len(credit_line), 1)
        self.assertEqual(credit_line.amount, 1000.00)
        self.assertEqual(credit_line.date, date(2025, 6, 15))

    def test_mtbank_xml_parse(self):
        """Test parsing MTBank XML format directly."""
        testfile = path.join(path.dirname(__file__), "files", "test_mtbank.xml")
        with open(testfile, "rb") as datafile:
            datafile_contents = datafile.read()

        wizard = self.env["account.statement.import"].create({
            "statement_file": base64.b64encode(datafile_contents),
            "statement_filename": "test_mtbank.xml",
        })

        # Parse the file
        result = wizard._parse_file(datafile_contents)

        # Verify it returns a list of tuples
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        # Verify tuple structure
        currency_code, account_number, stmts_vals = result[0]
        self.assertEqual(currency_code, "BYN")
        self.assertEqual(account_number, "BY09MTBK30120001093300069943")
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
