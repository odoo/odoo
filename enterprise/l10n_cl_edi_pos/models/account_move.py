# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'pos.load.mixin']

    l10n_cl_sii_barcode_image = fields.Char(string="SII Barcode Image", compute='_compute_l10n_cl_sii_barcode_image')

    def _compute_l10n_cl_sii_barcode_image(self):
        for record in self:
            record.l10n_cl_sii_barcode_image = False
            if record.l10n_cl_sii_barcode:
                record.l10n_cl_sii_barcode_image = record._pdf417_barcode(record.l10n_cl_sii_barcode)

    @api.model
    def _load_pos_data_domain(self, data):
        result = super()._load_pos_data_domain(data)
        if self.env.company.country_id.code == 'CL':
            return False
        return result

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'CL':
            return ['l10n_latam_document_type_id', 'l10n_latam_document_number', 'l10n_cl_sii_barcode_image']
        return result
