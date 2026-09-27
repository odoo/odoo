from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model_create_multi
    def create(self, vals_list):
        sale_orders = super().create(vals_list)
        if self.env.context.get('is_sale_order') and sale_orders and self.env.user.has_group('project.group_project_user'):
            first_so = sale_orders[0]
            projects = first_so.opportunity_id.project_ids.filtered(lambda p: not p.reinvoiced_sale_order_id)
            if projects:
                projects.sudo().write({
                    'reinvoiced_sale_order_id': first_so.id
                })
        return sale_orders
