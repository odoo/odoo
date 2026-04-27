from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.pos_preparation_display.models.preparation_display_orderline import PosPreparationDisplayOrderline

class PosPreparationDisplay(models.Model):
    _name = 'pos_preparation_display.display'
    _inherit = ["pos.bus.mixin", "pos.load.mixin"]
    _description = "Preparation display"

    name = fields.Char("Name", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    pos_config_ids = fields.Many2many(string="Point of Sale", comodel_name='pos.config')
    category_ids = fields.Many2many('pos.category', string="Product categories", help="Product categories that will be displayed on this screen.")
    order_count = fields.Integer("Order count", compute='_compute_order_count')
    average_time = fields.Integer("Order average time", compute='_compute_order_count', help="Average time of all order that not in a done stage.")
    stage_ids = fields.One2many('pos_preparation_display.stage', 'preparation_display_id', string="Stages", default=[
        {'name': 'To prepare', 'color': '#6C757D', 'alert_timer': 10},
        {'name': 'Ready', 'color': '#4D89D1', 'alert_timer': 5},
        {'name': 'Completed', 'color': '#4ea82a', 'alert_timer': 0}
    ])
    contains_bar_restaurant = fields.Boolean("Is a Bar/Restaurant", compute='_compute_contains_bar_restaurant', store=True)
    access_token = fields.Char("Access Token", default=lambda self: self._ensure_access_token())

    @api.model
    def _load_pos_data_domain(self, data):
        return [
            (
                "id",
                "in",
                [
                    display.id
                    for display in self.env["pos_preparation_display.display"]
                    .search([])
                    .filtered(
                        lambda d: not d.pos_config_ids
                        or data["pos.config"]["data"][0]["id"] in d.pos_config_ids.ids
                    )
                ],
            )
        ]

    @api.model_create_multi
    def create(self, vals_list):
        displays = super().create(vals_list)
        displays.reset()
        return displays

    # getter for pos_category_ids and pos_config_ids, in case of no one selected, return all of each.
    def _get_pos_category_ids(self):
        self.ensure_one()
        if not self.category_ids:
            return self.env['pos.category'].search([])
        else:
            return self.category_ids

    def _should_include(self, orderline: PosPreparationDisplayOrderline) -> bool:
        """
        Returns whether the orderline should be included in the preparation
        display, based on the categories that are selected for the preparation
        """
        return any(categ_id in self._get_pos_category_ids().ids for categ_id in orderline.product_id.pos_categ_ids.ids)

    def get_pos_config_ids(self):
        self.ensure_one()
        if not self.pos_config_ids:
            return self.env['pos.config'].search([])
        else:
            return self.pos_config_ids

    def _get_open_orders_in_display(self):
        self.ensure_one()
        PosPreparationDisplayOrder = self.env['pos_preparation_display.order']
        open_orders = self.env['pos_preparation_display.order.stage']._read_group(
            domain=[
                ('preparation_display_id', '=', self.id),
                ('order_id.pos_order_id.session_id.state', 'not in', ['closed', 'closing_control']),
            ],
            groupby=['order_id'],
            having=[('done:bool_or', '=', False)],
        )
        orders = PosPreparationDisplayOrder
        if open_orders:
            orders = PosPreparationDisplayOrder.union(*(order[0] for order in open_orders))

        return orders

    def _get_stageless_orders_in_display(self):
        self.ensure_one()
        stageless_orders_ids = self.env['pos_preparation_display.order']._search([
            '|', ('pos_order_id', '=', False),
                 ('pos_config_id', 'in', self.get_pos_config_ids().ids),
        ])
        stageless_orders_ids.add_where(
            """
            NOT EXISTS
                (
                    SELECT 1
                    FROM pos_preparation_display_order_stage
                    WHERE order_id = pos_preparation_display_order.id AND preparation_display_id = %s
                )
            """,
            (self.id,)
        )

        return self.env['pos_preparation_display.order'].browse(stageless_orders_ids)

    def get_preparation_display_data(self):
        return {
            'categories': self._get_pos_category_ids().read(['id', 'display_name', 'sequence']),
            'stages': self.stage_ids.read(),
            'orders': self.env["pos_preparation_display.order"].get_preparation_display_order(self.id),
            'attributes': self.env['product.attribute'].search([]).read(['id', 'name']),
            'attribute_values': self.env['product.template.attribute.value'].search([]).read(['id', 'name', 'attribute_id']),
        }

    def open_reset_wizard(self):
        return {
            'name': _("Reset Preparation Display"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pos_preparation_display.reset.wizard',
            'target': 'new',
            'context': {'preparation_display_id': self.id}
        }

    def open_ui(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos_preparation_display/web?display_id=%d' % self.id,
            'target': 'self',
        }

    # if needed the user can instantly reset a preparation display and archive all the orders.
    def reset(self):
        for preparation_display in self:
            last_stage = preparation_display.stage_ids[-1]
            orders = preparation_display._get_open_orders_in_display()
            new_orders = preparation_display._get_stageless_orders_in_display()

            order_stages = []
            for order in new_orders:
                order_stages.append({
                        'preparation_display_id': preparation_display.id,
                        'stage_id': last_stage.id,
                        'order_id': order.id,
                        'done': True
                    })
            self.env['pos_preparation_display.order.stage'].create(order_stages)

            for order in orders:
                current_order_stage = None

                for stage in order.order_stage_ids[::-1]:
                    if stage.preparation_display_id.id == preparation_display.id:
                        current_order_stage = stage
                        break

                current_order_stage.done = True

            preparation_display._send_load_orders_message()

    def _send_load_orders_message(self, sound=False):
        self.ensure_one()
        self._notify('LOAD_ORDERS', {'sound': sound})

    @api.depends('stage_ids', 'pos_config_ids', 'category_ids')
    def _compute_order_count(self):
        for preparation_display in self:
            progress_order_count = 0
            orders = preparation_display.env['pos_preparation_display.order'].search([
                ('pos_config_id', 'in', preparation_display.get_pos_config_ids().ids),
                ('create_date', '>=', fields.Date.today())
            ])

            for order in orders:
                order_stage = order.order_stage_ids.filtered(lambda s: s.preparation_display_id.id == preparation_display.id)

                if order_stage:
                    order_stage_last = sorted(order_stage, key=lambda s: s.write_date, reverse=True)[0]
                    if order_stage_last.stage_id.id == preparation_display.stage_ids[-1].id:
                        continue

                for orderline in order.preparation_display_order_line_ids:
                    if preparation_display._should_include(orderline) and orderline.product_quantity > 0:
                        progress_order_count += 1
                        break

            preparation_display.order_count = progress_order_count
            order_stages = self.env['pos_preparation_display.order.stage'].search([
                ('preparation_display_id', '=', preparation_display.id),
                ('create_date', '>=', fields.Date.today()),
                ('done', '=', True)
            ])

            completed_order_times = [(order_stage.write_date - order_stage.order_id.create_date).total_seconds() for order_stage in order_stages]
            preparation_display.average_time = round(sum(completed_order_times) / len(completed_order_times) / 60) if completed_order_times else 0

    @api.constrains('stage_ids')
    def _check_stage_ids(self):
        for preparation_display in self:
            if len(preparation_display.stage_ids) == 0:
                raise ValidationError(_("A preparation display must have a minimum of one step."))
            # If any session is open, the stages cannot be modified.
            if any(preparation_display.pos_config_ids.mapped('session_ids').filtered(lambda s: s.state =='opened')):
                raise ValidationError(_("You cannot modify the stages of a preparation display that has an active sessions."))

    @api.depends('pos_config_ids')
    def _compute_contains_bar_restaurant(self):
        for preparation_display in self:
            preparation_display.contains_bar_restaurant = any(pos_config_id.module_pos_restaurant for pos_config_id in preparation_display.get_pos_config_ids())

    @api.model
    def pos_has_valid_product(self):
        return self.env['product.product'].sudo().search_count([('available_in_pos', '=', True), ('list_price', '>=', 0), ('id', 'not in', self.env['pos.config']._get_special_products().ids)], limit=1) > 0
