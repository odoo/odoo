from odoo import models, fields


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    pos_table_stand_number = fields.Char(string="Table Stand Number")
    pos_takeaway = fields.Boolean(string="Take Away", default=False)

    def _export_for_ui(self, preparation_display):
        order_for_ui = super()._export_for_ui(preparation_display)

        if order_for_ui:
            order_for_ui['takeaway'] = self.pos_order_id.takeaway
            order_for_ui['table_stand_number'] = self.pos_order_id.table_stand_number

        return order_for_ui

    def _get_preparation_order_values(self, order):
        order_to_create = super()._get_preparation_order_values(order)

        if order.get('pos_takeaway'):
            order_to_create['pos_takeaway'] = order['pos_takeaway']
        if order.get('pos_table_stand_number'):
            order_to_create['pos_table_stand_number'] = order['pos_table_stand_number']

        return order_to_create
