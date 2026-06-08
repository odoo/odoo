import logging
import re

from odoo import api, models, _

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _run_check_identification(self, validation='error'):
        """Add validation of UY document types CI and NIE  """
        if validation == 'error':
            ci_nie_types = self.filtered(lambda p:
                p.l10n_latam_identification_type_id.l10n_uy_dgi_code in ("1", "3")
                and p.l10n_latam_identification_type_id.country_id.code == "UY"
                and p.vat
            )
            for partner in ci_nie_types:
                if not partner._l10n_uy_ci_nie_is_valid():
                    raise ValidationError(self._l10n_uy_build_vat_error_message(partner))
        return super()._run_check_identification(validation=validation)

    @api.model
    def _l10n_uy_build_vat_error_message(self, partner):
        """ Similar to _build_vat_error_message but using latam doc type name instead of vat_label
        NOTE: maybe can be implemented in master to l10n_latam_base for the use of different doc types """
        vat_label = _("CI/NIE")
        expected_format = _("3:402.010-2 or 93:402.010-1 (CI or NIE)")

        # Catch use case where the record label is about the public user (name: False)
        if partner.name:
            msg = "\n" + _(
                "The %(vat_label)s number [%(wrong_vat)s] for %(partner_label)s does not seem to be valid."
                "\nNote: the expected format is %(expected_format)s",
                vat_label=vat_label,
                wrong_vat=partner.vat,
                partner_label=_("partner [%s]", partner.name),
                expected_format=expected_format,
            )
        else:
            msg = "\n" + _(
                "The %(vat_label)s number [%(wrong_vat)s] does not seem to be valid."
                "\nNote: the expected format is %(expected_format)s",
                vat_label=vat_label,
                wrong_vat=partner.vat,
                expected_format=expected_format,
            )
        return msg

    def _l10n_uy_ci_nie_is_valid(self):
        """ Check if the partner's CI or NIE number is a valid one.

        CI:
            1) The ID number is taken up to the second to last position, that is, the first 6 or 7 digits.
            2) Each digit is multiplied by a different factor starting from right to left, the factors are:
                2, 9, 8, 7, 6, 3, 4.
            3) The products obtained are added:
            4) The base module 10 is calculated on this result to obtain the check digit, expressed in another way,
            the next number ending in zero is taken that follows the result of the addition (for the example
            would be 60) subtracting the sum itself: 60 - 59 = 1. The verification digit of the example ID is 1.

            NOTE: If the ID has fewer digits, it is preceded with zeros and the mechanism described above is applied

        NIE:
            The calculation for the NIE is the same as that used for the CI. The only difference is that we skip the
            first number

        Both algorithms where extracted from Uruware's Technical Manual (section 9.2 and 9.3)

        Return: False is not valid, True is valid
        """
        self.ensure_one()

        # The VAT must consist only numbers (format could have these characters ":., " we can skip them later)
        invalid_chars = re.findall(r"[^0-9:., \-]", self.vat)
        if invalid_chars:
            return False

        ci_nie_number = re.sub("[^0-9]", "", self.vat)

        # we get the validation digit, if NIE doc type we skip the first digit
        is_nie = self.l10n_latam_identification_type_id.l10n_uy_dgi_code == "1"
        verif_digit = int(ci_nie_number[-1])
        ci_nie_number = ci_nie_number[1:-1] if is_nie else ci_nie_number[0:-1]

        # If number is < 7 digits we add 0 to the left
        ci_nie_number = "%07d" % int(ci_nie_number)

        # If NIE > 7 digits is not valid
        if len(ci_nie_number) > 7:
            return False

        verification_vector = (2, 9, 8, 7, 6, 3, 4)
        num_sum = sum(int(ci_nie_number[i]) * verification_vector[i] for i in range(7))

        res = -num_sum % 10
        return res == verif_digit
