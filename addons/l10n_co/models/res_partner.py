# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('vat', 'country_id', 'l10n_latam_identification_type_id')
    def check_vat(self):
        # check_vat is implemented by base_vat which this localization
        # doesn't directly depend on. It is however automatically
        # installed for Colombia.
        if self.sudo().env.ref('base.module_base_vat').state == 'installed':
            # don't check Colombian partners unless they have RUT (= Colombian VAT) set as document type
            self = self.filtered(lambda partner: partner.country_id.code != "CO" or\
                                                 partner.l10n_latam_identification_type_id.l10n_co_document_code == 'rut')
            return super(ResPartner, self).check_vat()
        else:
            return True
