# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestResPartnerBank(TransactionCase):
    """Tests for Belarus bank account validation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "country_id": cls.env.ref("base.by").id,
            }
        )
        cls.bank = cls.env["res.bank"].search(
            [("bic", "=", "AKBBBY2X")], limit=1
        )  # Belarusbank

    def test_valid_by_account(self):
        """Test that valid Belarus account is accepted."""
        bank_account = self.env["res.partner.bank"].create(
            {
                "partner_id": self.partner.id,
                "acc_number": "BY86AKBB30120000080000000933",
                "bank_id": self.bank.id,
            }
        )
        self.assertEqual(bank_account.acc_type, "by_bank")
        self.assertEqual(
            bank_account.sanitized_acc_number, "BY86AKBB30120000080000000933"
        )

    def test_valid_by_account_with_spaces(self):
        """Test that Belarus account with spaces is sanitized."""
        bank_account = self.env["res.partner.bank"].create(
            {
                "partner_id": self.partner.id,
                "acc_number": "BY86 AKBB 3012 0000 0800 0000 0933",
                "bank_id": self.bank.id,
            }
        )
        self.assertEqual(bank_account.acc_type, "by_bank")
        self.assertEqual(
            bank_account.sanitized_acc_number, "BY86AKBB30120000080000000933"
        )

    def test_invalid_by_account_too_short(self):
        """Test that too short account number is rejected."""
        with self.assertRaises(ValidationError):
            self.env["res.partner.bank"].create(
                {
                    "partner_id": self.partner.id,
                    "acc_number": "BY86AKBB301200000800",
                    "bank_id": self.bank.id,
                }
            )

    def test_invalid_by_account_wrong_prefix(self):
        """Test that account without BY prefix is rejected."""
        with self.assertRaises(ValidationError):
            self.env["res.partner.bank"].create(
                {
                    "partner_id": self.partner.id,
                    "acc_number": "XX86AKBB30120000080000000933",
                    "bank_id": self.bank.id,
                }
            )

    def test_invalid_by_account_letters_in_digits(self):
        """Test that account with letters where digits expected is rejected."""
        with self.assertRaises(ValidationError):
            self.env["res.partner.bank"].create(
                {
                    "partner_id": self.partner.id,
                    "acc_number": "BYXXAKBB30120000080000000933",
                    "bank_id": self.bank.id,
                }
            )

    def test_detect_by_account_type(self):
        """Test automatic detection of Belarus account type."""
        acc_type = self.env["res.partner.bank"].retrieve_acc_type(
            "BY86AKBB30120000080000000933"
        )
        self.assertEqual(acc_type, "by_bank")

    def test_banks_loaded(self):
        """Test that Belarus banks are loaded from official NBRB data."""
        belarusbank = self.env["res.bank"].search([("bic", "=", "AKBBBY2X")])
        self.assertTrue(belarusbank, "Belarusbank should be loaded")
        self.assertEqual(belarusbank.name, "ОАО 'АСБ Беларусбанк'")
        self.assertEqual(belarusbank.country, self.env.ref("base.by"))

        # Check that multiple banks are loaded
        by_banks = self.env["res.bank"].search([("country", "=", self.env.ref("base.by").id)])
        self.assertGreater(len(by_banks), 20, "Should have loaded 26 Belarus banks")
