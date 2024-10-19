# -*- coding: utf-8 -*-

from collections import defaultdict, OrderedDict
from datetime import date, datetime, time, timedelta
import json

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round, format_date, float_is_zero
from odoo.exceptions import UserError


class ReportBomStructure(models.AbstractModel):
    _name = 'report.mrp.report_bom_structure'
    _description = 'BOM Overview Report'

    @api.model
    def get_html(self, bom_id=False, searchQty=1, searchVariant=False):
        res = self._get_report_data(bom_id=bom_id, searchQty=searchQty, searchVariant=searchVariant)
        res['has_attachments'] = self._has_attachments(res['lines'])
        return res

    @api.model
    def get_warehouses(self):
        return self.env['stock.warehouse'].search_read([('company_id', 'in', self.env.companies.ids)], fields=['id', 'name'])

    @api.model
    def _compute_current_production_capacity(self, bom_data):
        # Get the maximum amount producible product of the selected bom given each component's stock levels.
        components_qty_to_produce = defaultdict(lambda: 0)
        components_qty_available = {}
        for comp in bom_data.get('components', []):
            if not comp['product'].is_storable or float_is_zero(comp['base_bom_line_qty'], precision_rounding=comp['uom'].rounding):
                continue
            components_qty_to_produce[comp['product_id']] += comp['base_bom_line_qty']
            components_qty_available[comp['product_id']] = comp['free_to_manufacture_qty']
        producibles = [float_round(components_qty_available[p_id] / qty, precision_digits=0, rounding_method='DOWN') for p_id, qty in components_qty_to_produce.items()]
        return min(producibles) * bom_data['bom']['product_qty'] if producibles else 0

    @api.model
    def _compute_production_capacities(self, bom_qty, bom_data):
        date_today = self.env.context.get('from_date', fields.date.today())
        earliest_capacity = 0
        lead_time = bom_data['lead_time']
        availability_delay = bom_data['availability_delay']
        same_delay = lead_time == availability_delay
        res = {}
        if bom_data.get('producible_qty', 0):
            # Some quantities are producible today, at the earliest time possible
            earliest_capacity = bom_data['producible_qty']

        if bom_data['availability_state'] != 'unavailable':
            if same_delay:
                # Means that stock will be resupplied at date_today, so the whole manufacture can start at date_today.
                earliest_capacity = bom_qty
            elif (balance := bom_qty - bom_data.get('producible_qty', 0)) > 0:
                res['leftover_capacity'] = balance
                res['leftover_date'] = format_date(self.env, date_today + timedelta(days=availability_delay))

        if earliest_capacity:
            if bom_data['route_type'] == 'manufacture':
                # Simulate planning for 'earliest' capacity at date
                operations_planning = self._simulate_bom_planning(bom_data['bom'], bom_data['product'], datetime.combine(date_today, time.min), earliest_capacity)
                days = max(((p['date_finished'].date() - date_today).days for p in operations_planning.values()), default=0)
                lead_time = max(bom_data['bom'].produce_delay, days)
            res['earliest_date'] = format_date(self.env, date_today + timedelta(days=lead_time))
            res['earliest_capacity'] = earliest_capacity

        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        for bom_id in docids:
            bom = self.env['mrp.bom'].browse(bom_id)
            if not bom:
                continue
            variant = data.get('variant')
            candidates = variant and self.env['product.product'].browse(int(variant)) or bom.product_id or bom.product_tmpl_id.product_variant_ids
            quantity = float(data.get('quantity', bom.product_qty))
            if data.get('warehouse_id'):
                self = self.with_context(warehouse_id=int(data.get('warehouse_id')))  # noqa: PLW0642
            for product_variant_id in candidates.ids:
                docs.append(self._get_pdf_doc(bom_id, data, quantity, product_variant_id))
            if not candidates:
                docs.append(self._get_pdf_doc(bom_id, data, quantity))
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.bom',
            'docs': docs,
        }

    @api.model
    def _get_pdf_doc(self, bom_id, data, quantity, product_variant_id=None):
        if data and data.get('unfolded_ids'):
            doc = self._get_pdf_line(bom_id, product_id=product_variant_id, qty=quantity, unfolded_ids=set(json.loads(data.get('unfolded_ids'))))
        else:
            doc = self._get_pdf_line(bom_id, product_id=product_variant_id, qty=quantity, unfolded=True)
        doc['show_availabilities'] = False if data and data.get('availabilities') == 'false' else True
        doc['show_costs'] = False if data and data.get('costs') == 'false' else True
        doc['show_operations'] = False if data and data.get('operations') == 'false' else True
        doc['show_lead_times'] = False if data and data.get('lead_times') == 'false' else True
        return doc

    @api.model
    def _get_report_data(self, bom_id, searchQty=0, searchVariant=False):
        lines = {}
        bom = self.env['mrp.bom'].browse(bom_id)
        bom_quantity = searchQty or bom.product_qty or 1
        bom_product_variants = {}
        bom_uom_name = ''

        if searchVariant:
            product = self.env['product.product'].browse(int(searchVariant))
        else:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id or bom.product_tmpl_id.with_context(active_test=False).product_variant_ids[:1]

        if bom:
            bom_uom_name = bom.product_uom_id.name

            # Get variants used for search
            if not bom.product_id:
                for variant in bom.product_tmpl_id.product_variant_ids:
                    bom_product_variants[variant.id] = variant.display_name

        if self.env.context.get('warehouse_id'):
            warehouse = self.env['stock.warehouse'].browse(self.env.context.get('warehouse_id'))
        else:
            warehouse = self.env['stock.warehouse'].browse(self.get_warehouses()[0]['id'])

        lines = self._get_bom_data(bom, warehouse, product=product, line_qty=bom_quantity, level=0)
        production_capacities = self._compute_production_capacities(bom_quantity, lines)
        lines.update(production_capacities)
        return {
            'lines': lines,
            'variants': bom_product_variants,
            'bom_uom_name': bom_uom_name,
            'bom_qty': bom_quantity,
            'is_variant_applied': self.env.user.has_group('product.group_product_variant') and len(bom_product_variants) > 1,
            'is_uom_applied': self.env.user.has_group('uom.group_uom'),
            'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
        }

    @api.model
    def _get_components_closest_forecasted(self, lines, line_quantities, parent_bom, product_info, parent_product, ignore_stock=False):
        """
            Returns a dict mapping products to a dict of their corresponding BoM lines,
            which are mapped to their closest date in the forecast report where consumed quantity >= forecasted quantity.

            E.g. {'product_1_id': {'line_1_id': date_1, line_2_id: date_2}, 'product_2': {line_3_id: date_3}, ...}.

            Note that
                - if a product is unavailable + not forecasted for a specific bom line => its date will be `date.max`
                - if a product's type is not `product` or is already in stock for a specific bom line => its date will be `date.min`.
        """
        if ignore_stock:
            return {}
        # Use defaultdict(OrderedDict) in case there are lines with the same component.
        closest_forecasted = defaultdict(OrderedDict)
        remaining_products = []
        product_quantities_info = defaultdict(OrderedDict)
        for line in lines:
            product = line.product_id
            quantities_info = self._get_quantities_info(product, line.product_uom_id, product_info, parent_bom, parent_product)
            stock_loc = quantities_info['stock_loc']
            product_info[product.id]['consumptions'][stock_loc] += line_quantities.get(line.id, 0.0)
            product_quantities_info[product.id][line.id] = product_info[product.id]['consumptions'][stock_loc]
            if (not product.is_storable or
                    float_compare(product_info[product.id]['consumptions'][stock_loc], quantities_info['free_qty'], precision_rounding=product.uom_id.rounding) <= 0):
                # Use date.min as a sentinel value for _get_stock_availability
                closest_forecasted[product.id][line.id] = date.min
            elif stock_loc != 'in_stock':
                closest_forecasted[product.id][line.id] = date.max
            else:
                remaining_products.append(product.id)
                closest_forecasted[product.id][line.id] = None
        date_today = self.env.context.get('from_date', fields.date.today())
        domain = [('state', '=', 'forecast'), ('date', '>=', date_today), ('product_id', 'in', list(set(remaining_products)))]
        if self.env.context.get('warehouse_id'):
            domain.append(('warehouse_id', '=', self.env.context.get('warehouse_id')))
        if remaining_products:
            res = self.env['report.stock.quantity']._read_group(
                domain,
                groupby=['product_id', 'product_qty'],
                aggregates=['date:min'],
                order='product_id asc, date:min asc'
            )
            available_quantities = defaultdict(list)
            for group in res:
                product_id = group[0].id
                available_quantities[product_id].append([group[2], group[1]])
            for product_id in remaining_products:
                # Find the first empty line_id for the given product_id.
                line_id = next(filter(lambda k: not closest_forecasted[product_id][k], closest_forecasted[product_id].keys()), None)
                # Find the first available quantity for the given product and update closest_forecasted
                for min_date, product_qty in available_quantities[product_id]:
                    if product_qty >= product_quantities_info[product_id][line_id]:
                        closest_forecasted[product_id][line_id] = min_date
                        break
                if not closest_forecasted[product_id][line_id]:
                    closest_forecasted[product_id][line_id] = date.max
        return closest_forecasted

    @api.model
    def _get_bom_data(self, bom, warehouse, product=False, line_qty=False, bom_line=False, level=0, parent_bom=False, parent_product=False, index=0, product_info=False, ignore_stock=False, simulated_leaves_per_workcenter=False):
        """ Gets recursively the BoM and all its subassemblies and computes availibility estimations for each component and their disponibility in stock.
            Accepts specific keys in context that will affect the data computed :
            - 'minimized': Will cut all data not required to compute availability estimations.
            - 'from_date': Gives a single value for 'today' across the functions, as well as using this date in products quantity computes.
        """
        is_minimized = self.env.context.get('minimized', False)
        if not product:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
        if line_qty is False:
            line_qty = bom.product_qty
        if not product_info:
            product_info = {}
        if simulated_leaves_per_workcenter is False:
            simulated_leaves_per_workcenter = defaultdict(list)

        company = bom.company_id or self.env.company
        current_quantity = line_qty
        if bom_line:
            current_quantity = bom_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id) or 0

        prod_cost = 0
        has_attachments = False
        if not is_minimized:
            if product:
                prod_cost = product.uom_id._compute_price(product.with_company(company).standard_price, bom.product_uom_id) * current_quantity
                has_attachments = self.env['product.document'].search_count(['&', '&', ('attached_on_mrp', '=', 'bom'), ('active', '=', 't'), '|', '&', ('res_model', '=', 'product.product'),
                                                                 ('res_id', '=', product.id), '&', ('res_model', '=', 'product.template'),
                                                                 ('res_id', '=', product.product_tmpl_id.id)], limit=1) > 0
            else:
                # Use the product template instead of the variant
                prod_cost = bom.product_tmpl_id.uom_id._compute_price(bom.product_tmpl_id.with_company(company).standard_price, bom.product_uom_id) * current_quantity
                has_attachments = self.env['product.document'].search_count(['&', '&', ('attached_on_mrp', '=', 'bom'), ('active', '=', 't'),
                                                                    '&', ('res_model', '=', 'product.template'), ('res_id', '=', bom.product_tmpl_id.id)], limit=1) > 0

        key = product.id
        bom_key = bom.id
        qty_product_uom = bom.product_uom_id._compute_quantity(current_quantity, product.uom_id or bom.product_tmpl_id.uom_id)
        self._update_product_info(product, bom_key, product_info, warehouse, qty_product_uom, bom=bom, parent_bom=parent_bom, parent_product=parent_product)
        route_info = product_info[key].get(bom_key, {})
        quantities_info = {}
        if not ignore_stock:
            # Useless to compute quantities_info if it's not going to be used later on
            quantities_info = self._get_quantities_info(product, bom.product_uom_id, product_info, parent_bom, parent_product)

        bom_report_line = {
            'index': index,
            'bom': bom,
            'bom_id': bom and bom.id or False,
            'bom_code': bom and bom.code or False,
            'type': 'bom',
            'quantity': current_quantity,
            'quantity_available': quantities_info.get('free_qty') or 0,
            'quantity_on_hand': quantities_info.get('on_hand_qty') or 0,
            'free_to_manufacture_qty': quantities_info.get('free_to_manufacture_qty') or 0,
            'base_bom_line_qty': bom_line.product_qty if bom_line else False,  # bom_line isn't defined only for the top-level product
            'name': product.display_name or bom.product_tmpl_id.display_name,
            'uom': bom.product_uom_id if bom else product.uom_id,
            'uom_name': bom.product_uom_id.name if bom else product.uom_id.name,
            'route_type': route_info.get('route_type', ''),
            'route_name': route_info.get('route_name', ''),
            'route_detail': route_info.get('route_detail', ''),
            'route_alert': route_info.get('route_alert', False),
            'currency': company.currency_id,
            'currency_id': company.currency_id.id,
            'product': product,
            'product_id': product.id,
            'product_template_id': product.product_tmpl_id.id,
            'link_id': (product.id if product.product_variant_count > 1 else product.product_tmpl_id.id) or bom.product_tmpl_id.id,
            'link_model': 'product.product' if product.product_variant_count > 1 else 'product.template',
            'code': bom and bom.display_name or '',
            'prod_cost': prod_cost,
            'bom_cost': 0,
            'level': level or 0,
            'has_attachments': has_attachments,
            'phantom_bom': bom.type == 'phantom',
            'parent_id': parent_bom and parent_bom.id or False,
        }

        components = []
        no_bom_lines = self.env['mrp.bom.line']
        line_quantities = {}
        for line in bom.bom_line_ids:
            if product and line._skip_bom_line(product):
                continue
            line_quantity = (current_quantity / (bom.product_qty or 1.0)) * line.product_qty
            line_quantities[line.id] = line_quantity
            if not line.child_bom_id:
                no_bom_lines |= line
                # Update product_info for all the components before computing closest forecasted.
                qty_product_uom = line.product_uom_id._compute_quantity(line_quantity, line.product_id.uom_id)
                self._update_product_info(line.product_id, bom.id, product_info, warehouse, qty_product_uom, bom=False, parent_bom=bom, parent_product=product)
        components_closest_forecasted = self._get_components_closest_forecasted(no_bom_lines, line_quantities, bom, product_info, product, ignore_stock)
        for component_index, line in enumerate(bom.bom_line_ids):
            new_index = f"{index}{component_index}"
            if product and line._skip_bom_line(product):
                continue
            line_quantity = line_quantities.get(line.id, 0.0)
            if line.child_bom_id:
                component = self._get_bom_data(line.child_bom_id, warehouse, line.product_id, line_quantity, bom_line=line, level=level + 1, parent_bom=bom,
                                               parent_product=product, index=new_index, product_info=product_info, ignore_stock=ignore_stock,
                                               simulated_leaves_per_workcenter=simulated_leaves_per_workcenter)
            else:
                component = self.with_context(
                    components_closest_forecasted=components_closest_forecasted,
                )._get_component_data(bom, product, warehouse, line, line_quantity, level + 1, new_index, product_info, ignore_stock)
            for component_bom in components:
                if component['product_id'] == component_bom['product_id'] and component['uom'].id == component_bom['uom'].id:
                    self._merge_components(component_bom, component)
                    break
            else:
                components.append(component)
            bom_report_line['bom_cost'] += component['bom_cost']
        bom_report_line['components'] = components
        bom_report_line['producible_qty'] = self._compute_current_production_capacity(bom_report_line)

        availabilities = self._get_availabilities(product, current_quantity, product_info, bom_key, quantities_info, level, ignore_stock, components, report_line=bom_report_line)
        # in case of subcontracting, lead_time will be calculated with components availability delay
        bom_report_line['lead_time'] = route_info.get('lead_time', False)
        bom_report_line['manufacture_delay'] = route_info.get('manufacture_delay', False)
        bom_report_line.update(availabilities)

        if not is_minimized:

            operations = self._get_operation_line(product, bom, float_round(current_quantity, precision_rounding=1, rounding_method='UP'), level + 1, index, bom_report_line, simulated_leaves_per_workcenter)
            bom_report_line['operations'] = operations
            bom_report_line['operations_cost'] = sum(op['bom_cost'] for op in operations)
            bom_report_line['operations_time'] = sum(op['quantity'] for op in operations)
            bom_report_line['operations_delay'] = max((op['availability_delay'] for op in operations), default=0)
            if 'simulated' in bom_report_line:
                bom_report_line['availability_state'] = 'estimated'
                max_component_delay = bom_report_line['max_component_delay']
                bom_report_line['availability_delay'] = max_component_delay + max(bom.produce_delay, bom_report_line['operations_delay'])
                bom_report_line['availability_display'] = self._format_date_display(bom_report_line['availability_state'], bom_report_line['availability_delay'])
            bom_report_line['bom_cost'] += bom_report_line['operations_cost']

            byproducts, byproduct_cost_portion = self._get_byproducts_lines(product, bom, current_quantity, level + 1, bom_report_line['bom_cost'], index)
            bom_report_line['byproducts'] = byproducts
            bom_report_line['cost_share'] = float_round(1 - byproduct_cost_portion, precision_rounding=0.0001)
            bom_report_line['byproducts_cost'] = sum(byproduct['bom_cost'] for byproduct in byproducts)
            bom_report_line['byproducts_total'] = sum(byproduct['quantity'] for byproduct in byproducts)
            bom_report_line['bom_cost'] *= bom_report_line['cost_share']

        if level == 0:
            # Gives a unique key for the first line that indicates if product is ready for production right now.
            bom_report_line['components_available'] = all([c['stock_avail_state'] == 'available' for c in components])
        return bom_report_line

    @api.model
    def _get_component_data(self, parent_bom, parent_product, warehouse, bom_line, line_quantity, level, index, product_info, ignore_stock=False):
        company = parent_bom.company_id or self.env.company
        price = bom_line.product_id.uom_id._compute_price(bom_line.product_id.with_company(company).standard_price, bom_line.product_uom_id) * line_quantity
        rounded_price = company.currency_id.round(price)

        key = bom_line.product_id.id
        bom_key = parent_bom.id
        route_info = product_info[key].get(bom_key, {})

        quantities_info = {}
        if not ignore_stock:
            # Useless to compute quantities_info if it's not going to be used later on
            quantities_info = self._get_quantities_info(bom_line.product_id, bom_line.product_uom_id, product_info, parent_bom, parent_product)
        availabilities = self._get_availabilities(bom_line.product_id, line_quantity, product_info, bom_key, quantities_info, level, ignore_stock, bom_line=bom_line)

        has_attachments = False
        if not self.env.context.get('minimized', False):
            has_attachments = self.env['product.document'].search_count(['&', ('attached_on_mrp', '=', 'bom'), '|', '&', ('res_model', '=', 'product.product'), ('res_id', '=', bom_line.product_id.id),
                                                              '&', ('res_model', '=', 'product.template'), ('res_id', '=', bom_line.product_id.product_tmpl_id.id)]) > 0

        return {
            'type': 'component',
            'index': index,
            'bom_id': False,
            'product': bom_line.product_id,
            'product_id': bom_line.product_id.id,
            'product_template_id': bom_line.product_tmpl_id.id,
            'link_id': bom_line.product_id.id if bom_line.product_id.product_variant_count > 1 else bom_line.product_id.product_tmpl_id.id,
            'link_model': 'product.product' if bom_line.product_id.product_variant_count > 1 else 'product.template',
            'name': bom_line.product_id.display_name,
            'code': '',
            'currency': company.currency_id,
            'currency_id': company.currency_id.id,
            'quantity': line_quantity,
            'quantity_available': quantities_info.get('free_qty', 0),
            'quantity_on_hand': quantities_info.get('on_hand_qty', 0),
            'free_to_manufacture_qty': quantities_info.get('free_to_manufacture_qty', 0),
            'base_bom_line_qty': bom_line.product_qty,
            'uom': bom_line.product_uom_id,
            'uom_name': bom_line.product_uom_id.name,
            'prod_cost': rounded_price,
            'bom_cost': rounded_price,
            'route_type': route_info.get('route_type', ''),
            'route_name': route_info.get('route_name', ''),
            'route_detail': route_info.get('route_detail', ''),
            'route_alert': route_info.get('route_alert', False),
            'lead_time': route_info.get('lead_time', False),
            'manufacture_delay': route_info.get('manufacture_delay', False),
            'stock_avail_state': availabilities['stock_avail_state'],
            'resupply_avail_delay': availabilities['resupply_avail_delay'],
            'availability_display': availabilities['availability_display'],
            'availability_state': availabilities['availability_state'],
            'availability_delay': availabilities['availability_delay'],
            'parent_id': parent_bom.id,
            'level': level or 0,
            'has_attachments': has_attachments,
        }

    @api.model
    def _get_quantities_info(self, product, bom_uom, product_info, parent_bom=False, parent_product=False):
        quantities_info = {
            'free_qty': max(product.uom_id._compute_quantity(product.free_qty, bom_uom), 0) if product.is_storable else 0,
            'on_hand_qty': product.uom_id._compute_quantity(product.qty_available, bom_uom) if product.is_storable else 0,
            'stock_loc': 'in_stock',
        }
        quantities_info['free_to_manufacture_qty'] = quantities_info['free_qty']
        return quantities_info

    @api.model
    def _update_product_info(self, product, bom_key, product_info, warehouse, quantity, bom, parent_bom, parent_product):
        key = product.id
        if key not in product_info:
            product_info[key] = {'consumptions': {'in_stock': 0}}
        if not product_info[key].get(bom_key):
            product_info[key][bom_key] = self._get_resupply_route_info(warehouse, product, quantity, product_info, bom, parent_bom, parent_product)
        elif product_info[key][bom_key].get('route_alert'):
            # Need more quantity than a single line, might change with additional quantity
            product_info[key][bom_key] = self._get_resupply_route_info(
                warehouse, product, quantity + product_info[key][bom_key].get('qty_checked'), product_info, bom, parent_bom, parent_product)

    @api.model
    def _get_byproducts_lines(self, product, bom, bom_quantity, level, total, index):
        byproducts = []
        byproduct_cost_portion = 0
        company = bom.company_id or self.env.company
        byproduct_index = 0
        for byproduct in bom.byproduct_ids:
            if byproduct._skip_byproduct_line(product):
                continue
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * byproduct.product_qty
            cost_share = byproduct.cost_share / 100
            byproduct_cost_portion += cost_share
            price = byproduct.product_id.uom_id._compute_price(byproduct.product_id.with_company(company).standard_price, byproduct.product_uom_id) * line_quantity
            byproducts.append({
                'id': byproduct.id,
                'index': f"{index}{byproduct_index}",
                'type': 'byproduct',
                'link_id': byproduct.product_id.id if byproduct.product_id.product_variant_count > 1 else byproduct.product_id.product_tmpl_id.id,
                'link_model': 'product.product' if byproduct.product_id.product_variant_count > 1 else 'product.template',
                'currency_id': company.currency_id.id,
                'name': byproduct.product_id.display_name,
                'quantity': line_quantity,
                'uom_name': byproduct.product_uom_id.name,
                'prod_cost': company.currency_id.round(price),
                'parent_id': bom.id,
                'level': level or 0,
                'bom_cost': company.currency_id.round(total * cost_share),
                'cost_share': cost_share,
            })
            byproduct_index += 1
        return byproducts, byproduct_cost_portion

    @api.model
    def _get_operation_cost(self, operation, workcenter, duration):
        return (duration / 60.0) * workcenter.costs_hour

    @api.model
    def _get_operation_line(self, product, bom, qty, level, index, bom_report_line, simulated_leaves_per_workcenter):
        operations = []
        company = bom.company_id or self.env.company
        operations_planning = {}
        if bom_report_line['availability_state'] in ['unavailable', 'estimated'] and bom.operation_ids:
            qty_to_produce = bom.product_uom_id._compute_quantity(max(0, qty - (product.virtual_available if level > 1 else 0)), bom.product_tmpl_id.uom_id)
            if not float_is_zero(qty_to_produce, precision_rounding=(product or bom.product_tmpl_id).uom_id.rounding):
                max_component_delay = 0
                for component in bom_report_line['components']:
                    line_delay = component.get('availability_delay', 0)
                    max_component_delay = max(max_component_delay, line_delay)
                date_today = self.env.context.get('from_date', fields.date.today()) + timedelta(days=max_component_delay)
                operations_planning = self._simulate_bom_planning(bom, product, datetime.combine(date_today, time.min), qty_to_produce, simulated_leaves_per_workcenter=simulated_leaves_per_workcenter)
                bom_report_line['simulated'] = True
                bom_report_line['max_component_delay'] = max_component_delay
        operation_index = 0
        for operation in bom.operation_ids:
            if not product or operation._skip_operation_line(product):
                continue
            duration_expected = operation._get_duration_expected(product, qty, product.uom_id)
            bom_cost = self.env.company.currency_id.round(self._get_operation_cost(operation, operation.workcenter_id, duration_expected))
            if planning := operations_planning.get(operation, None):
                availability_state = 'estimated'
                availability_delay = (planning['date_finished'].date() - date_today).days
                availability_display = _('Estimated %s', format_date(self.env, planning['date_finished'])) + (" [" + planning['workcenter'].name + "]" if planning['workcenter'] != operation.workcenter_id else "")
            else:
                availability_state = 'available'
                availability_delay = 0
                availability_display = ''
            operations.append({
                'type': 'operation',
                'index': f"{index}{operation_index}",
                'level': level or 0,
                'operation': operation,
                'link_id': operation.id,
                'link_model': 'mrp.routing.workcenter',
                'name': operation.name + ' - ' + operation.workcenter_id.name,
                'uom_name': _("Minutes"),
                'quantity': duration_expected,
                'bom_cost': bom_cost,
                'currency_id': company.currency_id.id,
                'model': 'mrp.routing.workcenter',
                'availability_state': availability_state,
                'availability_delay': availability_delay,
                'availability_display': availability_display,
            })
            operation_index += 1
        return operations

    @api.model
    def _get_pdf_line(self, bom_id, product_id=False, qty=1, unfolded_ids=None, unfolded=False):
        if unfolded_ids is None:
            unfolded_ids = set()

        bom = self.env['mrp.bom'].browse(bom_id)
        if product_id:
            product = self.env['product.product'].browse(int(product_id))
        else:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id or bom.product_tmpl_id.with_context(active_test=False).product_variant_ids[:1]

        if self.env.context.get('warehouse_id'):
            warehouse = self.env['stock.warehouse'].browse(self.env.context.get('warehouse_id'))
        else:
            warehouse = self.env['stock.warehouse'].browse(self.get_warehouses()[0]['id'])

        level = 1
        data = self._get_bom_data(bom, warehouse, product=product, line_qty=qty, level=0)
        pdf_lines = self._get_bom_array_lines(data, level, unfolded_ids, unfolded, True)

        data['lines'] = pdf_lines
        return data

    @api.model
    def _get_bom_array_lines(self, data, level, unfolded_ids, unfolded, parent_unfolded=True):
        bom_lines = data['components']
        lines = []
        for bom_line in bom_lines:
            line_unfolded = ('bom_' + str(bom_line['index'])) in unfolded_ids
            line_visible = level == 1 or unfolded or parent_unfolded
            lines.append({
                'bom_id': bom_line['bom_id'],
                'name': bom_line['name'],
                'type': bom_line['type'],
                'quantity': bom_line['quantity'],
                'quantity_available': bom_line['quantity_available'],
                'quantity_on_hand': bom_line['quantity_on_hand'],
                'producible_qty': bom_line.get('producible_qty', False),
                'uom': bom_line['uom_name'],
                'prod_cost': bom_line['prod_cost'],
                'bom_cost': bom_line['bom_cost'],
                'route_name': bom_line['route_name'],
                'route_detail': bom_line['route_detail'],
                'route_alert': bom_line.get('route_alert', False),
                'lead_time': bom_line['lead_time'],
                'manufacture_delay': bom_line['manufacture_delay'],
                'level': bom_line['level'],
                'code': bom_line['code'],
                'availability_state': bom_line['availability_state'],
                'availability_display': bom_line['availability_display'],
                'visible': line_visible,
            })
            if bom_line.get('components'):
                lines += self._get_bom_array_lines(bom_line, level + 1, unfolded_ids, unfolded, line_visible and line_unfolded)

        if data['operations']:
            lines.append({
                'name': _('Operations'),
                'type': 'operation',
                'quantity': data['operations_time'],
                'uom': _('minutes'),
                'bom_cost': data['operations_cost'],
                'level': level,
                'visible': parent_unfolded,
            })
            operations_unfolded = unfolded or (parent_unfolded and ('operations_' + str(data['index'])) in unfolded_ids)
            for operation in data['operations']:
                lines.append({
                    'name': operation['name'],
                    'type': 'operation',
                    'quantity': operation['quantity'],
                    'uom': _('minutes'),
                    'bom_cost': operation['bom_cost'],
                    'level': level + 1,
                    'availability_state': operation['availability_state'],
                    'availability_delay': operation['availability_delay'],
                    'availability_display': operation['availability_display'],
                    'visible': operations_unfolded,
                })
        if data['byproducts']:
            lines.append({
                'name': _('Byproducts'),
                'type': 'byproduct',
                'uom': False,
                'quantity': data['byproducts_total'],
                'bom_cost': data['byproducts_cost'],
                'level': level,
                'visible': parent_unfolded,
            })
            byproducts_unfolded = unfolded or (parent_unfolded and ('byproducts_' + str(data['index'])) in unfolded_ids)
            for byproduct in data['byproducts']:
                lines.append({
                    'name': byproduct['name'],
                    'type': 'byproduct',
                    'quantity': byproduct['quantity'],
                    'uom': byproduct['uom_name'],
                    'prod_cost': byproduct['prod_cost'],
                    'bom_cost': byproduct['bom_cost'],
                    'level': level + 1,
                    'visible': byproducts_unfolded,
                })
        return lines

    @api.model
    def _get_resupply_route_info(self, warehouse, product, quantity, product_info, bom=False, parent_bom=False, parent_product=False):
        found_rules = []
        if self._need_special_rules(product_info, parent_bom, parent_product):
            found_rules = self._find_special_rules(product, product_info, bom, parent_bom, parent_product)
        if not found_rules:
            found_rules = product._get_rules_from_location(warehouse.lot_stock_id)
        if not found_rules:
            return {}
        rules_delay = sum(rule.delay for rule in found_rules)
        return self.with_context(parent_bom=parent_bom)._format_route_info(found_rules, rules_delay, warehouse, product, bom, quantity)

    @api.model
    def _is_resupply_rules(self, rules, bom):
        return bom and any(rule.action == 'manufacture' for rule in rules)

    @api.model
    def _need_special_rules(self, product_info, parent_bom=False, parent_product=False):
        return False

    @api.model
    def _find_special_rules(self, product, product_info, current_bom=False, parent_bom=False, parent_product=False):
        return False

    @api.model
    def _format_route_info(self, rules, rules_delay, warehouse, product, bom, quantity):
        manufacture_rules = [rule for rule in rules if rule.action == 'manufacture' and bom]
        if manufacture_rules:
            # Need to get rules from Production location to get delays before production
            wh_manufacture_rules = product._get_rules_from_location(product.property_stock_production, route_ids=warehouse.route_ids)
            wh_manufacture_rules -= rules
            rules_delay += sum(rule.delay for rule in wh_manufacture_rules)
            manufacturing_lead = bom.company_id.manufacturing_lead if bom and bom.company_id else 0
            return {
                'route_type': 'manufacture',
                'route_name': manufacture_rules[0].route_id.display_name,
                'route_detail': bom.display_name,
                'lead_time': bom.produce_delay + rules_delay + manufacturing_lead + bom.days_to_prepare_mo,
                'manufacture_delay': bom.produce_delay + rules_delay + manufacturing_lead,
                'bom': bom,
            }
        return {}

    @api.model
    def _get_availabilities(self, product, quantity, product_info, bom_key, quantities_info, level, ignore_stock=False, components=False, bom_line=None, report_line=False):
        # Get availabilities according to stock (today & forecasted).
        stock_state, stock_delay = ('unavailable', False)
        if not ignore_stock:
            stock_state, stock_delay = self._get_stock_availability(product, quantity, product_info, quantities_info, bom_line=bom_line)

        # Get availabilities from applied resupply rules
        components = components or []
        route_info = product_info[product.id].get(bom_key)
        resupply_state, resupply_delay = ('unavailable', False)
        if product and not product.is_storable:
            resupply_state, resupply_delay = ('available', 0)
        elif route_info:
            resupply_state, resupply_delay = self._get_resupply_availability(route_info, components)

        if resupply_state == "unavailable" and route_info == {} and components and report_line and report_line['phantom_bom']:
            val = self._get_last_availability(report_line)
            return val

        base = {
            'resupply_avail_delay': resupply_delay,
            'stock_avail_state': stock_state,
        }
        if level != 0 and stock_state != 'unavailable':
            return {**base, **{
                'availability_display': self._format_date_display(stock_state, stock_delay),
                'availability_state': stock_state,
                'availability_delay': stock_delay,
            }}
        return {**base, **{
            'availability_display': self._format_date_display(resupply_state, resupply_delay),
            'availability_state': resupply_state,
            'availability_delay': resupply_delay,
        }}

    @api.model
    def _get_stock_availability(self, product, quantity, product_info, quantities_info, bom_line=None):
        closest_forecasted = None
        if bom_line:
            closest_forecasted = self.env.context.get('components_closest_forecasted', {}).get(product.id, {}).get(bom_line.id)
        if closest_forecasted == date.min:
            return ('available', 0)
        if closest_forecasted == date.max:
            return ('unavailable', False)
        date_today = self.env.context.get('from_date', fields.date.today())
        if product and not product.is_storable:
            return ('available', 0)

        stock_loc = quantities_info['stock_loc']
        product_info[product.id]['consumptions'][stock_loc] += quantity
        # Check if product is already in stock with enough quantity
        if product and float_compare(product_info[product.id]['consumptions'][stock_loc], quantities_info['free_qty'], precision_rounding=product.uom_id.rounding) <= 0:
            return ('available', 0)

        # No need to check forecast if the product isn't located in our stock
        if stock_loc == 'in_stock':
            domain = [('state', '=', 'forecast'), ('date', '>=', date_today), ('product_id', '=', product.id), ('product_qty', '>=', product_info[product.id]['consumptions'][stock_loc])]
            if self.env.context.get('warehouse_id'):
                domain.append(('warehouse_id', '=', self.env.context.get('warehouse_id')))

            # Seek the closest date in the forecast report where consummed quantity >= forecasted quantity
            if not closest_forecasted:
                [closest_forecasted] = self.env['report.stock.quantity']._read_group(domain, aggregates=['date:min'])[0]
            if closest_forecasted:
                days_to_forecast = (closest_forecasted - date_today).days
                return ('expected', days_to_forecast)
        return ('unavailable', False)

    @api.model
    def _get_resupply_availability(self, route_info, components):
        if route_info.get('route_type') == 'manufacture':
            max_component_delay = self._get_max_component_delay(components)
            if max_component_delay is False:
                return ('unavailable', False)
            produce_delay = route_info.get('manufacture_delay', 0) + max_component_delay
            return ('estimated', produce_delay)
        return ('unavailable', False)

    @api.model
    def _get_max_component_delay(self, components):
        max_component_delay = 0
        for component in components:
            line_delay = component.get('availability_delay', False)
            if line_delay is False:
                # This component isn't available right now and cannot be resupplied, so the manufactured product can't be resupplied either.
                return False
            max_component_delay = max(max_component_delay, line_delay)
        return max_component_delay

    @api.model
    def _format_date_display(self, state, delay):
        date_today = self.env.context.get('from_date', fields.date.today())
        if state == 'available':
            return _('Available')
        if state == 'unavailable':
            return _('Not Available')
        if state == 'expected':
            return _('Expected %s', format_date(self.env, date_today + timedelta(days=delay)))
        if state == 'estimated':
            return _('Estimated %s', format_date(self.env, date_today + timedelta(days=delay)))
        return ''

    @api.model
    def _has_attachments(self, data):
        return data['has_attachments'] or any(self._has_attachments(component) for component in data.get('components', []))

    def _merge_components(self, component_1, component_2):
        qty = component_2['quantity']
        component_1["quantity"] = component_1["quantity"] + qty
        component_1["base_bom_line_qty"] = component_1["quantity"] + qty
        component_1["prod_cost"] = component_1["prod_cost"] + component_2["prod_cost"]
        component_1["bom_cost"] = component_1["bom_cost"] + component_2["bom_cost"]
        if component_2.get('availability_delay') is False or component_2.get('availability_delay') >= component_1.get('availability_delay'):
            component_1.update(self._format_availability(component_2))
        if not component_1.get("components"):
            return
        for index in range(len(component_1.get("components"))):
            self._merge_components(component_1["components"][index], component_2["components"][index])

    def _get_last_availability(self, report_line):
        delay = 0
        component_max_delay = False
        for component in report_line["components"]:
            if component["availability_delay"] is False:
                component_max_delay = component
                break
            elif component["availability_delay"] >= delay:
                component_max_delay = component
                delay = component["availability_delay"]
        return self._format_availability(component_max_delay)

    def _format_availability(self, component):
        return {
            'resupply_avail_delay': component['resupply_avail_delay'],
            'stock_avail_state': component['stock_avail_state'],
            'availability_display': component['availability_display'],
            'availability_state': component['availability_state'],
            'availability_delay': component['availability_delay'],
        }

    def _simulate_bom_planning(self, bom, product, start_date, quantity, simulated_leaves_per_workcenter=False):
        """ Simulate planning of all the operations depending on the workcenters work schedule.
        (see '_plan_workorders' & '_link_workorders_and_moves')
        """
        bom.ensure_one()
        if not bom.operation_ids:
            return {}
        if not product:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
        planning_per_operation = {}
        if simulated_leaves_per_workcenter is False:
            simulated_leaves_per_workcenter = defaultdict(list)
        if bom.allow_operation_dependencies:
            final_operations = bom.operation_ids.filtered(lambda o: not o.needed_by_operation_ids)
            for operation in final_operations:
                if operation._skip_operation_line(product):
                    continue
                self._simulate_operation_planning(operation, product, start_date, quantity, planning_per_operation, simulated_leaves_per_workcenter)
        else:
            for operation in bom.operation_ids:
                if operation._skip_operation_line(product):
                    continue
                self._simulate_operation_planning(operation, product, start_date, quantity, planning_per_operation, simulated_leaves_per_workcenter)
                start_date = planning_per_operation[operation]['date_finished']
        return planning_per_operation

    def _simulate_operation_planning(self, operation, product, start_date, quantity, planning_per_operation=False, simulated_leaves_per_workcenter=False):
        """ Simulate planning of an operation depending on its workcenter/alternatives work schedule.
        (see '_plan_workorder')
        """
        operation.ensure_one()
        if planning_per_operation is False:
            planning_per_operation = {}
        if simulated_leaves_per_workcenter is False:
            simulated_leaves_per_workcenter = defaultdict(list)
        # Plan operation after its predecessors
        date_start = max(start_date, datetime.now())
        for op in operation.blocked_by_operation_ids:
            if op._skip_operation_line(product):
                continue
            if op not in planning_per_operation:
                self._simulate_operation_planning(op, product, start_date, quantity, planning_per_operation, simulated_leaves_per_workcenter)
            date_start = max(date_start, planning_per_operation[op]['date_finished'])
        # Consider workcenter and alternatives
        workcenters = operation.workcenter_id | operation.workcenter_id.alternative_workcenter_ids
        best_date_finished = datetime.max
        for workcenter in workcenters:
            if not workcenter.resource_calendar_id:
                raise UserError(_('There is no defined calendar on workcenter %s.', workcenter.name))
            # Compute theoretical duration
            duration_expected = operation._get_duration_expected(product, quantity, product.uom_id, workcenter)
            # Try to plan on workcenter
            from_date, to_date = workcenter._get_first_available_slot(date_start, duration_expected, extra_leaves_slots=simulated_leaves_per_workcenter[workcenter])
            # If the workcenter is unavailable, try planning on the next one
            if not from_date:
                continue
            # Check if this workcenter is better than the previous ones
            if to_date and to_date < best_date_finished:
                best_date_start = from_date
                best_date_finished = to_date
                best_workcenter = workcenter
                best_duration_expected = duration_expected
        # If none of the workcenter are available, raise
        if best_date_finished == datetime.max:
            raise UserError(_('Impossible to plan. Please check the workcenter availabilities.'))
        planning_per_operation[operation] = {
            'date_start': best_date_start,
            'date_finished': best_date_finished,
            'workcenter': best_workcenter,
            'duration_expected': best_duration_expected,
        }
        simulated_leaves_per_workcenter[best_workcenter].append((best_date_start, best_date_finished))
        return planning_per_operation
