# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "MTBank Statement Import",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Import bank statements from MTBank (Belarus) XML format",
    "author": "Aliaksandr Zubik, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-belarus",
    "license": "AGPL-3",
    "countries": ["by"],
    "depends": [
        "account_statement_import_file",
        "l10n_by",
        "l10n_by_bank",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
}
