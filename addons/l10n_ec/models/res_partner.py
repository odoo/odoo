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
        if partner.vat and verify_final_consumer(partner.vat):
            return cls.FINAL_CONSUMER
        elif move_type.startswith('in_'):
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

    def _run_check_identification(self, validation='error'):
        """ Since we validate more documents than the vat for Argentinean partners (CUIT - VAT AR, CUIL, DNI) we
        extend this method in order to process it. """
        l10n_ec_partners = self.filtered(lambda p: p.vat and p.country_code == 'EC')
        if l10n_ec_partners and validation == 'error':
            it_dni = self.env.ref("l10n_ec.ec_dni", False)
            for partner in l10n_ec_partners.filtered(lambda p: p.l10n_latam_identification_type_id == it_dni):
                if len(partner.vat) != 10 or not partner.vat.isdecimal():
                    raise ValidationError(_('If your identification type is %s, it must be 10 digits',
                                            it_dni.display_name))

        return super(ResPartner, self - l10n_ec_partners)._run_check_identification(validation=validation)

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
