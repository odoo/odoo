# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields


class AccountMove(models.Model):

    _inherit = 'account.move'

    l10n_ar_afip_responsability_type_id = fields.Many2one(
        'l10n_ar.afip.responsability.type', string='AFIP Responsability Type', index=True, help='Defined by AFIP to'
        ' identify the type of responsabilities that a person or a legal entity could have and that impacts in the'
        ' type of operations and requirements they need.')

    # TODO do it on create/write
    @api.constrains('partner_id')
    def set_l10n_ar_afip_responsability_type_id(self):
        for rec in self:
            commercial_partner = rec.partner_id.commercial_partner_id
            rec.l10n_ar_afip_responsability_type_id = commercial_partner.l10n_ar_afip_responsability_type_id.id

    @staticmethod
    def _l10n_ar_get_document_number_parts(document_number, document_type_code):
        # despachos de importacion
        if document_type_code in ['66', '67']:
            point_of_sale = invoice_number = '0'
        else:
            invoice_number, point_of_sale = document_number.split('-')
        return {'invoice_number': int(invoice_number), 'point_of_sale': int(point_of_sale)}
