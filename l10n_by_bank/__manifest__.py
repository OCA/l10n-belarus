# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Belarus - Banks",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Belarus bank accounts validation and bank registry",
    "author": "Aliaksandr Zubik, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-belarus",
    "license": "AGPL-3",
    "countries": ["by"],
    "depends": [
        "account",
        "l10n_by",
    ],
    "data": [
        "data/res_bank_data.xml",
        "views/res_partner_bank_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
