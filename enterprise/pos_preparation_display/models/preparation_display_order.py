
from odoo import fields, models, api
from datetime import timedelta

class PosPreparationDisplayOrder(models.Model):
    _name = 'pos_preparation_display.order'
    _description = "Preparation orders"

    displayed = fields.Boolean("Order is displayed", help="Determines whether the order should be displayed on the preparation screen")
    pos_order_id = fields.Many2one('pos.order', index=True, help="ID of the original PoS order")
    pos_config_id = fields.Many2one(related='pos_order_id.config_id')
    order_stage_ids = fields.One2many('pos_preparation_display.order.stage', 'order_id', help="All the stage ids in which the order is placed")
    preparation_display_order_line_ids = fields.One2many(
        'pos_preparation_display.orderline',
        'preparation_display_order_id',
        string="Order Lines",
        readonly=True)
    pdis_general_note = fields.Text("General Note", help="Current general-note displayed on preparation display")

    @api.model
    def process_order(self, order_id, cancelled=False, general_note=None, note_history=None):
        if not order_id:
            return

        order = self.env['pos.order'].browse(order_id)
        if not order:
            return

        data = order._process_preparation_changes(cancelled, general_note, note_history)
        preparation_displays = self.env['pos_preparation_display.display'].search([
            '&',
            '|', ('pos_config_ids', '=', False),
            ('pos_config_ids', 'in', [order.config_id.id]),
            '|', ('category_ids', 'in', list(data['category_ids'])),
            ('category_ids', '=', False)])

        if data['change']:
            for p_dis in preparation_displays:
                p_dis._send_load_orders_message(data['sound'])

        return True

    @api.model
    def _send_orders_to_preparation_display(self, preparation_display_id):
        preparation_display = self.env['pos_preparation_display.display'].browse(preparation_display_id)
        preparation_display._send_load_orders_message()

    def _get_preparation_order_values(self, order):
        return {
            'displayed': True,
            'pos_order_id':  order['pos_order_id'],
        }

    def change_order_stage(self, stage_id, preparation_display_id):
        self.ensure_one()

        categories = self.preparation_display_order_line_ids.mapped('product_id.pos_categ_ids.id')
        p_dis = self.env['pos_preparation_display.display'].search([('id', '=', preparation_display_id)])

        for orderline in self.preparation_display_order_line_ids:
            orderline.todo = 1

        p_dis_categories = p_dis._get_pos_category_ids()

        if len(set(p_dis_categories.ids).intersection(categories)) > 0:
            if stage_id in p_dis.stage_ids.ids:
                current_stage = self.order_stage_ids.create({
                    'preparation_display_id': p_dis.id,
                    'stage_id': stage_id,
                    'order_id': self.id,
                    'done': False
                })

                p_dis._notify('CHANGE_ORDER_STAGE', {
                    'order_id': self.id,
                    'last_stage_change': current_stage.write_date,
                    'stage_id': stage_id
                })

                return current_stage.write_date

    def done_orders_stage(self, preparation_display_id):
        preparation_display = self.env['pos_preparation_display.display'].browse(preparation_display_id)
        last_stage = preparation_display.stage_ids[-1]

        for order in self:
            p_dis_order_stage_ids = order.order_stage_ids.filtered(lambda order_stage:
                order_stage.preparation_display_id == preparation_display
            )
            current_order_stage = p_dis_order_stage_ids.filtered(lambda order_stage:
                order_stage.stage_id == last_stage
            )

            if current_order_stage:
                p_dis_order_stage_ids.unlink()
                order.order_stage_ids.create({
                    'preparation_display_id': preparation_display_id,
                    'stage_id': last_stage.id,
                    'order_id': order.id,
                    'done': True
                })

        preparation_display._send_load_orders_message()

    def get_preparation_display_order(self, preparation_display_id):
        preparation_display = self.env['pos_preparation_display.display'].browse(preparation_display_id)
        orders = preparation_display._get_open_orders_in_display()
        new_orders = preparation_display._get_stageless_orders_in_display()
        first_stage = preparation_display.stage_ids[0]

        preparation_display_orders = []
        order_stages = []
        for order in new_orders:
            order_stages.append({
                'preparation_display_id': preparation_display_id,
                'stage_id': first_stage.id,
                'order_id': order.id,
                'done': False
            })
            orders += order
        self.env['pos_preparation_display.order.stage'].create(order_stages)

        for order in orders:
            order_ui = order._export_for_ui(preparation_display)
            if order_ui:
                preparation_display_orders.append(order_ui)

        return preparation_display_orders

    def _export_for_ui(self, preparation_display):
        preparation_display_orderlines = []

        for orderline in self.preparation_display_order_line_ids:
            if preparation_display._should_include(orderline):
                preparation_display_orderlines.append({
                    'id': orderline.id,
                    'todo': orderline.todo,
                    'internal_note': orderline.internal_note,
                    'attribute_ids': orderline.attribute_value_ids.ids,
                    'product_id': orderline.product_id.id,
                    'product_name': orderline.product_id.display_name,
                    'product_quantity': orderline.product_quantity,
                    'product_cancelled': orderline.product_cancelled,
                    'product_category_ids': orderline.product_id.pos_categ_ids.ids,
                })

        if preparation_display_orderlines:
            current_order_stage = None

            for stage in self.order_stage_ids[::-1]:
                if stage.preparation_display_id.id == preparation_display.id:
                    current_order_stage = stage
                    break

            return {
                'id': self.id,
                'pos_order_id': self.pos_order_id.id,
                'create_date': self.create_date,
                'responsible': self.create_uid.display_name,
                'stage_id': current_order_stage.stage_id.id if current_order_stage else None,
                'last_stage_change': current_order_stage.write_date if current_order_stage else self.create_date,
                'displayed': self.displayed,
                'orderlines': preparation_display_orderlines,
                'tracking_number': self.pos_order_id.tracking_number,
                'generalNote': self.pdis_general_note or '',
            }

    @api.model
    def _clean_preparation_data(self):
        orders = self.env['pos_preparation_display.order'].search([('write_date', '<=', fields.Datetime.now() - timedelta(days=1))])
        orders.unlink()
        return True
