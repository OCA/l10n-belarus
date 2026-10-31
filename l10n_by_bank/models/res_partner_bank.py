# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.base_iban.models.res_partner_bank import (
    normalize_iban,
    validate_iban,
)


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.model
    def _get_supported_account_types(self):
        """Add BY bank account type."""
        rslt = super()._get_supported_account_types()
        rslt.append(("by_bank", self.env._("Belarus Bank Account")))
        return rslt

    @api.model
    def retrieve_acc_type(self, acc_number):
        """Detect Belarus bank account format."""
        if self._is_by_account(acc_number):
            return "by_bank"
        return super().retrieve_acc_type(acc_number)

    @api.constrains("acc_number", "partner_id")
    def _check_by_account(self):
        """Validate Belarus bank account numbers."""
        for bank in self:
            acc_number = bank.acc_number
            if not acc_number:
                continue
            # Only numbers starting with BY are Belarusian: a Belarusian
            # partner may legitimately hold a foreign bank account.
            if not normalize_iban(acc_number).upper().startswith("BY"):
                continue
            if not self._is_by_account(acc_number):
                raise ValidationError(
                    self.env._(
                        "Invalid Belarus IBAN. Expected structure: "
                        "BY + 2 check digits + 4 bank code characters + "
                        "4 balance account digits + 16 account number "
                        "characters (28 characters in total).\n"
                        "Example: BY13NBRB3600900000002Z00AB00"
                    )
                )

    @api.model
    def _is_by_account(self, acc_number):
        """
        Check if account number is a valid Belarusian IBAN.

        Belarus IBAN structure per the SWIFT registry (28 characters):
        BY + 2 check digits + 4 bank code characters (letters/digits)
        + 4 balance account digits + 16 account number characters
        (letters/digits), e.g. BY13NBRB3600900000002Z00AB00
        """
        if not acc_number:
            return False

        acc_clean = normalize_iban(acc_number).upper()
        if not acc_clean.startswith("BY"):
            return False

        # BYkk BBBB AAAA CCCC CCCC CCCC CCCC: the balance account number
        # part is digits only, letters are allowed in the account number.
        if not re.match(r"^BY\d{2}[A-Z0-9]{4}\d{4}[A-Z0-9]{16}$", acc_clean):
            return False

        # The IBAN checksum (mod-97) is validated by base_iban.
        try:
            validate_iban(acc_clean)
        except ValidationError:
            return False

        return True

    def _sanitize_account_number(self, acc_number):
        """Sanitize Belarus account number by removing separators."""
        if self._is_by_account(acc_number):
            return normalize_iban(acc_number).upper()
        return super()._sanitize_account_number(acc_number)
