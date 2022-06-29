# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


def verify_final_consumer(vat):
    all_number_9 = False
    try:
        all_number_9 = vat and all(int(number) == 9 for number in vat) or False
    except ValueError as e:
        _logger.debug('Vat is not only numbers %s', e)
    return all_number_9 and len(vat) == 13


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
                                              "it must be like this form 0123456782") % partner.vat
                        if partner.l10n_latam_identification_type_id.id == it_ruc.id:
                            error_message = _("VAT %s is not valid for an Ecuadorian company, "
                                              "it must be like this form 0123456782001") % partner.vat
                        raise ValidationError(error_message)
        return super(ResPartner, self - ecuadorian_partners).check_vat()
