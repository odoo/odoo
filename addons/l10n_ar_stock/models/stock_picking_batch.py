from odoo import api, fields, models


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    l10n_ar_show_generate_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_buttons",
    )
    l10n_ar_show_send_delivery_guide = fields.Boolean(
        compute="_compute_l10n_ar_delivery_guide_buttons",
    )

    @api.depends(
        'picking_type_id.l10n_ar_document_type_id',
        'picking_ids.l10n_ar_allow_generate_delivery_guide',
        'picking_ids.l10n_ar_allow_send_delivery_guide',
    )
    def _compute_l10n_ar_delivery_guide_buttons(self):
        for batch in self:
            is_done = batch.state == 'done'
            has_doc_type = bool(batch.picking_type_id.l10n_ar_document_type_id)
            batch.l10n_ar_show_generate_delivery_guide = (
                has_doc_type and is_done and any(batch.picking_ids.mapped('l10n_ar_allow_generate_delivery_guide'))
            )
            batch.l10n_ar_show_send_delivery_guide = (
                has_doc_type and is_done and any(batch.picking_ids.mapped('l10n_ar_allow_send_delivery_guide'))
            )

    def l10n_ar_action_create_delivery_guide(self):
        self.picking_ids.filtered('l10n_ar_allow_generate_delivery_guide').l10n_ar_action_create_delivery_guide()

    def l10n_ar_action_send_delivery_guide(self):
        self.picking_ids.filtered('l10n_ar_allow_send_delivery_guide').l10n_ar_action_send_delivery_guide(do_async=True)
