# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.fields import Domain


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    show_bom = fields.Boolean('Show BoM column', compute='_compute_show_bom')
    bom_id = fields.Many2one(
        'mrp.bom', string='Bill of Materials', check_company=True,
        domain="[('type', '=', 'normal'), '&', '|', ('company_id', '=', company_id), ('company_id', '=', False), '|', ('product_id', '=', product_id), '&', ('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]",
        inverse='_inverse_bom_id',
    )
    bom_id_placeholder = fields.Char(compute='_compute_bom_id_placeholder')
    effective_bom_id = fields.Many2one(
        'mrp.bom', string='Effective Bill of Materials', search='_search_effective_bom_id', compute='_compute_effective_bom_id',
        store=False, help='Either the Bill of Materials set directly or the one computed to be used by this replenishment'
    )

    def _inverse_route_id(self):
        for orderpoint in self:
            if not orderpoint.route_id:
                orderpoint.bom_id = False
        super()._inverse_route_id()

    def _get_replenishment_order_notification(self):
        self.ensure_one()
        domain = Domain('orderpoint_id', 'in', self.ids)
        if self.env.context.get('written_after'):
            domain &= Domain('write_date', '>=', self.env.context.get('written_after'))
        production = self.env['mrp.production'].search(domain, limit=1)
        if production:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('The following replenishment order has been generated'),
                    'message': '%s',
                    'links': [{
                        'label': production.name,
                        'url': f'/odoo/action-mrp.action_mrp_production_form/{production.id}'
                    }],
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        return super()._get_replenishment_order_notification()

    @api.depends('bom_id', 'product_id.bom_ids.produce_delay')
    def _compute_deadline_date(self):
        """ Extend to add more depends values """
        super()._compute_deadline_date()

    def _get_lead_days_values(self):
        values = super()._get_lead_days_values()
        if self.bom_id:
            values['bom'] = self.bom_id
        return values

    @api.depends('bom_id', 'bom_id.product_uom_id', 'product_id.bom_ids', 'product_id.bom_ids.product_uom_id')
    def _compute_qty_to_order_computed(self):
        """ Extend to add more depends values """
        super()._compute_qty_to_order_computed()

    def _compute_allowed_replenishment_uom_ids(self):
        super()._compute_allowed_replenishment_uom_ids()
        for orderpoint in self:
            if 'manufacture' in orderpoint.rule_ids.mapped('action'):
                orderpoint.allowed_replenishment_uom_ids += orderpoint.product_id.bom_ids.product_uom_id

    def _compute_show_supply_warning(self):
        for orderpoint in self:
            if 'manufacture' in orderpoint.rule_ids.mapped('action') and not orderpoint.show_supply_warning:
                orderpoint.show_supply_warning = not orderpoint.product_id.bom_ids
                continue
            super(StockWarehouseOrderpoint, orderpoint)._compute_show_supply_warning()

    @api.depends('effective_route_id')
    def _compute_show_bom(self):
        manufacture_route = []
        for res in self.env['stock.rule'].search_read([('action', '=', 'manufacture')], ['route_id']):
            manufacture_route.append(res['route_id'][0])
        for orderpoint in self:
            orderpoint.show_bom = orderpoint.effective_route_id.id in manufacture_route

    def _inverse_bom_id(self):
        for orderpoint in self:
            if not orderpoint.route_id and orderpoint.bom_id:
                orderpoint.route_id = self.env['stock.rule'].search([('action', '=', 'manufacture')])[0].route_id

    @api.depends('effective_route_id', 'bom_id', 'rule_ids', 'product_id.bom_ids')
    def _compute_bom_id_placeholder(self):
        for orderpoint in self:
            default_bom = orderpoint._get_default_bom()
            orderpoint.bom_id_placeholder = default_bom.display_name if default_bom else ''

    @api.depends('effective_route_id', 'bom_id', 'rule_ids', 'product_id.bom_ids')
    def _compute_effective_bom_id(self):
        for orderpoint in self:
            orderpoint.effective_bom_id = orderpoint.bom_id if orderpoint.bom_id else orderpoint._get_default_bom()

    def _search_effective_bom_id(self, operator, value):
        boms = self.env['mrp.bom'].search([('id', operator, value)])
        orderpoints = self.env['stock.warehouse.orderpoint'].search([]).filtered(
            lambda orderpoint: orderpoint.effective_bom_id in boms
        )
        return [('id', 'in', orderpoints.ids)]

    def _compute_days_to_order(self):
        res = super()._compute_days_to_order()
        # Avoid computing rule_ids in case no manufacture rules.
        if not self.env['stock.rule'].search([('action', '=', 'manufacture')]):
            return res
        # Compute rule_ids only for orderpoint with boms
        orderpoints_with_bom = self.filtered(lambda orderpoint: orderpoint.product_id.variant_bom_ids or orderpoint.product_id.bom_ids)
        for orderpoint in orderpoints_with_bom:
            if 'manufacture' in orderpoint.rule_ids.mapped('action'):
                boms = orderpoint.bom_id or orderpoint.product_id.variant_bom_ids or orderpoint.product_id.bom_ids
                orderpoint.days_to_order = boms and boms[0].days_to_prepare_mo or 0
        return res

    def _get_default_route(self):
        route_ids = self.env['stock.rule'].search([
            ('action', '=', 'manufacture')
        ]).route_id
        route_id = self.rule_ids.route_id & route_ids
        if self.product_id.bom_ids and route_id:
            return route_id[0]
        return super()._get_default_route()

    def _get_default_bom(self):
        self.ensure_one()
        if self.show_bom:
            return self._get_default_rule()._get_matching_bom(
                self.product_id, self.company_id, {}
            )
        else:
            return self.env['mrp.bom']

    def _get_replenishment_multiple_alternative(self, qty_to_order):
        self.ensure_one()
        routes = self.effective_route_id or self.product_id.route_ids
        if not any(r.action == 'manufacture' for r in routes.rule_ids):
            return super()._get_replenishment_multiple_alternative(qty_to_order)
        bom = self.bom_id or self.env['mrp.bom']._bom_find(self.product_id, picking_type=False, bom_type='normal', company_id=self.company_id.id)[self.product_id]
        return bom.product_uom_id

    def _quantity_in_progress(self):
        bom_kits = self.env['mrp.bom']._bom_find(self.product_id, bom_type='phantom')
        bom_kit_orderpoints = {
            orderpoint: bom_kits[orderpoint.product_id]
            for orderpoint in self
            if orderpoint.product_id in bom_kits
        }
        orderpoints_without_kit = self - self.env['stock.warehouse.orderpoint'].concat(*bom_kit_orderpoints.keys())
        res = super(StockWarehouseOrderpoint, orderpoints_without_kit)._quantity_in_progress()
        for orderpoint in bom_kit_orderpoints:
            dummy, bom_sub_lines = bom_kit_orderpoints[orderpoint].explode(orderpoint.product_id, 1)
            ratios_qty_available = []
            # total = qty_available + in_progress
            ratios_total = []
            for bom_line, bom_line_data in bom_sub_lines:
                component = bom_line.product_id
                if not component.is_storable or bom_line.product_uom_id.is_zero(bom_line_data['qty']):
                    continue
                uom_qty_per_kit = bom_line_data['qty'] / bom_line_data['original_qty']
                qty_per_kit = bom_line.product_uom_id._compute_quantity(uom_qty_per_kit, bom_line.product_id.uom_id, raise_if_failure=False)
                if not qty_per_kit:
                    continue
                qty_by_product_location, dummy = component._get_quantity_in_progress(orderpoint.location_id.ids)
                qty_in_progress = qty_by_product_location.get((component.id, orderpoint.location_id.id), 0.0)
                qty_available = component.qty_available / qty_per_kit
                ratios_qty_available.append(qty_available)
                ratios_total.append(qty_available + (qty_in_progress / qty_per_kit))
            # For a kit, the quantity in progress is :
            #  (the quantity if we have received all in-progress components) - (the quantity using only available components)
            product_qty = min(ratios_total or [0]) - min(ratios_qty_available or [0])
            res[orderpoint.id] = orderpoint.product_id.uom_id._compute_quantity(product_qty, orderpoint.product_uom, round=False)

        bom_manufacture = self.env['mrp.bom']._bom_find(orderpoints_without_kit.product_id, bom_type='normal')
        bom_manufacture = self.env['mrp.bom'].concat(*bom_manufacture.values())
        # add quantities coming from draft MOs
        productions_group = self.env['mrp.production']._read_group(
            [
                ('bom_id', 'in', bom_manufacture.ids),
                ('state', '=', 'draft'),
                ('orderpoint_id', 'in', orderpoints_without_kit.ids),
                ('id', 'not in', self.env.context.get('ignore_mo_ids', [])),
            ],
            ['orderpoint_id', 'product_uom_id'],
            ['product_qty:sum'])
        for orderpoint, uom, product_qty_sum in productions_group:
            res[orderpoint.id] += uom._compute_quantity(
                product_qty_sum, orderpoint.product_uom, round=False)

        # add quantities coming from confirmed MO to be started but not finished
        # by the end of the stock forecast
        in_progress_productions = self.env['mrp.production'].search([
            ('bom_id', 'in', bom_manufacture.ids),
            ('state', '=', 'confirmed'),
            ('orderpoint_id', 'in', orderpoints_without_kit.ids),
            ('id', 'not in', self.env.context.get('ignore_mo_ids', [])),
        ])
        for prod in in_progress_productions:
            date_start, date_finished, orderpoint = prod.date_start, prod.date_finished, prod.orderpoint_id
            lead_horizon_date = datetime.combine(orderpoint.lead_horizon_date, time.max)
            if date_start <= lead_horizon_date < date_finished:
                res[orderpoint.id] += prod.product_uom_id._compute_quantity(
                        prod.product_qty, orderpoint.product_uom, round=False)
        return res

    def _prepare_procurement_values(self, date=False):
        values = super()._prepare_procurement_values(date=date)
        values['bom_id'] = self.bom_id
        return values

    def _post_process_scheduler(self):
        """ Confirm the productions only after all the orderpoints have run their
        procurement to avoid the new procurement created from the production conflict
        with them. """
        self.env['mrp.production'].sudo().search([
            ('orderpoint_id', 'in', self.ids),
            ('move_raw_ids', '!=', False),
            ('state', '=', 'draft'),
        ]).action_confirm()
        return super()._post_process_scheduler()
