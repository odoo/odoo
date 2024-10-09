from odoo import models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def reflect_cancelled_sol(self, isCancelled):
        if self.env.user.has_group('point_of_sale.group_pos_user'):
            for invoice in self:
                for pos_order_line in invoice.pos_order_ids.mapped('lines'):
                    if isCancelled and "(Cancelled)" not in pos_order_line.sale_order_line_id.name:
                        pos_order_line.sale_order_line_id.name = _("%(line_description)s (Cancelled)", line_description=pos_order_line.sale_order_line_id.name)
                    elif not isCancelled:
                        pos_order_line.sale_order_line_id.name = pos_order_line.sale_order_line_id.name.replace(" (Cancelled)", "")

    def button_cancel(self):
        res = super().button_cancel()
        self.reflect_cancelled_sol(True)
        return res

    def action_post(self):
        res = super().action_post()
        self.reflect_cancelled_sol(False)
        return res
