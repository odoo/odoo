# Part of Odoo. See LICENSE file for full copyright and licensing details.

import enum
import stdnum
from odoo import _, api, fields, models


def verify_final_consumer(vat):
    return vat == '9' * 13  # final consumer is identified with 9999999999999


class PartnerIdTypeEc(enum.Enum):
    """
    Ecuadorian partner identification type/code for ATS and SRI.
    """

    IN_RUC = '01'
    IN_CEDULA = '02'
    IN_PASSPORT = '03'
    OUT_RUC = '04'
    OUT_CEDULA = '05'
    OUT_PASSPORT = '06'
    FINAL_CONSUMER = '07'
    FOREIGN = '08'

    @classmethod
    def get_ats_code_for_partner(cls, partner, move_type):
        """
        Returns ID code for move and partner based on subset of Table 2 of SRI's ATS specification
        """
        partner_id_type = partner._l10n_ec_get_identification_type()
        if partner.vat and verify_final_consumer(partner.vat):
            return cls.FINAL_CONSUMER
        elif move_type.startswith('in_'):
            return {  # 'ruc' includes final consumer
                'ruc': cls.IN_RUC,
                'cedula': cls.IN_CEDULA,
                'foreign': cls.IN_PASSPORT,
            }.get(partner_id_type)
        elif move_type.startswith('out_'):
            return {  # 'ruc' includes final consumer
                'ruc': cls.OUT_RUC,
                'cedula': cls.OUT_CEDULA,
                'foreign': cls.OUT_PASSPORT,
            }.get(partner_id_type)


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ec_vat_validation = fields.Char(
        string="VAT Error message validation",
        compute="_compute_l10n_ec_vat_validation",
        help="Error message when validating the Ecuadorian VAT",
    )

    @api.depends("vat", "country_id", "additional_identifiers")
    def _compute_l10n_ec_vat_validation(self):
        ruc = stdnum.util.get_cc_module("ec", "ruc")
        for partner in self:
            partner.l10n_ec_vat_validation = False
            if partner.country_code != 'EC' or not partner.vat or verify_final_consumer(partner.vat):
                continue
            # Cédula partners keep their citizen id under additional_identifiers EC_DNI;
            # in that case the vat field does not hold a RUC, so skip the RUC syntax check.
            if partner._get_additional_identifier('EC_DNI'):
                continue
            if not ruc.is_valid(partner.vat):
                partner.l10n_ec_vat_validation = _(
                    "The VAT %s seems to be invalid as the tenth digit doesn't comply with the validation algorithm "
                    "(SRI has stated that this validation is not required anymore for some VAT numbers)", partner.vat)

    def _l10n_ec_get_identification_type(self):
        """Maps the partner's identification to Ecuadorian ATS codes.

        - ``EC_DNI`` additional identifier → ``cedula``
        - ``PASSPORT`` additional identifier → ``foreign`` (passport-domiciled
          individual; the ATS treats them as a foreign-style ID)
        - EC partners with a ``vat`` (RUC or final consumer) → ``ruc``
        - any other partner (non-EC, or unidentified) → ``foreign``
        """
        self.ensure_one()
        if self._get_additional_identifier('EC_DNI'):
            return 'cedula'
        if self._get_additional_identifier('PASSPORT'):
            return 'foreign'
        if self.country_code == 'EC' and self.vat:
            return 'ruc'
        return 'foreign'
