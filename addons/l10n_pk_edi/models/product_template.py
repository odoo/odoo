from odoo import fields, models

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import SALE_TYPE


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------
    l10n_pk_edi_sale_type = fields.Selection(selection=SALE_TYPE, string='Sale Type', default='75', required=True)
    l10n_pk_edi_sro_id = fields.Many2one('l10n_pk_edi.sro', string='Statutory Regulatory Order Schedule')
    l10n_pk_edi_sro_item_id = fields.Many2one('l10n_pk_edi.sro.item', string='Statutory Regulatory Order Item')
    l10n_pk_edi_filter_sro_item_ids = fields.One2many(related='l10n_pk_edi_sro_id.sro_item_ids')
    l10n_pk_edi_uom_code = fields.Selection(related="uom_id.l10n_pk_edi_uom_code")
