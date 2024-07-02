from odoo import models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_cancel(self):
        res = super().button_cancel()
        for invoice in self:
            for pos_order in invoice.pos_order_ids:
                for pos_order_line in pos_order.lines:
                    if "(Cancelled)" not in pos_order_line.sale_order_line_id.name:
                        pos_order_line.sale_order_line_id.name = _("%(line_description)s (Cancelled)", line_description=pos_order_line.sale_order_line_id.name)
        return res

    def action_post(self):
        res = super().action_post()
        if self.env.user.has_group('point_of_sale.group_pos_user'):
            for invoice in self:
                for pos_order in invoice.pos_order_ids:
                    for pos_order_line in pos_order.lines:
                        pos_order_line.sale_order_line_id.name = pos_order_line.sale_order_line_id.name.replace(" (Cancelled)", "")
        return res
