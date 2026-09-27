from odoo import api, fields, models

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import SALE_TYPE


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_pk_edi_sale_type = fields.Selection(
        selection=SALE_TYPE,
        string="Sale Type",
        compute='_compute_l10n_pk_edi_from_product',
        precompute=True,
        store=True,
        readonly=False,
    )
    l10n_pk_edi_sro_id = fields.Many2one(
        comodel_name="l10n_pk_edi.sro",
        string="SRO Schedule",
        help="FBR Statutory Regulatory Order Schedule",
        compute='_compute_l10n_pk_edi_from_product',
        precompute=True,
        store=True,
        readonly=False,
    )
    l10n_pk_edi_sro_item_id = fields.Many2one(
        comodel_name="l10n_pk_edi.sro.item",
        string="SRO Item",
        help="FBR Statutory Regulatory Order Item",
        compute='_compute_l10n_pk_edi_from_product',
        precompute=True,
        store=True,
        readonly=False,
    )
    l10n_pk_edi_filter_sro_item_ids = fields.One2many(related='l10n_pk_edi_sro_id.sro_item_ids')

    @api.depends('product_id')
    def _compute_l10n_pk_edi_from_product(self):
        # precompute is what makes the 'draft' condition usable: these fields are stored
        for line in self:
            if line.move_id.country_code == 'PK' and line.parent_state == 'draft':
                line.l10n_pk_edi_sale_type = line.product_id.l10n_pk_edi_sale_type
                line.l10n_pk_edi_sro_id = line.product_id.l10n_pk_edi_sro_id
                line.l10n_pk_edi_sro_item_id = line.product_id.l10n_pk_edi_sro_item_id
