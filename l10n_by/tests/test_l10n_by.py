# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestL10nBy(TransactionCase):
    """Tests for Belarus localization."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {
                "name": "Belarus Test Company",
                "country_id": cls.env.ref("base.by").id,
                "currency_id": cls.env.ref("base.BYN").id,
            }
        )

    def test_chart_template_exists(self):
        """Test that Belarus chart template exists."""
        chart_template = self.env.ref("l10n_by.by_chart_template", raise_if_not_found=False)
        self.assertTrue(chart_template, "Belarus chart template should exist")
        self.assertEqual(chart_template.name, "Belarus - Chart of Accounts")
        self.assertEqual(chart_template.currency_id, self.env.ref("base.BYN"))

    def test_accounts_exist(self):
        """Test that key accounts are created."""
        # Check if accounts are created by trying to load the template
        chart_template = self.env.ref("l10n_by.by_chart_template")
        self.assertTrue(chart_template)

        # Verify key account templates exist
        account_templates = self.env["account.account.template"].search(
            [("chart_template_id", "=", chart_template.id)]
        )
        self.assertGreater(len(account_templates), 0, "Account templates should be created")

        # Check specific important accounts
        cash_account = self.env.ref("l10n_by.by_acc_5010", raise_if_not_found=False)
        self.assertTrue(cash_account, "Cash account should exist")

        bank_account = self.env.ref("l10n_by.by_acc_5110", raise_if_not_found=False)
        self.assertTrue(bank_account, "Bank account should exist")

    def test_vat_taxes_exist(self):
        """Test that VAT taxes are created."""
        chart_template = self.env.ref("l10n_by.by_chart_template")

        # Check VAT 20% sale tax
        vat_20_sale = self.env.ref("l10n_by.sale_vat_20", raise_if_not_found=False)
        self.assertTrue(vat_20_sale, "VAT 20% sale tax should exist")
        self.assertEqual(vat_20_sale.amount, 20.0)
        self.assertEqual(vat_20_sale.type_tax_use, "sale")

        # Check VAT 10% sale tax
        vat_10_sale = self.env.ref("l10n_by.sale_vat_10", raise_if_not_found=False)
        self.assertTrue(vat_10_sale, "VAT 10% sale tax should exist")
        self.assertEqual(vat_10_sale.amount, 10.0)

        # Check VAT 0% export tax
        vat_0_sale = self.env.ref("l10n_by.sale_vat_0", raise_if_not_found=False)
        self.assertTrue(vat_0_sale, "VAT 0% export tax should exist")
        self.assertEqual(vat_0_sale.amount, 0.0)

    def test_fiscal_positions_exist(self):
        """Test that fiscal positions are created."""
        # Check domestic fiscal position
        fp_domestic = self.env.ref("l10n_by.fp_belarus_domestic", raise_if_not_found=False)
        self.assertTrue(fp_domestic, "Domestic fiscal position should exist")
        self.assertEqual(fp_domestic.country_id, self.env.ref("base.by"))
        self.assertTrue(fp_domestic.auto_apply)

        # Check export fiscal position
        fp_export = self.env.ref("l10n_by.fp_belarus_export", raise_if_not_found=False)
        self.assertTrue(fp_export, "Export fiscal position should exist")

    def test_tax_groups_exist(self):
        """Test that tax groups are created."""
        tax_group_20 = self.env.ref("l10n_by.tax_group_vat_20", raise_if_not_found=False)
        self.assertTrue(tax_group_20, "VAT 20% tax group should exist")

        tax_group_10 = self.env.ref("l10n_by.tax_group_vat_10", raise_if_not_found=False)
        self.assertTrue(tax_group_10, "VAT 10% tax group should exist")

        tax_group_0 = self.env.ref("l10n_by.tax_group_vat_0", raise_if_not_found=False)
        self.assertTrue(tax_group_0, "VAT 0% tax group should exist")
