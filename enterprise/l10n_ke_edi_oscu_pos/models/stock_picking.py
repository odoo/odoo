from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_ke_state = fields.Selection(selection_add=[('waiting_pos_order', "Waiting for pos order")])

    @api.depends('move_ids.l10n_ke_oscu_sar_number',
                 'move_ids.l10n_ke_oscu_flow_type_code',
                 'state',
                 'partner_id')
    def _compute_l10n_ke_state(self):
        super()._compute_l10n_ke_state()
        for pick in self:
            if pick.pos_order_id and pick.l10n_ke_state != 'sent':
                if pick.pos_order_id.l10n_ke_order_send_status == 'sent':
                    pick.l10n_ke_state = 'to_send'
                else:
                    pick.l10n_ke_state = 'waiting_pos_order'
