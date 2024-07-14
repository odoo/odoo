# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict, namedtuple
from dateutil.relativedelta import relativedelta
from math import log10

from odoo import api, fields, models, _
from odoo.tools.date_utils import add, subtract
from odoo.tools.float_utils import float_round
from odoo.osv.expression import OR, AND
from collections import OrderedDict


class MrpProductionSchedule(models.Model):
    _name = 'mrp.production.schedule'
    _order = 'warehouse_id, product_id'
    _description = 'Schedule the production of Product in a warehouse'

    @api.model
    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)

    forecast_ids = fields.One2many('mrp.product.forecast', 'production_schedule_id',
        'Forecasted quantity at date')
    company_id = fields.Many2one('res.company', 'Company',
        default=lambda self: self.env.company)
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    product_tmpl_id = fields.Many2one('product.template', related="product_id.product_tmpl_id", readonly=True)
    product_category_id = fields.Many2one('product.category', related="product_id.product_tmpl_id.categ_id", readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM',
        related='product_id.uom_id')
    # TODO remove master: the `sequence` field was used for _order but not anymore.
    sequence = fields.Integer(related='product_id.sequence', store=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Production Warehouse',
        required=True, default=lambda self: self._default_warehouse_id())
    bom_id = fields.Many2one(
        'mrp.bom', "Bill of Materials",
        domain="[('product_tmpl_id', '=', product_tmpl_id), '|', ('product_id', '=', product_id), ('product_id', '=', False)]", check_company=True)

    forecast_target_qty = fields.Float(
        'Safety Stock Target',
        help="This is the minimum free stock you want to keep for that product at all times.")
    min_to_replenish_qty = fields.Float(
        'Minimum to Replenish',
        help="Unless the demand is 0, Odoo will always at least replenish this quantity.")
    max_to_replenish_qty = fields.Float(
        'Maximum to Replenish', default=1000,
        help="The maximum replenishment you would like to launch for each period in the MPS. Note that if the demand is higher than that amount, the remaining quantity will be transferred to the next period automatically.")
    replenish_state = fields.Selection([
        ('to_replenish', 'To Replenish'),
        ('under_replenishment', 'Under Replenishment'),
        ('excessive_replenishment', 'Excessive Replenishment')], store=False, search='_search_replenish_state',
        help="Technical field to support filtering by replenish state")

    _sql_constraints = [
        ('warehouse_product_ref_uniq', 'unique (warehouse_id, product_id)', 'The combination of warehouse and product must be unique!'),
    ]

    def _search_replenish_state(self, operator, value):
        productions_schedules = self.search([])
        productions_schedules_states = productions_schedules.get_production_schedule_view_state()

        def filter_function(f):
            if not value:
                return not (f['state'] == 'to_launch' and f['to_replenish'] or \
                    f['state'] == 'to_relaunch' or f['state'] == 'to_correct')
            return value == "to_replenish" and f['state'] == 'to_launch' and f['to_replenish'] or \
                value == "under_replenishment" and f['state'] == 'to_relaunch' or \
                value == "excessive_replenishment" and f['state'] == 'to_correct'

        ids = []
        for state in productions_schedules_states:
            if value:
                if any(map(filter_function, state['forecast_ids'])):
                    ids.append(state['id'])
            else:
                if all(map(filter_function, state['forecast_ids'])):
                    ids.append(state['id'])

        if operator == '=':
            operator = 'in'
        else:
            operator = 'not in'

        return [('id', operator, ids)]

    def action_open_actual_demand_details(self, date_str, date_start_str, date_stop_str):
        """ Open the picking list view for the actual demand for the current
        schedule.

        :param date_str: period name for the forecast sellected
        :param date_start: select incoming moves after this date
        :param date_stop: select incoming moves before this date
        :return: action values that open the picking list
        :rtype: dict
        """
        self.ensure_one()
        date_start = fields.Date.from_string(date_start_str)
        date_stop = fields.Date.from_string(date_stop_str)
        domain_moves = self._get_moves_domain(date_start, date_stop, 'outgoing')
        moves_by_date = self._get_moves_and_date(domain_moves)
        picking_ids = self._filter_moves(moves_by_date, date_start, date_stop).mapped('picking_id').ids
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'name': _('Actual Demand %s %s (%s - %s)', self.product_id.display_name, date_str, date_start_str, date_stop_str),
            'target': 'current',
            'domain': [('id', 'in', picking_ids)],
        }

    def action_open_actual_replenishment_details(self, date_str, date_start_str, date_stop_str):
        """ Open the actual replenishment details.

        :param date_str: period name for the forecast sellected
        :param date_start: select incoming moves and RFQ after this date
        :param date_stop: select incoming moves and RFQ before this date
        :return: action values that open the forecast details wizard
        :rtype: dict
        """
        date_start = fields.Date.from_string(date_start_str)
        date_stop = fields.Date.from_string(date_stop_str)
        domain_moves = self._get_moves_domain(date_start, date_stop, 'incoming')
        moves_by_date = self._get_moves_and_date(domain_moves)
        move_ids = self._filter_moves(moves_by_date, date_start, date_stop).ids

        rfq_domain = self._get_rfq_domain(date_start, date_stop)
        purchase_order_by_date = self._get_rfq_and_planned_date(rfq_domain)
        purchase_order_line_ids = self._filter_rfq(purchase_order_by_date, date_start, date_stop).ids
        name = _('Actual Replenishment %s %s (%s - %s)', self.product_id.display_name, date_str, date_start_str, date_stop_str)

        context = {
            'default_move_ids': move_ids,
            'default_purchase_order_line_ids': purchase_order_line_ids,
            'action_name': name,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_mode': 'form',
            'res_model': 'mrp.mps.forecast.details',
            'views': [(False, 'form')],
            'target': 'new',
            'context': context
        }

    def action_replenish(self, based_on_lead_time=False):
        """ Run the procurement for production schedule in self. Once the
        procurements are launched, mark the forecast as launched (only used
        for state 'to_relaunch')

        :param based_on_lead_time: 2 replenishment options exists in MPS.
        based_on_lead_time means that the procurement for self will be launched
        based on lead times.
        e.g. period are daily and the product have a manufacturing period
        of 5 days, then it will try to run the procurements for the 5 first
        period of the schedule.
        If based_on_lead_time is False then it will run the procurement for the
        first period that need a replenishment
        """
        production_schedule_states = self.get_production_schedule_view_state()
        production_schedule_states = {mps['id']: mps for mps in production_schedule_states}
        procurements = []
        forecasts_values = []
        forecasts_to_set_as_launched = self.env['mrp.product.forecast']
        for production_schedule in self:
            production_schedule_state = production_schedule_states[production_schedule.id]
            # Check for kit. If a kit and its component are both in the MPS we want to skip the
            # the kit procurement but instead only refill the components not in MPS
            bom = self.env['mrp.bom']._bom_find(
                production_schedule.product_id,
                company_id=production_schedule.company_id.id,
                bom_type='phantom')[production_schedule.product_id]
            product_ratio = []
            if bom:
                dummy, bom_lines = bom.explode(production_schedule.product_id, 1)
                product_ids = [l[0].product_id.id for l in bom_lines]
                product_ids_with_forecast = self.env['mrp.production.schedule'].search([
                    ('company_id', '=', production_schedule.company_id.id),
                    ('warehouse_id', '=', production_schedule.warehouse_id.id),
                    ('product_id', 'in', product_ids)
                ]).product_id.ids
                product_ratio += [
                    (l[0], l[0].product_qty * l[1]['qty'])
                    for l in bom_lines if l[0].product_id.id not in product_ids_with_forecast
                ]

            # Cells with values 'to_replenish' means that they are based on
            # lead times. There is at maximum one forecast by schedule with
            # 'forced_replenish', it's the cell that need a modification with
            #  the smallest start date.
            replenishment_field = based_on_lead_time and 'to_replenish' or 'forced_replenish'
            forecasts_to_replenish = filter(lambda f: f[replenishment_field], production_schedule_state['forecast_ids'])
            for forecast in forecasts_to_replenish:
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p:
                    p.date >= forecast['date_start'] and p.date <= forecast['date_stop']
                )
                extra_values = production_schedule._get_procurement_extra_values(forecast)
                quantity = forecast['replenish_qty'] - forecast['incoming_qty']
                if not bom:
                    procurements.append(self.env['procurement.group'].Procurement(
                        production_schedule.product_id,
                        quantity,
                        production_schedule.product_uom_id,
                        production_schedule.warehouse_id.lot_stock_id,
                        production_schedule.product_id.name,
                        'MPS', production_schedule.company_id, extra_values
                    ))
                else:
                    for bom_line, qty_ratio in product_ratio:
                        procurements.append(self.env['procurement.group'].Procurement(
                            bom_line.product_id,
                            quantity * qty_ratio,
                            bom_line.product_uom_id,
                            production_schedule.warehouse_id.lot_stock_id,
                            bom_line.product_id.name,
                            'MPS', production_schedule.company_id, extra_values
                        ))

                if existing_forecasts:
                    forecasts_to_set_as_launched |= existing_forecasts
                else:
                    forecasts_values.append({
                        'forecast_qty': 0,
                        'date': forecast['date_stop'],
                        'procurement_launched': True,
                        'production_schedule_id': production_schedule.id
                    })
        if procurements:
            self.env['procurement.group'].with_context(skip_lead_time=True).run(procurements)

        forecasts_to_set_as_launched.write({
            'procurement_launched': True,
        })
        if forecasts_values:
            self.env['mrp.product.forecast'].create(forecasts_values)

    @api.model
    def get_mps_view_state(self, domain=False, offset=0, limit=False):
        """ Return the global information about MPS and a list of production
        schedules values with the domain.

        :param domain: domain for mrp.production.schedule
        :return: values used by the client action in order to render the MPS.
            - dates: list of period name
            - production_schedule_ids: list of production schedules values
            - manufacturing_period: list of periods (days, months or years)
            - company_id: user current company
            - groups: company settings that hide/display different rows
        :rtype: dict
        """
        productions_schedules = self.env['mrp.production.schedule'].search(domain or [], offset=offset, limit=limit)
        count = self.env['mrp.production.schedule'].search_count(domain or [])
        productions_schedules_states = productions_schedules.get_production_schedule_view_state()
        company_groups = self.env.company.read([
            'mrp_mps_show_starting_inventory',
            'mrp_mps_show_demand_forecast',
            'mrp_mps_show_indirect_demand',
            'mrp_mps_show_actual_demand',
            'mrp_mps_show_to_replenish',
            'mrp_mps_show_actual_replenishment',
            'mrp_mps_show_safety_stock',
            'mrp_mps_show_available_to_promise',
            'mrp_mps_show_actual_demand_year_minus_1',
            'mrp_mps_show_actual_demand_year_minus_2',
        ])
        return {
            'dates': self.env.company._date_range_to_str(),
            'production_schedule_ids': productions_schedules_states,
            'manufacturing_period': self.env.company.manufacturing_period,
            'company_id': self.env.company.id,
            'groups': company_groups,
            'count': count,
        }

    @api.model_create_multi
    def create(self, vals_list):
        """ If the BoM is pass at the creation, create MPS for its components """
        existing_mps = []
        for i, vals in enumerate(vals_list):
            # Allow to add components of a BoM for MPS already created
            if vals.get('bom_id'):
                mps = self.search([
                    ('product_id', '=', vals['product_id']),
                    ('warehouse_id', '=', vals.get('warehouse_id', self._default_warehouse_id().id)),
                    ('company_id', '=', vals.get('company_id', self.env.company.id)),
                ], limit=1)
                if mps:
                    mps.bom_id = vals.get('bom_id')
                    existing_mps.append((i, mps.id))

        for i_remove, __ in reversed(existing_mps):
            del vals_list[i_remove]

        mps = super().create(vals_list)

        mps_ids = mps.ids
        for i, mps_id in existing_mps:
            mps_ids.insert(i, mps_id)
        mps = self.browse(mps_ids)

        components_list = set()
        components_vals = []
        for record in mps:
            bom = record.bom_id
            if not bom:
                continue
            dummy, components = bom.explode(record.product_id, 1)
            for component in components:
                if component[0].product_id.type != 'consu':
                    components_list.add((component[0].product_id.id, record.warehouse_id.id, record.company_id.id))
        for component in components_list:
            if self.env['mrp.production.schedule'].search([
                ('product_id', '=', component[0]),
                ('warehouse_id', '=', component[1]),
                ('company_id', '=', component[2]),
            ], limit=1):
                continue
            components_vals.append({
                'product_id': component[0],
                'warehouse_id': component[1],
                'company_id': component[2]
            })
        if components_vals:
            self.env['mrp.production.schedule'].create(components_vals)
        return mps

    def get_production_schedule_view_state(self):
        """ Prepare and returns the fields used by the MPS client action.
        For each schedule returns the fields on the model. And prepare the cells
        for each period depending the manufacturing period set on the company.
        The forecast cells contains the following information:
        - forecast_qty: Demand forecast set by the user
        - date_start: First day of the current period
        - date_stop: Last day of the current period
        - replenish_qty: The quantity to replenish for the current period. It
        could be computed or set by the user.
        - replenish_qty_updated: The quantity to replenish has been set manually
        by the user.
        - starting_inventory_qty: During the first period, the quantity
        available. After, the safety stock from previous period.
        - incoming_qty: The incoming moves and RFQ for the specified product and
        warehouse during the current period.
        - outgoing_qty: The outgoing moves quantity.
        - indirect_demand_qty: On manufacturing a quantity to replenish could
        require a need for a component in another schedule. e.g. 2 product A in
        order to create 1 product B. If the replenish quantity for product B is
        10, it will need 20 product A.
        - safety_stock_qty:
        starting_inventory_qty - forecast_qty - indirect_demand_qty + replenish_qty
        """
        company_id = self.env.company
        date_range = company_id._get_date_range()
        date_range_year_minus_1 = company_id._get_date_range(years=1)
        date_range_year_minus_2 = company_id._get_date_range(years=2)

        # We need to get the schedule that impact the schedules in self. Since
        # the state is not saved, it needs to recompute the quantity to
        # replenish of finished products. It will modify the indirect
        # demand and replenish_qty of schedules in self.
        schedules_to_compute = self.env['mrp.production.schedule'].browse(self.get_impacted_schedule()) | self

        # Dependencies between schedules
        indirect_demand_trees = schedules_to_compute._get_indirect_demand_tree()

        indirect_ratio_mps = schedules_to_compute._get_indirect_demand_ratio_mps(indirect_demand_trees)

        # Get the schedules that do not depends from other in first position in
        # order to compute the schedule state only once.
        indirect_demand_order = schedules_to_compute._get_indirect_demand_order(indirect_demand_trees)
        indirect_demand_qty = defaultdict(float)
        incoming_qty, incoming_qty_done = self._get_incoming_qty(date_range)
        outgoing_qty, outgoing_qty_done = self._get_outgoing_qty(date_range)
        dummy, outgoing_qty_year_minus_1 = self._get_outgoing_qty(date_range_year_minus_1)
        dummy, outgoing_qty_year_minus_2 = self._get_outgoing_qty(date_range_year_minus_2)
        read_fields = [
            'forecast_target_qty',
            'min_to_replenish_qty',
            'max_to_replenish_qty',
            'product_id',
        ]
        if self.env.user.has_group('stock.group_stock_multi_warehouses'):
            read_fields.append('warehouse_id')
        if self.env.user.has_group('uom.group_uom'):
            read_fields.append('product_uom_id')
        production_schedule_states = schedules_to_compute.read(read_fields)
        production_schedule_states_by_id = {mps['id']: mps for mps in production_schedule_states}
        for production_schedule in indirect_demand_order:
            # Bypass if the schedule is only used in order to compute indirect
            # demand.
            rounding = production_schedule.product_id.uom_id.rounding
            lead_time = production_schedule._get_lead_times()
            # Ignore "Days to Supply Components" when set demand for components since it's normally taken care by the
            # components themselves
            lead_time_ignore_components = lead_time - production_schedule.bom_id.days_to_prepare_mo
            production_schedule_state = production_schedule_states_by_id[production_schedule['id']]
            if production_schedule in self:
                procurement_date = add(fields.Date.today(), days=lead_time)
                precision_digits = max(0, int(-(log10(production_schedule.product_uom_id.rounding))))
                production_schedule_state['precision_digits'] = precision_digits
                production_schedule_state['forecast_ids'] = []

            starting_inventory_qty = production_schedule.product_id.with_context(warehouse=production_schedule.warehouse_id.id).qty_available
            if len(date_range):
                starting_inventory_qty -= incoming_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                starting_inventory_qty += outgoing_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)

            for index, (date_start, date_stop) in enumerate(date_range):
                forecast_values = {}
                key = ((date_start, date_stop), production_schedule.product_id, production_schedule.warehouse_id)
                key_y_1 = (date_range_year_minus_1[index], *key[1:])
                key_y_2 = (date_range_year_minus_2[index], *key[1:])
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p: p.date >= date_start and p.date <= date_stop)
                if production_schedule in self:
                    forecast_values['date_start'] = date_start
                    forecast_values['date_stop'] = date_stop
                    forecast_values['incoming_qty'] = float_round(incoming_qty.get(key, 0.0) + incoming_qty_done.get(key, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty'] = float_round(outgoing_qty.get(key, 0.0) + outgoing_qty_done.get(key, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty_year_minus_1'] = float_round(outgoing_qty_year_minus_1.get(key_y_1, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty_year_minus_2'] = float_round(outgoing_qty_year_minus_2.get(key_y_2, 0.0), precision_rounding=rounding)

                forecast_values['indirect_demand_qty'] = float_round(indirect_demand_qty.get(key, 0.0), precision_rounding=rounding, rounding_method='UP')
                replenish_qty_updated = False
                if existing_forecasts:
                    forecast_values['forecast_qty'] = float_round(sum(existing_forecasts.mapped('forecast_qty')), precision_rounding=rounding)
                    forecast_values['replenish_qty'] = float_round(sum(existing_forecasts.mapped('replenish_qty')), precision_rounding=rounding)

                    # Check if the to replenish quantity has been manually set or
                    # if it needs to be computed.
                    replenish_qty_updated = any(existing_forecasts.mapped('replenish_qty_updated'))
                    forecast_values['replenish_qty_updated'] = replenish_qty_updated
                else:
                    forecast_values['forecast_qty'] = 0.0

                if not replenish_qty_updated:
                    replenish_qty = production_schedule._get_replenish_qty(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'])
                    forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                    forecast_values['replenish_qty_updated'] = False

                forecast_values['starting_inventory_qty'] = float_round(starting_inventory_qty, precision_rounding=rounding)
                forecast_values['safety_stock_qty'] = float_round(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'] + forecast_values['replenish_qty'], precision_rounding=rounding)

                if production_schedule in self:
                    production_schedule_state['forecast_ids'].append(forecast_values)
                starting_inventory_qty = forecast_values['safety_stock_qty']
                if not forecast_values['replenish_qty']:
                    continue
                # Set the indirect demand qty for children schedules.
                for (product, ratio) in indirect_ratio_mps[(production_schedule.warehouse_id, production_schedule.product_id)].items():
                    related_date = max(subtract(date_start, days=lead_time_ignore_components), fields.Date.today())
                    index = next(i for i, (dstart, dstop) in enumerate(date_range) if related_date <= dstart or (related_date >= dstart and related_date <= dstop))
                    related_key = (date_range[index], product, production_schedule.warehouse_id)
                    indirect_demand_qty[related_key] += ratio * forecast_values['replenish_qty']

            if production_schedule in self:
                # The state is computed after all because it needs the final
                # quantity to replenish.
                forecasts_state = production_schedule._get_forecasts_state(production_schedule_states_by_id, date_range, procurement_date)
                forecasts_state = forecasts_state[production_schedule.id]
                for index, forecast_state in enumerate(forecasts_state):
                    production_schedule_state['forecast_ids'][index].update(forecast_state)

                # The purpose is to hide indirect demand row if the schedule do not
                # depends from another.
                has_indirect_demand = any(forecast['indirect_demand_qty'] != 0 for forecast in production_schedule_state['forecast_ids'])
                production_schedule_state['has_indirect_demand'] = has_indirect_demand
        return [production_schedule_states_by_id[_id] for _id in self.ids if _id in production_schedule_states_by_id]

    def get_impacted_schedule(self, domain=False):
        """ When the user modify the demand forecast on a schedule. The new
        replenish quantity is computed from schedules that use the product in
        self as component (no matter at which BoM level). It will also modify
        the replenish quantity on self that will impact the schedule that use
        the product in self as a finished product.

        :param domain: filter supplied and supplying schedules with the domain
        :return ids of supplied and supplying schedules
        :rtype list
        """
        if not domain:
            domain = []

        def _used_in_bom(products, related_products):
            """ Bottom up from bom line to finished products in order to get
            all the finished products that use 'products' as component.
            """
            if not products:
                return related_products
            boms = products.bom_line_ids.mapped('bom_id')
            products = boms.mapped('product_id') | boms.mapped('product_tmpl_id.product_variant_ids')
            products -= related_products
            related_products |= products
            return _used_in_bom(products, related_products)

        supplying_mps = self.env['mrp.production.schedule'].search(
            AND([domain, [
                ('warehouse_id', 'in', self.mapped('warehouse_id').ids),
                ('product_id', 'in', _used_in_bom(self.mapped('product_id'), self.env['product.product']).ids)
            ]]))

        def _use_boms(products, related_products):
            """ Explore bom line from products's BoMs in order to get components
            used.
            """
            if not products:
                return related_products
            components = products.mapped(lambda product: product.bom_ids.bom_line_ids.filtered(lambda line: not line._skip_bom_line(product)).mapped('product_id'))

            components -= related_products
            related_products |= components
            return _use_boms(components, related_products)

        supplied_mps = self.env['mrp.production.schedule'].search(
            AND([domain, [
                ('warehouse_id', 'in', self.mapped('warehouse_id').ids),
                ('product_id', 'in', _use_boms(self.mapped('product_id'), self.env['product.product']).ids)
            ]]))
        return (supplying_mps | supplied_mps).ids

    def remove_replenish_qty(self, date_index):
        """ Remove the quantity to replenish on the forecast cell.

        param date_index: index of the period used to find start and stop date
        where the manual replenish quantity should be remove.
        """
        date_start, date_stop = self.company_id._get_date_range()[date_index]
        forecast_ids = self.forecast_ids.filtered(lambda f:
            f.date >= date_start and f.date <= date_stop)
        forecast_ids.write({
            'replenish_qty': 0.0,
            'replenish_qty_updated': False,
        })
        return True

    def set_forecast_qty(self, date_index, quantity):
        """ Save the forecast quantity:

        params quantity: The new total forecasted quantity
        params date_index: The manufacturing period
        """
        # Get the last date of current period
        self.ensure_one()
        date_start, date_stop = self.company_id._get_date_range()[date_index]
        existing_forecast = self.forecast_ids.filtered(lambda f:
            f.date >= date_start and f.date <= date_stop)
        quantity = float_round(float(quantity), precision_rounding=self.product_uom_id.rounding)
        quantity_to_add = quantity - sum(existing_forecast.mapped('forecast_qty'))
        if existing_forecast:
            new_qty = existing_forecast[0].forecast_qty + quantity_to_add
            new_qty = float_round(new_qty, precision_rounding=self.product_uom_id.rounding)
            existing_forecast[0].write({'forecast_qty': new_qty})
        else:
            existing_forecast.create({
                'forecast_qty': quantity,
                'date': date_stop,
                'replenish_qty': 0,
                'production_schedule_id': self.id
            })
        return True

    def set_replenish_qty(self, date_index, quantity):
        """ Save the replenish quantity and mark the cells as manually updated.

        params quantity: The new quantity to replenish
        params date_index: The manufacturing period
        """
        # Get the last date of current period
        self.ensure_one()
        date_start, date_stop = self.company_id._get_date_range()[date_index]
        existing_forecast = self.forecast_ids.filtered(lambda f:
            f.date >= date_start and f.date <= date_stop)
        quantity = float_round(float(quantity), precision_rounding=self.product_uom_id.rounding)
        quantity_to_add = quantity - sum(existing_forecast.mapped('replenish_qty'))
        if existing_forecast:
            new_qty = existing_forecast[0].replenish_qty + quantity_to_add
            new_qty = float_round(new_qty, precision_rounding=self.product_uom_id.rounding)
            existing_forecast[0].write({
                'replenish_qty': new_qty,
                'replenish_qty_updated': True
            })
        else:
            existing_forecast.create({
                'forecast_qty': 0,
                'date': date_stop,
                'replenish_qty': quantity,
                'replenish_qty_updated': True,
                'production_schedule_id': self.id
            })
        return True

    def _filter_moves(self, moves_by_date, date_start, date_stop):
        return self.env['stock.move'].concat(*[m[0] for m in moves_by_date if m[1] >= date_start and m[1] <= date_stop])

    def _filter_rfq(self, rfq_by_date_planned, date_start, date_stop):
        return self.env['purchase.order.line'].concat(*[pl[0] for pl in rfq_by_date_planned if pl[1] >= date_start and pl[1] <= date_stop])

    def _get_procurement_extra_values(self, forecast_values):
        """ Extra values that could be added in the vals for procurement.

        return values pass to the procurement run method.
        rtype dict
        """
        return {
            'date_planned': forecast_values['date_start'],
            'warehouse_id': self.warehouse_id,
        }

    def _get_forecasts_state(self, production_schedule_states, date_range, procurement_date):
        """ Return the state for each forecast cells.
        - to_relaunch: A procurement has been launched for the same date range
        but a replenish modification require a new procurement.
        - to_correct: The actual replenishment is greater than planned, the MPS
        should be updated in order to match reality.
        - launched: Nothing todo. Either the cell is in the lead time range but
        the forecast match the actual replenishment. Or a foreced replenishment
        happens but the forecast and the actual demand still the same.
        - to_launch: The actual replenishment is lower than forecasted.

        It also add a tag on cell in order to:
        - to_replenish: The cell is to launch and it needs to be runned in order
        to arrive on time due to lead times.
        - forced_replenish: Cell to_launch or to_relaunch with the smallest
        period

        param production_schedule_states: schedules with a state to compute
        param date_range: list of period where a state should be computed
        param procurement_date: today + lead times for products in self
        return: the state for each time slot in date_range for each schedule in
        production_schedule_states
        rtype: dict
        """
        forecasts_state = defaultdict(list)
        for production_schedule in self:
            forecast_values = production_schedule_states[production_schedule.id]['forecast_ids']
            forced_replenish = True
            for index, (date_start, date_stop) in enumerate(date_range):
                forecast_state = {}
                forecast_value = forecast_values[index]
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p: p.date >= date_start and p.date <= date_stop)
                procurement_launched = any(existing_forecasts.mapped('procurement_launched'))

                replenish_qty = forecast_value['replenish_qty']
                incoming_qty = forecast_value['incoming_qty']
                if incoming_qty < replenish_qty and procurement_launched:
                    state = 'to_relaunch'
                elif incoming_qty > replenish_qty:
                    state = 'to_correct'
                elif incoming_qty == replenish_qty and (date_start <= procurement_date or procurement_launched):
                    state = 'launched'
                else:
                    state = 'to_launch'
                forecast_state['state'] = state

                forecast_state['forced_replenish'] = False
                forecast_state['to_replenish'] = False

                procurement_qty = replenish_qty - incoming_qty
                if forecast_state['state'] not in ('launched', 'to_correct') and procurement_qty > 0:
                    if date_start <= procurement_date:
                        forecast_state['to_replenish'] = True
                    if forced_replenish:
                        forecast_state['forced_replenish'] = True
                        forced_replenish = False

                forecasts_state[production_schedule.id].append(forecast_state)
        return forecasts_state

    def _get_lead_times(self):
        """ Get the lead time for each product in self. The lead times are
        based on rules lead times + produce delay or supplier info delay.
        """
        rules = self.product_id._get_rules_from_location(self.warehouse_id.lot_stock_id)
        return rules._get_lead_days(self.product_id, bom=self.bom_id)[0]['total_delay']

    def _get_replenish_qty(self, after_forecast_qty):
        """ Modify the quantity to replenish depending the min/max and targeted
        quantity for safety stock.

        param after_forecast_qty: The quantity to replenish in order to reach a
        safety stock of 0.
        return: quantity to replenish
        rtype: float
        """
        optimal_qty = self.forecast_target_qty - after_forecast_qty

        if optimal_qty > self.max_to_replenish_qty:
            replenish_qty = self.max_to_replenish_qty
        elif optimal_qty <= 0:
            replenish_qty = 0
        elif optimal_qty < self.min_to_replenish_qty:
            replenish_qty = self.min_to_replenish_qty
        else:
            replenish_qty = optimal_qty

        return replenish_qty

    def _get_incoming_qty(self, date_range):
        """ Get the incoming quantity from RFQ and existing moves.

        param: list of time slots used in order to group incoming quantity.
        return: a dict with as key a production schedule and as values a list
        of incoming quantity for each date range.
        """
        incoming_qty = defaultdict(float)
        incoming_qty_done = defaultdict(float)
        after_date = date_range[0][0]
        before_date = date_range[-1][1]
        # Get quantity in RFQ
        rfq_domain = self._get_rfq_domain(after_date, before_date)
        rfq_lines_date_planned = self._get_rfq_and_planned_date(rfq_domain, order='date_planned')
        rfq_lines_date_planned = sorted(rfq_lines_date_planned, key=lambda i: i[1])
        index = 0
        for (line, date_planned) in rfq_lines_date_planned:
            # There are cases when we want to consider rfq_lines where their date_planned occurs before the after_date
            # if lead times make their stock arrive at a relevant time. Therefore we need to ignore the lines that have
            # date_planned + lead time < after_date
            if date_planned < after_date:
                continue
            # Skip to the next time range if the planned date is not in the
            # current time interval.

            while not (date_range[index][0] <= date_planned and
                       date_range[index][1] >= date_planned):
                index += 1
            quantity = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            incoming_qty[date_range[index], line.product_id, line.order_id.picking_type_id.warehouse_id] += quantity

        # Get quantity on incoming moves
        # TODO: issue since it will use one search by move. Should use a
        # read_group with a group by location.
        domain_moves = self._get_moves_domain(after_date, before_date, 'incoming')
        stock_moves_and_date = self._get_moves_and_date(domain_moves)
        stock_moves_and_date = sorted(stock_moves_and_date, key=lambda m: m[1])
        index = 0
        for (move, date) in stock_moves_and_date:
            if date < after_date or date > before_date:
                continue
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= date and date_range[index][1] >= date):
                index += 1
            key = (date_range[index], move.product_id, move.location_dest_id.warehouse_id)
            if move.state == 'done':
                incoming_qty_done[key] += move.product_qty
            else:
                incoming_qty[key] += move.product_qty

        return incoming_qty, incoming_qty_done

    def _get_indirect_demand_order(self, indirect_demand_trees):
        """ return a new order for record in self. The order returned ensure
        that the indirect demand from a record in the set could only be modified
        by a record before it. The purpose of this function is to define the
        states of multiple schedules only once by schedule and avoid to
        recompute a state because its indirect demand was a depend from another
        schedule.
        """
        product_ids = self.mapped('product_id')

        def _get_pre_order(node):
            order_list = []
            if node.product in product_ids:
                order_list.append(node.product)
            for child in node.children:
                order_list += _get_pre_order(child)
            return order_list

        product_order_by_tree = []
        for node in indirect_demand_trees:
            product_order_by_tree += _get_pre_order(node)

        product_order = OrderedDict()
        for product in reversed(product_order_by_tree):
            if product not in product_order:
                product_order[product] = True

        mps_order_by_product = defaultdict(lambda: self.env['mrp.production.schedule'])
        for mps in self:
            mps_order_by_product[mps.product_id] |= mps

        mps_order = self.env['mrp.production.schedule']
        for product in reversed(product_order.keys()):
            mps_order |= mps_order_by_product[product]
        return mps_order

    def _get_indirect_demand_ratio_mps(self, indirect_demand_trees):
        """ Return {(warehouse, product): {product: ratio}} dict containing the indirect ratio
        between two products.
        """
        by_warehouse_mps = defaultdict(lambda: self.env['mrp.production.schedule'])
        for mps in self:
            by_warehouse_mps[mps.warehouse_id] |= mps

        result = defaultdict(lambda: defaultdict(float))
        for warehouse_id, other_mps in by_warehouse_mps.items():
            other_mps_product_ids = other_mps.mapped('product_id')
            subtree_visited = set()

            def _dfs_ratio_search(current_node, ratio, node_indirect=False):
                for child in current_node.children:
                    if child.product in other_mps_product_ids:
                        result[(warehouse_id, node_indirect and node_indirect.product or current_node.product)][child.product] += ratio * child.ratio
                        if child.product in subtree_visited:  # Don't visit the same subtree twice
                            continue
                        subtree_visited.add(child.product)
                        _dfs_ratio_search(child, 1.0, node_indirect=False)
                    else:  # Hidden Bom => continue DFS and set node_indirect
                        _dfs_ratio_search(child, child.ratio * ratio, node_indirect=current_node)

            for tree in indirect_demand_trees:
                _dfs_ratio_search(tree, tree.ratio)

        return result

    def _get_indirect_demand_tree(self):
        """ Get the tree architecture for all the BoM and BoM line that are
        related to production schedules in self. The purpose of the tree:
        - Easier traversal than with BoM and BoM lines.
        - Allow to determine the schedules evaluation order. (compute the
        schedule without indirect demand first)
        It also made the link between schedules even if some intermediate BoM
        levels are hidden. (e.g. B1 -1-> B2 -1-> B3, schedule for B1 and B3
        are linked even if the schedule for B2 does not exist.)
        Return a list of namedtuple that represent on top the schedules without
        indirect demand and on lowest leaves the schedules that are the most
        influenced by the others.
        """
        bom_by_product = self.env['mrp.bom']._bom_find(self.product_id)

        Node = namedtuple('Node', ['product', 'ratio', 'children'])
        indirect_demand_trees = {}
        product_visited = {}

        def _get_product_tree(product, ratio):
            product_tree = product_visited.get(product)
            if product_tree:
                return Node(product_tree.product, ratio, product_tree.children)

            product_tree = Node(product, ratio, [])
            product_bom = bom_by_product.get(product)
            if product not in bom_by_product and not product_bom:
                product_bom = self.env['mrp.bom']._bom_find(product)[product]
            for line in product_bom.bom_line_ids:
                if line._skip_bom_line(product):
                    continue
                line_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
                bom_qty = line.bom_id.product_uom_id._compute_quantity(line.bom_id.product_qty, line.bom_id.product_tmpl_id.uom_id)
                ratio = line_qty / bom_qty
                tree = _get_product_tree(line.product_id, ratio)
                product_tree.children.append(tree)
                if line.product_id in indirect_demand_trees:
                    del indirect_demand_trees[line.product_id]
            product_visited[product] = product_tree
            return product_tree

        for product in self.mapped('product_id'):
            if product in product_visited:
                continue
            indirect_demand_trees[product] = _get_product_tree(product, 1.0)

        return [tree for tree in indirect_demand_trees.values()]

    def _get_moves_domain(self, date_start, date_stop, type):
        """ Return domain for incoming or outgoing moves """
        if not self:
            return [('id', '=', False)]
        location = type == 'incoming' and 'location_dest_id' or 'location_id'
        location_dest = type == 'incoming' and 'location_id' or 'location_dest_id'
        domain = []
        common_domain = [
            ('state', 'not in', ['cancel', 'draft']),
            (location + '.usage', '!=', 'inventory'),
            '|',
                (location_dest + '.usage', 'not in', ('internal', 'inventory')),
                '&',
                (location_dest + '.usage', '=', 'internal'),
                '!',
                    (location_dest, 'child_of', self.mapped('warehouse_id.view_location_id').ids),
            ('is_inventory', '=', False),
            ('date', '<=', date_stop),
        ]
        groupby_delay = defaultdict(list)
        for schedule in self:
            rules = schedule.product_id._get_rules_from_location(schedule.warehouse_id.lot_stock_id)
            lead_days, dummy = rules.filtered(lambda r: r.action not in ['buy', 'manufacture'])._get_lead_days(schedule.product_id)
            delay = lead_days['total_delay']
            groupby_delay[delay].append((schedule.product_id, schedule.warehouse_id))
        for delay in groupby_delay:
            products, warehouses = zip(*groupby_delay[delay])
            warehouses = self.env['stock.warehouse'].concat(*warehouses)
            products = self.env['product.product'].concat(*products)
            specific_domain = [
                (location, 'child_of', warehouses.mapped('view_location_id').ids),
                ('product_id', 'in', products.ids),
                ('date', '>=', date_start - relativedelta(days=delay)),
            ]
            domain = OR([domain, AND([common_domain, specific_domain])])
        return domain

    @api.model
    def _get_dest_moves_delay(self, move, delay=0):
        if move.origin_returned_move_id:
            return delay
        elif not move.move_dest_ids:
            return delay + move.rule_id.delay
        else:
            delays = []
            additional_delay = move.rule_id.delay
            for move_dest in move.move_dest_ids:
                delays.append(self._get_dest_moves_delay(
                    move_dest, delay=delay + additional_delay))
            return max(delays)

    def _get_moves_and_date(self, moves_domain, order=False):
        moves = self.env['stock.move'].search(moves_domain, order=order)
        res_moves = []
        for move in moves:
            delay = self._get_dest_moves_delay(move)
            date = fields.Date.to_date(move.date) + relativedelta(days=delay)
            res_moves.append((move, date))
        return res_moves

    def _get_outgoing_qty(self, date_range):
        """ Get the outgoing quantity from existing moves.
        return a dict with as key a production schedule and as values a list
        of outgoing quantity for each date range.
        """
        outgoing_qty = defaultdict(float)
        outgoing_qty_done = defaultdict(float)
        after_date = date_range[0][0]
        before_date = date_range[-1][1]
        # Get quantity on incoming moves

        domain_moves = self._get_moves_domain(after_date, before_date, 'outgoing')
        domain_moves = AND([domain_moves, [('raw_material_production_id', '=', False)]])
        stock_moves_by_date = self._get_moves_and_date(domain_moves)
        stock_moves_by_date = sorted(stock_moves_by_date, key=lambda m: m[1])
        index = 0
        for (move, date) in stock_moves_by_date:
            # There are cases when we want to consider moves where their (scheduled) date occurs before the after_date
            # if lead times make their stock delivery at a relevant time. Therefore we need to ignore the lines that have
            # date + lead time < after_date. Similar logic with before_date
            if date < after_date or date > before_date:
                continue
            # Skip to the next time range if the planned date is not in the
            # current time interval.
            while not (date_range[index][0] <= date and date_range[index][1] >= date):
                index += 1
            key = (date_range[index], move.product_id, move.location_id.warehouse_id)
            if move.state == 'done':
                outgoing_qty_done[key] += move.product_uom_qty
            else:
                outgoing_qty[key] += move.product_uom_qty

        return outgoing_qty, outgoing_qty_done

    def _get_rfq_domain(self, date_start, date_stop):
        """ Return a domain used to compute the incoming quantity for a given
        product/warehouse/company.

        :param date_start: start date of the forecast domain
        :param date_stop: end date of the forecast domain
        """
        if not self:
            return [('id', '=', False)]
        domain = []
        common_domain = [
            ('state', 'in', ('draft', 'sent', 'to approve')),
            ('date_planned', '<=', date_stop)
        ]
        groupby_delay = defaultdict(list)
        for schedule in self:
            rules = schedule.product_id._get_rules_from_location(schedule.warehouse_id.lot_stock_id)
            lead_days, dummy = rules._get_lead_days(schedule.product_id)
            delay = lead_days['total_delay']
            groupby_delay[delay].append((schedule.product_id, schedule.warehouse_id))

        for delay in groupby_delay:
            products, warehouses = zip(*groupby_delay[delay])
            warehouses = self.env['stock.warehouse'].concat(*warehouses)
            products = self.env['product.product'].concat(*products)
            specific_domain = [
                ('order_id.picking_type_id.default_location_dest_id', 'child_of', warehouses.mapped('view_location_id').ids),
                ('product_id', 'in', products.ids),
                ('date_planned', '>=', date_start - relativedelta(days=delay)),
            ]
            domain = OR([domain, AND([common_domain, specific_domain])])
        return domain

    def _get_rfq_and_planned_date(self, rfq_domain, order=False):
        purchase_lines = self.env['purchase.order.line'].search(rfq_domain, order=order)
        res_purchase_lines = []
        for line in purchase_lines:
            if not line.move_dest_ids:
                res_purchase_lines.append((line, fields.Date.to_date(line.date_planned)))
                continue
            delay = max(map(self._get_dest_moves_delay, line.move_dest_ids))
            date = fields.Date.to_date(line.date_planned) + relativedelta(days=delay)
            res_purchase_lines.append((line, date))

        return res_purchase_lines

class MrpProductForecast(models.Model):
    _name = 'mrp.product.forecast'
    _order = 'date'
    _description = 'Product Forecast at Date'

    production_schedule_id = fields.Many2one('mrp.production.schedule',
        required=True, ondelete='cascade')
    date = fields.Date('Date', required=True)

    forecast_qty = fields.Float('Demand Forecast')
    replenish_qty = fields.Float('To Replenish')
    replenish_qty_updated = fields.Boolean('Replenish_qty has been manually updated')

    procurement_launched = fields.Boolean('Procurement has been run for this forecast')
