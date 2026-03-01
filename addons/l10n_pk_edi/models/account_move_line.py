from odoo import api, fields, models

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import TRANSACTION_TYPE


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_pk_edi_transaction_type = fields.Selection(
        selection=TRANSACTION_TYPE,
        string='Transaction Type',
        compute='_compute_l10n_pk_edi_transaction_type',
        store=True,
        readonly=False,
    )
    l10n_pk_edi_sro_id = fields.Many2one(
        "l10n_pk_edi.sro",
        string='SRO Schedule',
        compute="_compute_l10n_pk_edi_sro_id",
        store=True,
        readonly=False,
    )
    l10n_pk_edi_sro_item_id = fields.Many2one(
        'l10n_pk_edi.sro.item',
        string='SRO Item',
        compute="_compute_l10n_pk_edi_sro_item_id",
        store=True,
        readonly=False,
    )
    l10n_pk_edi_filter_sro_item_ids = fields.One2many(related='l10n_pk_edi_sro_id.sro_item_ids')

    @api.depends('product_id')
    def _compute_l10n_pk_edi_transaction_type(self):
        for record in self:
            record.l10n_pk_edi_transaction_type = (
                record.product_id.l10n_pk_edi_transaction_type
            )

    @api.depends('product_id')
    def _compute_l10n_pk_edi_sro_id(self):
        for record in self:
            record.l10n_pk_edi_sro_id = (
                record.product_id.l10n_pk_edi_sro_id
            )

    @api.depends('product_id')
    def _compute_l10n_pk_edi_sro_item_id(self):
        for record in self:
            record.l10n_pk_edi_sro_item_id = (
                record.product_id.l10n_pk_edi_sro_item_id
            )
