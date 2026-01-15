# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.fields import Domain, Command
from odoo.tools import OrderedSet


class StockRule(models.Model):
    _inherit = 'stock.rule'
    action = fields.Selection(selection_add=[
        ('manufacture', 'Manufacture')
    ], ondelete={'manufacture': 'cascade'})

    def _get_message_dict(self):
        message_dict = super(StockRule, self)._get_message_dict()
        source, destination, direct_destination, operation = self._get_message_values()
        manufacture_message = _('When products are needed in <b>%s</b>, <br/> a manufacturing order is created to fulfill the need.', destination)
        if self.location_src_id:
            manufacture_message += _(' <br/><br/> The components will be taken from <b>%s</b>.', source)
        if direct_destination and not self.location_dest_from_rule:
            manufacture_message += _(' <br/><br/> The manufactured products will be moved towards <b>%(destination)s</b>, <br/> as specified from <b>%(operation)s</b> destination.', destination=direct_destination, operation=operation)
        message_dict['manufacture'] = manufacture_message
        return message_dict

    def _compute_picking_type_code_domain(self):
        super()._compute_picking_type_code_domain()
        for rule in self:
            if rule.action == 'manufacture':
                rule.picking_type_code_domain = rule.picking_type_code_domain or [] + ['mrp_operation']

    def _should_auto_confirm_procurement_mo(self, p):
        if not p.move_raw_ids:
            return (not p.workorder_ids and (p.orderpoint_id or p.move_dest_ids.procure_method == 'make_to_stock'))
        return not p.orderpoint_id

    @api.model
    def run(self, procurements, raise_user_error=True):
        """ If 'run' is called on a kit, this override is made in order to call
        the original 'run' method with the values of the components of that kit.
        """
        procurements_without_kit = []
        product_by_company = defaultdict(OrderedSet)
        for procurement in procurements:
            product_by_company[procurement.company_id].add(procurement.product_id.id)
        kits_by_company = {
            company: self.env['mrp.bom']._bom_find(self.env['product.product'].browse(product_ids), company_id=company.id, bom_type='phantom')
            for company, product_ids in product_by_company.items()
        }
        for procurement in procurements:
            bom_kit = kits_by_company[procurement.company_id].get(procurement.product_id)
            if bom_kit:
                order_qty = procurement.product_uom._compute_quantity(procurement.product_qty, bom_kit.product_uom_id, round=False)
                qty_to_produce = (order_qty / bom_kit.product_qty)
                _dummy, bom_sub_lines = bom_kit.explode(procurement.product_id, qty_to_produce, never_attribute_values=procurement.values.get("never_product_template_attribute_value_ids"))
                for bom_line, bom_line_data in bom_sub_lines:
                    bom_line_uom = bom_line.product_uom_id
                    quant_uom = bom_line.product_id.uom_id
                    # recreate dict of values since each child has its own bom_line_id
                    values = dict(procurement.values, bom_line_id=bom_line.id)
                    component_qty, procurement_uom = bom_line_uom._adjust_uom_quantities(bom_line_data['qty'], quant_uom)
                    procurements_without_kit.append(self.env['stock.rule'].Procurement(
                        bom_line.product_id, component_qty, procurement_uom,
                        procurement.location_id, procurement.name,
                        procurement.origin, procurement.company_id, values))
            else:
                procurements_without_kit.append(procurement)
        return super().run(procurements_without_kit, raise_user_error=raise_user_error)

    def _filter_warehouse_routes(self, product, warehouses, route):
        if any(rule.action == 'manufacture' for rule in route.rule_ids):
            if any(bom.type == 'normal' for bom in product.bom_ids):
                return super()._filter_warehouse_routes(product, warehouses, route)
            return False
        return super()._filter_warehouse_routes(product, warehouses, route)

    @api.model
    def _run_manufacture(self, procurements):
        new_productions_values_by_company = defaultdict(lambda: defaultdict(list))
        for procurement, rule in procurements:
            if procurement.product_uom.compare(procurement.product_qty, 0) <= 0:
                # If procurement contains negative quantity, don't create a MO that would be for a negative value.
                continue
            bom = rule._get_matching_bom(procurement.product_id, procurement.company_id, procurement.values)

            mo = self.env['mrp.production']
            if procurement.origin != 'MPS':
                domain = rule._make_mo_get_domain(procurement, bom)
                mo = self.env['mrp.production'].sudo().search(domain, limit=1)
            is_batch_size = bom and bom.enable_batch_size
            if not mo or is_batch_size:
                procurement_qty = procurement.product_qty
                batch_size = bom.product_uom_id._compute_quantity(bom.batch_size, procurement.product_uom) if is_batch_size else procurement_qty
                vals = rule._prepare_mo_vals(*procurement, bom)
                while procurement.product_uom.compare(procurement_qty, 0) > 0:
                    new_productions_values_by_company[procurement.company_id.id]['values'].append({
                        **vals,
                        'product_qty': procurement.product_uom._compute_quantity(batch_size, bom.product_uom_id) if bom else procurement_qty,
                    })
                    new_productions_values_by_company[procurement.company_id.id]['procurements'].append(procurement)
                    procurement_qty -= batch_size
            else:
                procurement_product_uom_qty = procurement.product_uom._compute_quantity(procurement.product_qty, procurement.product_id.uom_id)
                self.env['change.production.qty'].sudo().with_context(skip_activity=True).create({
                    'mo_id': mo.id,
                    'product_qty': mo.product_id.uom_id._compute_quantity((mo.product_uom_qty + procurement_product_uom_qty), mo.product_uom_id),
                }).change_prod_qty()

        for company_id in new_productions_values_by_company:
            productions_vals_list = new_productions_values_by_company[company_id]['values']
            # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
            productions = self.env['mrp.production'].with_user(SUPERUSER_ID).sudo().with_company(company_id).create(productions_vals_list)
            for mo in productions:
                if self._should_auto_confirm_procurement_mo(mo):
                    mo.action_confirm()
            productions._post_run_manufacture(new_productions_values_by_company[company_id]['procurements'])
        return True

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        res = super()._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        res['production_group_id'] = values.get('production_group_id')
        return res

    def _get_moves_to_assign_domain(self, company_id):
        domain = super()._get_moves_to_assign_domain(company_id)
        return Domain(domain) & Domain('production_id', '=', False)

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['bom_line_id']
        return fields

    def _get_matching_bom(self, product_id, company_id, values):
        if values.get('bom_id', False):
            return values['bom_id']
        if values.get('orderpoint_id', False) and values['orderpoint_id'].bom_id:
            return values['orderpoint_id'].bom_id
        bom = self.env['mrp.bom']._bom_find(product_id, picking_type=self.picking_type_id, bom_type='normal', company_id=company_id.id)[product_id]
        if bom:
            return bom
        return self.env['mrp.bom']._bom_find(product_id, picking_type=False, bom_type='normal', company_id=company_id.id)[product_id]

    def _make_mo_get_domain(self, procurement, bom):
        domain = (
            ('bom_id', '=', bom.id),
            ('product_id', '=', procurement.product_id.id),
            ('state', 'in', ['draft', 'confirmed']),
            ('is_planned', '=', False),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('company_id', '=', procurement.company_id.id),
            ('user_id', '=', False),
            ('reference_ids', '=', procurement.values.get('reference_ids', self.env['stock.reference']).ids),
        )
        if procurement.values.get('orderpoint_id'):
            procurement_date = datetime.combine(
                fields.Date.to_date(procurement.values['date_planned']) - relativedelta(days=int(bom.produce_delay)),
                datetime.max.time()
            )
            domain += ('|',
                       '&', ('state', '=', 'draft'), ('date_deadline', '<=', procurement_date),
                       '&', ('state', '=', 'confirmed'), ('date_start', '<=', procurement_date))
        return domain

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        date_planned = self._get_date_planned(bom, values)
        date_deadline = values.get('date_deadline') or date_planned + relativedelta(days=bom.produce_delay)
        picking_type = bom.picking_type_id or self.picking_type_id
        mo_values = {
            'origin': origin,
            'product_id': product_id.id,
            'product_description_variants': values.get('product_description_variants'),
            'never_product_template_attribute_value_ids': values.get('never_product_template_attribute_value_ids'),
            'product_qty': product_uom._compute_quantity(product_qty, bom.product_uom_id) if bom else product_qty,
            'product_uom_id': bom.product_uom_id.id if bom else product_uom.id,
            'location_src_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id or location_dest_id.id,
            'location_final_id': location_dest_id.id,
            'bom_id': bom.id,
            'date_deadline': date_deadline,
            'date_start': date_planned,
            'reference_ids': [Command.set(values.get('reference_ids', self.env['stock.reference']).ids)],
            'propagate_cancel': self.propagate_cancel,
            'orderpoint_id': values.get('orderpoint_id', False) and values.get('orderpoint_id').id,
            'picking_type_id': picking_type.id or values['warehouse_id'].manu_type_id.id,
            'company_id': company_id.id,
            'move_dest_ids': values.get('move_dest_ids') and [(4, x.id) for x in values['move_dest_ids']] or False,
            'user_id': False,
        }
        if self.location_dest_from_rule:
            mo_values['location_dest_id'] = self.location_dest_id.id
        return mo_values

    def _get_date_planned(self, bom_id, values):
        format_date_planned = fields.Datetime.from_string(values['date_planned'])
        date_planned = format_date_planned - relativedelta(days=bom_id.produce_delay)
        if date_planned == format_date_planned:
            date_planned = date_planned - relativedelta(hours=1)
        return date_planned

    def _get_lead_days(self, product, **values):
        """Add the product and company manufacture delay to the cumulative delay
        and cumulative description.
        """
        delays, delay_description = super()._get_lead_days(product, **values)
        bypass_delay_description = self.env.context.get('bypass_delay_description')
        manufacture_rule = self.filtered(lambda r: r.action == 'manufacture')
        if not manufacture_rule:
            return delays, delay_description
        manufacture_rule.ensure_one()
        bom = values.get('bom') or self.env['mrp.bom']._bom_find(product, picking_type=manufacture_rule.picking_type_id, company_id=manufacture_rule.company_id.id)[product]
        if not bom:
            delays['total_delay'] += 365
            delays['no_bom_found_delay'] += 365
            if not bypass_delay_description:
                delay_description.append((_('No BoM Found'), _('+ %s day(s)', 365)))
        manufacture_delay = bom.produce_delay
        delays['total_delay'] += manufacture_delay
        delays['manufacture_delay'] += manufacture_delay
        if not bypass_delay_description:
            delay_description.append((_('Production End Date'), manufacture_delay))
            delay_description.append((_('Manufacturing Lead Time'), _('+ %d day(s)', manufacture_delay)))
        if bom.type == 'normal':
            # pre-production rules
            warehouse = self.location_dest_id.warehouse_id
            for wh in warehouse:
                if wh.manufacture_steps != 'mrp_one_step':
                    wh_manufacture_rules = product._get_rules_from_location(product.property_stock_production, route_ids=wh.pbm_route_id)
                    extra_delays, extra_delay_description = (wh_manufacture_rules - self).with_context(global_horizon_days=0)._get_lead_days(product, **values)
                    for key, value in extra_delays.items():
                        delays[key] += value
                    delay_description += extra_delay_description
        days_to_order = values.get('days_to_order', bom.days_to_prepare_mo)
        delays['total_delay'] += days_to_order
        if not bypass_delay_description:
            delay_description.append((_('Production Start Date'), days_to_order))
            delay_description.append((_('Days to Supply Components'), _('+ %d day(s)', days_to_order)))
        return delays, delay_description

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super()._push_prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals['production_group_id'] = move_to_copy.production_group_id.id
        new_move_vals['production_id'] = False
        return new_move_vals


class StockRoute(models.Model):
    _inherit = "stock.route"

    def _is_valid_resupply_route_for_product(self, product):
        if any(rule.action == 'manufacture' for rule in self.rule_ids):
            return any(bom.type == 'normal' for bom in product.bom_ids)
        return super()._is_valid_resupply_route_for_product(product)
