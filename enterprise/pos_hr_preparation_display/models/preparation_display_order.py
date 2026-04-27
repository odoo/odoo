from odoo import fields, models, api


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    employee_id = fields.Many2one('hr.employee', string='Responsible employee')

    def _export_for_ui(self, preparation_display):
        data = super()._export_for_ui(preparation_display)
        if data and self.employee_id:
            data['responsible'] = self.employee_id.name
        return data

    @api.model_create_multi
    def create(self, vals_list):
        # We cannot use related='pos_order_id.employee_id' on the field employee_id because
        # it can be several pos_preparation_display.order with different employee_id for one
        # pos_order_id. So we set the employee_id manually
        result = super().create(vals_list)
        for order in result:
            order.employee_id = order.pos_order_id.employee_id
        return result
