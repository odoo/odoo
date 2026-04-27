from odoo import _, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('invoice_line_ids.product_id',
                 'invoice_line_ids.product_uom_id')
    def _compute_l10n_ke_validation_message(self):
        super()._compute_l10n_ke_validation_message()
        for move in self:
            if move.pos_order_ids.l10n_ke_order_send_status == 'sent':
                move.l10n_ke_validation_message = {}

    def action_view_pos_order(self):
        return {
            'name': _('Pos Order'),
            'view_mode': 'form',
            'view_id': self.env.ref('point_of_sale.view_pos_pos_form').id,
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'res_id': self.pos_order_ids.id,
        }
