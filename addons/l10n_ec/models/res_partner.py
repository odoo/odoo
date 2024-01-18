# Part of Odoo. See LICENSE file for full copyright and licensing details.

import enum
import stdnum
from odoo import _, api, fields, models
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

    l10n_ec_vat_validation = fields.Char(
        string="VAT Error message validation",
        compute="_compute_l10n_ec_vat_validation",
        help="Error message when validating the Ecuadorian VAT",
    )

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
                        raise ValidationError(_('If your identification type is %s, it must be 10 digits',
                                                it_dni.display_name))
                    if partner.l10n_latam_identification_type_id.id == it_ruc.id and len(partner.vat) != 13:
                        raise ValidationError(_('If your identification type is %s, it must be 13 digits',
                                                it_ruc.display_name))
        return super(ResPartner, self - ecuadorian_partners).check_vat()

    @api.depends("vat", "country_id", "l10n_latam_identification_type_id")
    def _compute_l10n_ec_vat_validation(self):
        it_ruc = self.env.ref("l10n_ec.ec_ruc", False)
        it_dni = self.env.ref("l10n_ec.ec_dni", False)
        ruc = stdnum.util.get_cc_module("ec", "ruc")
        ci = stdnum.util.get_cc_module("ec", "ci")
        for partner in self:
            partner.l10n_ec_vat_validation = False
            if partner and partner.l10n_latam_identification_type_id in (it_ruc, it_dni) and partner.vat:
                final_consumer = verify_final_consumer(partner.vat)
                if not final_consumer:
                    if partner.l10n_latam_identification_type_id.id == it_dni.id and not ci.is_valid(partner.vat):
                        partner.l10n_ec_vat_validation = _("The VAT %s seems to be invalid as the tenth digit doesn't comply with the validation algorithm "
                                                           "(could be an old VAT number)", partner.vat)
                    if partner.l10n_latam_identification_type_id.id == it_ruc.id and not ruc.is_valid(partner.vat):
                        partner.l10n_ec_vat_validation = _("The VAT %s seems to be invalid as the tenth digit doesn't comply with the validation algorithm "
                                                           "(SRI has stated that this validation is not required anymore for some VAT numbers)", partner.vat)

    def _l10n_ec_get_identification_type(self):
        """Maps Odoo identification types to Ecuadorian ones.
        Useful for document type domains, electronic documents, ats, others.
        """
        self.ensure_one()

        id_types_by_xmlid = {
            'l10n_ec.ec_dni': 'cedula',  # DNI
            'l10n_ec.ec_ruc': 'ruc',  # RUC
            'l10n_ec.ec_passport': 'ec_passport',  # EC passport
            'l10n_latam_base.it_pass': 'passport',  # Passport
            'l10n_latam_base.it_fid': 'foreign',  # Foreign ID
            'l10n_latam_base.it_vat': 'foreign',
        }

        # This method is orm-cached, which makes it more efficient in loops than get_external_id()
        xmlid_by_res_id = {
            self.env['ir.model.data']._xmlid_to_res_model_res_id(xmlid, raise_if_not_found=True)[1]: xmlid
            for xmlid in id_types_by_xmlid
        }

        id_type_xmlid = xmlid_by_res_id.get(self.l10n_latam_identification_type_id.id)
        if id_type_xmlid in id_types_by_xmlid:
            return id_types_by_xmlid[id_type_xmlid]

        if self.l10n_latam_identification_type_id.country_id.code != 'EC':
            return 'foreign'
