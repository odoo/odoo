from odoo import models


class L10nPtReprintReason(models.TransientModel):
    _inherit = 'l10n_pt.reprint.reason'

    def action_log_and_print(self):
        if self.env.context.get('res_model') == 'stock.picking':
            active_ids = self.env.context.get('active_ids')
            pickings = self.env['stock.picking'].browse(active_ids)

            for picking in pickings:
                picking.message_post(body=self._prepare_reprint_message(picking))

            report_action = self.env.ref('stock.action_report_delivery').report_action(pickings)
            report_action['close_on_report_download'] = True
            return report_action
        return super().action_log_and_print()

