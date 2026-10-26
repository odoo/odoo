# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingBatch(models.Model):

    _inherit = 'stock.picking.batch'

    # DeCA versions of all the pickings of a batch
    l10n_es_deca_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="DeCA versions",
        compute='_compute_l10n_es_deca_attachment_ids',
    )

    @api.depends('picking_ids.l10n_es_deca_attachment_ids')
    def _compute_l10n_es_deca_attachment_ids(self):
        for batch in self:
            batch.l10n_es_deca_attachment_ids = batch.picking_ids.l10n_es_deca_attachment_ids

    def action_l10n_es_print_deca(self):
        return self.picking_ids.action_l10n_es_print_deca()
