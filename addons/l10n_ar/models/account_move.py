# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class AccountMove(models.Model):

    _inherit = 'account.move'

    l10n_ar_afip_responsability_type = fields.Selection(
        selection='_get_afip_responsabilities',
        string='AFIP Responsability Type',
    )

    @api.constrains('partner_id')
    def set_l10n_ar_afip_responsability_type(self):
        for rec in self:
            commercial_partner = rec.partner_id.commercial_partner_id
            rec.l10n_ar_afip_responsability_type = (
                commercial_partner.l10n_ar_afip_responsability_type)

    def _get_afip_responsabilities(self):
        """ Return the list of values of the selection field """
        return self.env['res.partner']._get_afip_responsabilities()

    @staticmethod
    def _l10n_ar_get_document_number_parts(document_number, document_type_code):
        # despachos de importacion
        if document_type_code in ['66', '67']:
            point_of_sale = '0'
            invoice_number = '0'
        else:
            invoice_number, point_of_sale  = str_number.split('-')
        return {
            'invoice_number': int(invoice_number),
            'point_of_sale': int(point_of_sale),
        }
