# Copyright 2026 Aliaksandr Zubik <alexzub@tut.by> (https://artcloud.by)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    @api.model
    def _get_supported_account_types(self):
        """Add BY bank account type."""
        rslt = super()._get_supported_account_types()
        rslt.append(("by_bank", _("Belarus Bank Account")))
        return rslt

    @api.model
    def retrieve_acc_type(self, acc_number):
        """Detect Belarus bank account format."""
        if self._is_by_account(acc_number):
            return "by_bank"
        return super().retrieve_acc_type(acc_number)

    @api.constrains("acc_number", "partner_id")
    def _check_by_account(self):
        """Validate Belarus bank account number."""
        for bank in self:
            # Check if account is Belarus-related (by country or type)
            is_by_country = bank.partner_id and bank.partner_id.country_id.code == "BY"
            is_by_type = bank.acc_type == "by_bank" and bank.acc_number

            if is_by_country or is_by_type:
                if not self._is_by_account(bank.acc_number):
                    raise ValidationError(
                        _(
                            "Invalid Belarus IBAN format. "
                            "Expected format: BY + 2 check digits + 4 BIC chars + "
                            "20 account digits (total 28 characters).\n"
                            "Example: BY86AKBB30120000080000000933"
                        )
                    )

    @api.model
    def _is_by_account(self, acc_number):
        """
        Check if account number matches Belarus bank account format (IBAN).

        Belarus IBAN format:
        - Total: 28 characters
        - BY (country code) + 2 check digits + 4 BIC chars + 20 account digits
        - Example: BY86AKBB30120000080000000933
        """
        if not acc_number:
            return False

        # Remove spaces and convert to uppercase
        acc_clean = re.sub(r"\s", "", acc_number).upper()

        # Check IBAN format: BY + 2 digits + 4 alphanumeric (BIC) + 20 digits
        if not re.match(r"^BY\d{2}[A-Z0-9]{4}\d{20}$", acc_clean):
            return False

        return True

    @api.model
    def _by_calculate_check_digits(self, bank_code, account_number):
        """
        Calculate check digits for Belarus bank account.

        This is a simplified validation. The actual algorithm used by
        Belarusian banks may differ. This provides basic format validation.
        """
        # Combine bank code and account number
        full_number = bank_code + account_number

        # Calculate modulo 97 (similar to IBAN)
        # Move BY to the end and replace with numeric values (B=11, Y=34)
        numeric_string = full_number + "1134"  # B=11, Y=34 for BY

        # Calculate check digits
        remainder = int(numeric_string) % 97
        check_digits = 98 - remainder

        return str(check_digits).zfill(2)

    def _sanitize_account_number(self, acc_number):
        """Sanitize Belarus account number by removing spaces."""
        if self._is_by_account(acc_number):
            return re.sub(r"\s", "", acc_number).upper()
        return super()._sanitize_account_number(acc_number)
