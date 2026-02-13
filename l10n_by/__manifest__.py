# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Belarus - Accounting",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations/Account Charts",
    "summary": "Chart of Accounts and Taxes for Belarus",
    "author": "Aliaksandr Zubik, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-belarus",
    "license": "AGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "data/account_account_tag_data.xml",
        "data/account_chart_template_data.xml",
        "data/template/account.account-by.csv",
        "data/account_tax_group_data.xml",
        "data/account_tax_template_data.xml",
        "data/l10n_by_chart_post_data.xml",
        "data/account_fiscal_position_template_data.xml",
        "data/account_chart_template_configuration_data.xml",
    ],
    "installable": True,
    "auto_install": False,
}
