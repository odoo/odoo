# Part of Odoo. See LICENSE file for full copyright and licensing details.

import enum

from odoo import _, api, models
from odoo.exceptions import ValidationError


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
        if move_type.startswith('in_'):
            if partner_id_type == 'ruc':  # includes final consumer
                return cls.IN_RUC
            elif partner_id_type == 'cedula':
                return cls.IN_CEDULA
            elif partner_id_type in ['foreign', 'passport']:
                return cls.IN_PASSPORT
        elif move_type.startswith('out_'):
            if partner_id_type == 'ruc':  # includes final consumer
                return cls.OUT_RUC
            elif partner_id_type == 'cedula':
                return cls.OUT_CEDULA
            elif partner_id_type in ['foreign', 'passport']:
                return cls.OUT_PASSPORT


class ResPartner(models.Model):

    _inherit = "res.partner"

    @api.constrains("vat", "country_id", "l10n_latam_identification_type_id")
    def check_vat(self):
        it_ruc = self.env.ref("l10n_ec.ec_ruc", False)
        it_dni = self.env.ref("l10n_ec.ec_dni", False)
        ecuadorian_partners = self.filtered(
            lambda x: x.country_id == self.env.ref("base.ec")
        )
        for partner in ecuadorian_partners:
            if partner.vat:
                if partner.l10n_latam_identification_type_id.id in (
                    it_ruc.id,
                    it_dni.id,
                ):
                    if partner.l10n_latam_identification_type_id.id == it_dni.id and len(partner.vat) != 10:
                        raise ValidationError(_('If your identification type is %s, it must be 10 digits')
                                              % it_dni.display_name)
                    if partner.l10n_latam_identification_type_id.id == it_ruc.id and len(partner.vat) != 13:
                        raise ValidationError(_('If your identification type is %s, it must be 13 digits')
                                              % it_ruc.display_name)
                    final_consumer = verify_final_consumer(partner.vat)
                    if final_consumer:
                        valid = True
                    else:
                        valid = self.is_valid_ruc_ec(partner.vat)
                    if not valid:
                        error_message = ""
                        if partner.l10n_latam_identification_type_id.id == it_dni.id:
                            error_message = _("VAT %s is not valid for an Ecuadorian DNI, "
                                              "it must be like this form 1234567897") % partner.vat
                        if partner.l10n_latam_identification_type_id.id == it_ruc.id:
                            error_message = _("VAT %s is not valid for an Ecuadorian company, "
                                              "it must be like this form 1234567897001") % partner.vat
                        raise ValidationError(error_message)
        return super(ResPartner, self - ecuadorian_partners).check_vat()

    def _l10n_ec_get_identification_type(self):
        """Maps Odoo identification types to Ecuadorian ones.
        Useful for document type domains, electronic documents, ats, others.
        """
        self.ensure_one()

        def id_type_in(*args):
            return any([self.l10n_latam_identification_type_id == self.env.ref(arg) for arg in args])

        if id_type_in('l10n_ec.ec_dni'):
            return 'cedula'  # DNI
        elif id_type_in('l10n_ec.ec_ruc'):
            return 'ruc'  # RUC
        elif id_type_in('l10n_latam_base.it_pass'):
            return 'passport'  # Pasaporte
        elif id_type_in('l10n_latam_base.it_fid', 'l10n_latam_base.it_vat') \
                or self.l10n_latam_identification_type_id.country_id != self.env.ref('base.ec'):
            return 'foreign'  # Identificacion del exterior
