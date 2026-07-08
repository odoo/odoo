from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        production_ids = set()
        for move in posted:
            if not move.is_purchase_document():
                continue
            mos = move.invoice_line_ids.purchase_line_id.move_ids._get_subcontract_production()
            production_ids.update(mos.filtered(lambda p: p.state == 'done').ids)
        self.env['mrp.production'].browse(production_ids)._post_subcontract_extra_cost()
        return posted
