# -*- coding: utf-8 -*-

import copy
import json
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_compare, format_date, float_is_zero, get_lang
from datetime import datetime, timedelta
from math import log10

class ReportMoOverview(models.AbstractModel):
    _name = 'report.mrp.report_mo_overview'
    _description = 'MO Overview Report'

    @api.model
    def get_report_values(self, production_id):
        """ Endpoint for HTML display. """
        return {
            'data': self._get_report_data(production_id),
            'context': self._get_display_context(),
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        """ Endpoint for PDF display. """
        if not data:
            data = {}
        docs = []
        for prod_id in docids:
            doc = self._get_report_data(prod_id)
            doc['show_replenishments'] = data.get('replenishments') == '1'
            doc['show_availabilities'] = data.get('availabilities') == '1'
            doc['show_receipts'] = data.get('receipts') == '1'
            doc['show_mo_costs'] = data.get('moCosts') == '1'
            doc['show_product_costs'] = data.get('productCosts') == '1'
            doc['show_uom'] = self.env.user.user_has_groups('uom.group_uom')
            doc['data_mo_unit_cost'] = doc['summary'].get('mo_cost', 0) / doc['summary'].get('quantity', 1)
            doc['data_product_unit_cost'] = doc['summary'].get('product_cost', 0) / doc['summary'].get('quantity', 1)
            doc['unfolded_ids'] = set(json.loads(data.get('unfoldedIds', '[]')))

            docs.append(doc)
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
        }

    def _get_display_context(self):
        return {
            'show_uom': self.env.user.user_has_groups('uom.group_uom'),
        }

    def _get_report_data(self, production_id):
        production = self.env['mrp.production'].browse(production_id)
        components = self._get_components_data(production, level=1, current_index='')
        operations = self._get_operations_data(production, level=1, current_index='')
        summary = self._get_mo_summary(production, components, operations)
        return {
            'id': production.id,
            'summary': summary,
            'components': components,
            'operations': operations,
            'extras': self._get_report_extra_lines(summary),
        }

    def _get_report_extra_lines(self, summary):
        currency = summary.get('currency', self.env.company)
        unit_mo_cost = currency.round(summary.get('mo_cost', 0) / summary.get('quantity', 1))
        unit_product_cost = currency.round(summary.get('product_cost', 0) / summary.get('quantity', 1))
        return {
            'unit_mo_cost': unit_mo_cost,
            'unit_mo_cost_decorator': self._get_comparison_decorator(unit_product_cost, unit_mo_cost, currency.rounding),
            'unit_product_cost': unit_product_cost,
        }

    def _get_mo_summary(self, production, components, operations):
        product = production.product_id
        company = production.company_id or self.env.company
        mo_cost = sum(component.get('summary', {}).get('mo_cost', 0.0) for component in components)
        return {
            'level': 0,
            'model': production._name,
            'id': production.id,
            'name': production.product_id.display_name,
            'product_model': production.product_id._name,
            'product_id': production.product_id.id,
            'state': production.state,
            'formatted_state': self._format_state(production),
            'quantity': production.product_qty,
            'uom_name': production.product_uom_id.display_name,
            'uom_precision': self._get_uom_precision(production.product_uom_id.rounding),
            'quantity_free': product.uom_id._compute_quantity(product.free_qty, production.product_uom_id) if product.type == 'product' else False,
            'quantity_on_hand': product.uom_id._compute_quantity(product.qty_available, production.product_uom_id) if product.type == 'product' else False,
            'quantity_reserved': 0.0,
            'receipt': self._check_planned_start(production.date_deadline, self._get_replenishment_receipt(production, components)),
            'mo_cost': company.currency_id.round(mo_cost + operations.get('summary', {}).get('mo_cost', 0.0)),
            'product_cost': company.currency_id.round(product.standard_price * production.product_uom_qty),
            'currency_id': company.currency_id.id,
            'currency': company.currency_id,
        }

    def _format_state(self, record):
        return dict(record._fields['state']._description_selection(self.env)).get(record.state)

    def _get_uom_precision(self, uom_rounding):
        return max(0, int(-(log10(uom_rounding))))

    def _get_comparison_decorator(self, expected, current, rounding):
        compare = float_compare(current, expected, precision_rounding=rounding)
        if float_is_zero(current, precision_rounding=rounding) or compare == 0:
            return False
        elif compare > 0:
            return 'danger'
        else:
            return 'success'

    def _get_operations_data(self, production, level=0, current_index=False):
        currency = (production.company_id or self.env.company).currency_id
        operation_uom = _("Minutes")
        operations = []
        total_expected_time = 0.0
        total_current_time = 0.0
        total_expected_cost = 0.0
        total_current_cost = 0.0
        for index, workorder in enumerate(production.workorder_ids):
            wo_duration = workorder.duration + workorder.get_working_duration()  # Add duration of ongoing work sessions.
            expected_cost = workorder._compute_expected_operation_cost()
            current_cost = workorder._compute_current_operation_cost()
            operations.append({
                'level': level,
                'index': f"{current_index}W{index}",
                'model': workorder._name,
                'id': workorder.id,
                'name': workorder.name,
                'state': workorder.state,
                'formatted_state': self._format_state(workorder),
                'quantity': workorder.duration_expected if float_is_zero(wo_duration, precision_digits=2) else wo_duration,
                'quantity_decorator': self._get_comparison_decorator(workorder.duration_expected, wo_duration, 0.01),
                'uom_name': operation_uom,
                'production_id': production.id,
                'mo_cost': expected_cost if float_is_zero(current_cost, precision_rounding=currency.rounding) else current_cost,
                'mo_cost_decorator': self._get_comparison_decorator(expected_cost, current_cost, currency.rounding),
                'currency_id': currency.id,
                'currency': currency,
            })
            total_expected_time += workorder.duration_expected
            total_current_time += workorder.duration_expected if float_is_zero(wo_duration, precision_digits=2) else wo_duration
            total_expected_cost += expected_cost
            total_current_cost += expected_cost if float_is_zero(current_cost, precision_rounding=currency.rounding) else current_cost

        return {
            'summary': {
                'index': f"{current_index}W",
                'quantity': total_current_time,
                'quantity_decorator': self._get_comparison_decorator(total_expected_time, total_current_time, 0.01),
                'mo_cost': total_current_cost,
                'mo_cost_decorator': self._get_comparison_decorator(total_expected_cost, total_current_cost, currency.rounding),
                'uom_name': operation_uom,
                'currency_id': currency.id,
                'currency': currency,
            },
            'details': operations,
        }

    def _get_components_data(self, production, replenish_data=False, level=0, current_index=False):
        if not replenish_data:
            replenish_data = {
                'products': {},
                'warehouses': {},
                'qty_already_reserved': defaultdict(float),
                'qty_reserved': {},
            }
        components = []
        company = production.company_id or self.env.company
        replenish_data = self._get_replenishments_from_forecast(production, replenish_data)
        for count, move_raw in enumerate(production.move_raw_ids):
            component_index = f"{current_index}{count}"
            replenishments = self._get_replenishment_lines(production, move_raw, replenish_data, level, component_index)
            # If not enough replenishment -> To Order / Might get "non-available" in summary since all component won't be there in time
            components.append({
                'summary': self._format_component_move(production, move_raw, replenishments, company, replenish_data, level, component_index),
                'replenishments': replenishments
            })

        return components

    def _format_component_move(self, production, move_raw, replenishments, company, replenish_data, level, index):
        product = move_raw.product_id
        replenish_mo_cost = sum(rep.get('summary', {}).get('mo_cost', 0.0) for rep in replenishments)
        replenish_quantity = sum(rep.get('summary', {}).get('quantity', 0.0) for rep in replenishments)
        missing_quantity = move_raw.product_uom_qty - replenish_quantity
        mo_cost = replenish_mo_cost + (product.standard_price * move_raw.product_uom._compute_quantity(missing_quantity, product.uom_id))
        component = {
            'level': level,
            'index': index,
            'id': product.id,
            'model': product._name,
            'name': product.display_name,
            'product_model': product._name,
            'product_id': product.id,
            'quantity': move_raw.product_uom_qty,
            'uom_name': move_raw.product_uom.display_name,
            'uom_precision': self._get_uom_precision(move_raw.product_uom.rounding),
            'quantity_free': product.uom_id._compute_quantity(product.free_qty, move_raw.product_uom) if product.type == 'product' else False,
            'quantity_on_hand': product.uom_id._compute_quantity(product.qty_available, move_raw.product_uom) if product.type == 'product' else False,
            'quantity_reserved': self._get_reserved_qty(move_raw, production.warehouse_id, replenish_data),
            'receipt': self._check_planned_start(production.date_start, self._get_component_receipt(product, move_raw, production.warehouse_id, replenishments, replenish_data)),
            'mo_cost': company.currency_id.round(mo_cost),
            'product_cost': company.currency_id.round(product.standard_price * move_raw.product_qty),
            'currency_id': company.currency_id.id,
            'currency': company.currency_id,
        }
        if product.type != 'product':
            return component
        if any(rep.get('summary', {}).get('model') == 'to_order' for rep in replenishments):
            # Means that there's an extra "To Order" line summing up what's left to order.
            component['formatted_state'] = _("To Order")
            component['state'] = 'to_order'

        return component

    def _check_planned_start(self, mo_planned_start, receipt):
        if mo_planned_start and receipt.get('date', False) and receipt['date'] > mo_planned_start:
            receipt['decorator'] = 'danger'
        return receipt

    def _get_component_receipt(self, product, move, warehouse, replenishments, replenish_data):
        def get(replenishment, key, check_in_receipt=False):
            fetch = replenishment.get('summary', {})
            if check_in_receipt:
                fetch = fetch.get('receipt', {})
            return fetch.get(key, False)

        if any(get(rep, 'type', True) == 'unavailable' for rep in replenishments):
            return self._format_receipt_date('unavailable')
        if product.type != 'product':
            return self._format_receipt_date('available')

        has_to_order_line = any(rep.get('summary', {}).get('model') == 'to_order' for rep in replenishments)
        reserved_quantity = self._get_reserved_qty(move, warehouse, replenish_data)
        missing_quantity = move.product_uom_qty - reserved_quantity
        free_qty = product.uom_id._compute_quantity(product.free_qty, move.product_uom)
        if float_compare(missing_quantity, 0.0, precision_rounding=move.product_uom.rounding) <= 0 \
           or (not has_to_order_line
               and float_compare(missing_quantity, free_qty, precision_rounding=move.product_uom.rounding) <= 0):
            return self._format_receipt_date('available')

        max_date = max(map(lambda rep: get(rep, 'date', True), replenishments), default=fields.datetime.today())
        if has_to_order_line or any(get(rep, 'type', True) == 'estimated' for rep in replenishments):
            return self._format_receipt_date('estimated', max_date)
        else:
            return self._format_receipt_date('expected', max_date)

    def _get_replenishment_lines(self, production, move_raw, replenish_data, level, current_index):
        product = move_raw.product_id
        currency = (production.company_id or self.env.company).currency_id
        forecast = replenish_data['products'][product.id].get('forecast', [])
        current_lines = filter(lambda line: line.get('document_in', False) and line.get('document_out', False)
                               and line['document_out'].get('id', False) == production.id and not line.get('already_used'), forecast)
        total_ordered = 0
        replenishments = []
        for count, forecast_line in enumerate(current_lines):
            if float_compare(total_ordered, move_raw.product_uom_qty, precision_rounding=move_raw.product_uom.rounding) == 0:
                # If a same product is used twice in the same MO, don't duplicate the replenishment lines
                break
            doc_in = self.env[forecast_line['document_in']['_name']].browse(forecast_line['document_in']['id'])
            replenishment_index = f"{current_index}{count}"
            replenishment = {}
            forecast_uom_id = forecast_line['uom_id']
            replenishment['summary'] = {
                'level': level + 1,
                'index': replenishment_index,
                'id': doc_in.id,
                'model': doc_in._name,
                'name': doc_in.display_name,
                'product_model': product._name,
                'product_id': product.id,
                'state': doc_in.state,
                'formatted_state': self._format_state(doc_in),
                'quantity': min(move_raw.product_uom_qty, forecast_uom_id._compute_quantity(forecast_line['quantity'], move_raw.product_uom)),  # Avoid over-rounding
                'uom_name': move_raw.product_uom.display_name,
                'uom_precision': self._get_uom_precision(forecast_line['uom_id']['rounding']),
                'mo_cost': forecast_line.get('cost', self._get_replenishment_cost(product, forecast_line['quantity'], forecast_uom_id, currency, forecast_line.get('move_in'))),
                'product_cost': currency.round(forecast_uom_id._compute_quantity(forecast_line['quantity'], product.uom_id) * product.standard_price),
                'currency_id': currency.id,
                'currency': currency,
            }
            if doc_in._name == 'mrp.production':
                replenishment['components'] = self._get_components_data(doc_in, replenish_data, level + 2, replenishment_index)
                replenishment['operations'] = self._get_operations_data(doc_in, level + 2, replenishment_index)
                replenishment['summary']['mo_cost'] = currency.round(sum(component.get('summary', {}).get('mo_cost', 0.0) for component in replenishment['components']) + replenishment['operations'].get('summary', {}).get('mo_cost', 0.0))
            replenishment['summary']['receipt'] = self._check_planned_start(production.date_start, self._get_replenishment_receipt(doc_in, replenishment.get('components', [])))
            replenishments.append(replenishment)
            forecast_line['already_used'] = True
            total_ordered += replenishment['summary']['quantity']

        # Add "In transit" line if necessary
        in_transit_line = self._add_transit_line(move_raw, forecast, production, level, current_index)
        if in_transit_line:
            total_ordered += in_transit_line['summary']['quantity']
            replenishments.append(in_transit_line)

        reserved_quantity = self._get_reserved_qty(move_raw, production.warehouse_id, replenish_data)
        # Avoid creating a "to_order" line to compensate for missing stock (i.e. negative free_qty).
        free_qty = max(0, product.uom_id._compute_quantity(product.free_qty, move_raw.product_uom))
        missing_quantity = move_raw.product_uom_qty - (reserved_quantity + free_qty + total_ordered)
        if product.type == 'product' and float_compare(missing_quantity, 0, precision_rounding=move_raw.product_uom.rounding) > 0:
            # Need to order more products to fulfill the need
            resupply_rules = replenish_data['products'][product.id].get('resupply_rules', [])
            rules_delay = sum(rule.delay for rule in resupply_rules)
            resupply_data = self._get_resupply_data(resupply_rules, rules_delay, missing_quantity, move_raw.product_uom, product, production.warehouse_id)

            to_order_line = {'summary': {
                'level': level + 1,
                'index': f"{current_index}TO",
                'name': _("To Order"),
                'model': "to_order",
                'product_model': product._name,
                'product_id': product.id,
                'quantity': missing_quantity,
                'replenish_quantity': move_raw.product_uom._compute_quantity(missing_quantity, product.uom_id),
                'uom_name': move_raw.product_uom.display_name,
                'uom_precision': self._get_uom_precision(move_raw.product_uom.rounding),
                'product_cost': currency.round(product.standard_price * move_raw.product_uom._compute_quantity(missing_quantity, product.uom_id)),
                'currency_id': currency.id,
                'currency': currency,
            }}
            if resupply_data:
                to_order_line['summary']['mo_cost'] = currency.round(resupply_data['cost'])
                to_order_line['summary']['receipt'] = self._check_planned_start(production.date_start, self._format_receipt_date('estimated', fields.datetime.today() + timedelta(days=resupply_data['delay'])))
            else:
                to_order_line['summary']['mo_cost'] = currency.round(product.standard_price * move_raw.product_uom._compute_quantity(missing_quantity, product.uom_id))
                to_order_line['summary']['receipt'] = self._format_receipt_date('unavailable')
            replenishments.append(to_order_line)

        return replenishments

    def _add_transit_line(self, move_raw, forecast, production, level, current_index):
        in_transit = next(filter(lambda line: line.get('in_transit') and line.get('document_out') and line['document_out'].get('id') == production.id, forecast), None)
        if not in_transit:
            return None

        product = move_raw.product_id
        currency = (production.company_id or self.env.company).currency_id
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        receipt_date = datetime.strptime(in_transit['delivery_date'], lg.date_format)
        return {'summary': {
            'level': level + 1,
            'index': f"{current_index}IT",
            'name': _("In Transit"),
            'model': "in_transit",
            'product_model': product._name,
            'product_id': product.id,
            'quantity': min(move_raw.product_uom_qty, in_transit['uom_id']._compute_quantity(in_transit['quantity'], move_raw.product_uom)),  # Avoid over-rounding
            'uom_name': move_raw.product_uom.display_name,
            'uom_precision': self._get_uom_precision(move_raw.product_uom.rounding),
            'mo_cost': self._get_replenishment_cost(product, in_transit['quantity'], in_transit['uom_id'], currency),
            'product_cost': currency.round(product.standard_price * in_transit['uom_id']._compute_quantity(in_transit['quantity'], product.uom_id)),
            'receipt': self._check_planned_start(production.date_start, self._format_receipt_date('expected', receipt_date)),
            'currency_id': currency.id,
            'currency': currency,
        }}

    def _get_replenishment_cost(self, product, quantity, uom_id, currency, move_in=False):
        return currency.round(product.standard_price * uom_id._compute_quantity(quantity, product.uom_id))

    def _get_replenishment_receipt(self, doc_in, components):
        if doc_in._name == 'stock.picking':
            return self._format_receipt_date('expected', doc_in.scheduled_date)

        if doc_in._name == 'mrp.production':
            max_date_start = doc_in.date_start
            all_available = True
            some_unavailable = False
            some_estimated = False
            for component in components:
                if component['summary']['receipt']['date']:
                    max_date_start = max(max_date_start, component['summary']['receipt']['date'])
                all_available = all_available and component['summary']['receipt']['type'] == 'available'
                some_unavailable = some_unavailable or component['summary']['receipt']['type'] == 'unavailable'
                some_estimated = some_estimated or component['summary']['receipt']['type'] == 'estimated'

            if some_unavailable:
                return self._format_receipt_date('unavailable')
            if all_available:
                return self._format_receipt_date('expected', doc_in.date_finished)

            new_date = max_date_start + timedelta(days=doc_in.bom_id.produce_delay)
            receipt_state = 'estimated' if some_estimated else 'expected'
            return self._format_receipt_date(receipt_state, new_date)
        return self._format_receipt_date('unavailable')

    def _format_receipt_date(self, state, date=False):
        if state == 'available':
            return {'display': _("Available"), 'type': 'available', 'decorator': 'success', 'date': False}
        elif state == 'estimated':
            return {'display': _("Estimated %s", format_date(self.env, date)), 'type': 'estimated', 'decorator': False, 'date': date}
        elif state == 'expected':
            return {'display': _("Expected %s", format_date(self.env, date)), 'type': 'expected', 'decorator': 'warning', 'date': date}
        else:
            return {'display': _("Not Available"), 'type': 'unavailable', 'decorator': 'danger', 'date': False}

    def _get_replenishments_from_forecast(self, production, replenish_data):
        products = production.move_raw_ids.product_id
        unknown_products = products.filtered(lambda product: product.id not in replenish_data.get('products', {}))
        if unknown_products:
            warehouse = production.warehouse_id
            wh_location_ids = self._get_warehouse_locations(warehouse, replenish_data)
            forecast_lines = self.env['stock.forecasted_product_product']._get_report_lines(False, unknown_products.ids, wh_location_ids, warehouse.lot_stock_id, read=False)
            for product in unknown_products:
                extra_docs = self._get_extra_replenishments(product)
                # Sorting the extra documents so that the ones flagged with an explicit production_id are on top of the list.
                extra_docs.sort(key=lambda ex: ex.get('production_id', False), reverse=True)
                product_forecast_lines = list(filter(lambda line: line.get('product', {}).get('id') == product.id, forecast_lines))
                replenish_data['products'][product.id] = {
                    'forecast': self._add_extra_in_forecast(product_forecast_lines, extra_docs, product.uom_id.rounding),
                    'resupply_rules': product._get_rules_from_location(production.warehouse_id.lot_stock_id),
                }

        return replenish_data

    def _add_extra_in_forecast(self, forecast_lines, extras, product_rounding):
        if not extras:
            return forecast_lines

        lines_with_extras = []
        for forecast_line in forecast_lines:
            if forecast_line.get('document_in', False) or forecast_line.get('replenishment_filled'):
                lines_with_extras.append(forecast_line)
                continue
            line_qty = forecast_line['quantity']
            if forecast_line.get('document_out', False) and forecast_line['document_out']['_name'] == 'mrp.production':
                production_id = forecast_line['document_out']['id']
            else:
                production_id = False
            index_to_remove = []
            for index, extra in enumerate(extras):
                if float_is_zero(extra['quantity'], precision_rounding=product_rounding):
                    index_to_remove.append(index)
                    continue
                if production_id and extra.get('production_id', False) and extra['production_id'] != production_id:
                    continue
                if 'init_quantity' not in extra:
                    extra['init_quantity'] = extra['quantity']
                converted_qty = extra['uom']._compute_quantity(extra['quantity'], forecast_line['uom_id'])
                taken_from_extra = min(line_qty, converted_qty)
                ratio = taken_from_extra / extra['uom']._compute_quantity(extra['init_quantity'], forecast_line['uom_id'])
                line_qty -= taken_from_extra
                # Create copy of the current forecast line to add a possible replenishment.
                # Needs to be a copy since it might take multiple replenishment to fulfill a single "out" line.
                new_extra_line = copy.copy(forecast_line)
                new_extra_line['quantity'] = taken_from_extra
                new_extra_line['document_in'] = {
                    '_name': extra['_name'],
                    'id': extra['id'],
                }
                new_extra_line['cost'] = extra['cost'] * ratio
                lines_with_extras.append(new_extra_line)
                extra['quantity'] -= forecast_line['uom_id']._compute_quantity(taken_from_extra, extra['uom'])
                if float_compare(extra['quantity'], 0, precision_rounding=product_rounding) <= 0:
                    index_to_remove.append(index)
                if float_is_zero(line_qty, precision_rounding=product_rounding):
                    break

            for index in reversed(index_to_remove):
                del extras[index]

        return lines_with_extras

    def _get_extra_replenishments(self, product):
        return []

    def _get_resupply_data(self, rules, rules_delay, quantity, uom_id, product, warehouse):
        manufacture_rules = [rule for rule in rules if rule.action == 'manufacture']
        if manufacture_rules:
            # Need to get rules from Production location to get delays before production
            wh_manufacture_rules = product._get_rules_from_location(product.property_stock_production, route_ids=warehouse.route_ids)
            wh_manufacture_rules -= rules
            rules_delay += sum(rule.delay for rule in wh_manufacture_rules)
            related_bom = self.env['mrp.bom']._bom_find(product)[product]
            if not related_bom:
                return False
            return {
                'delay': related_bom.produce_delay + rules_delay,
                'cost': product.standard_price * uom_id._compute_quantity(quantity, product.uom_id),
            }
        return False

    def _get_warehouse_locations(self, warehouse, replenish_data):
        if not replenish_data['warehouses'].get(warehouse.id):
            replenish_data['warehouses'][warehouse.id] = [loc['id'] for loc in self.env['stock.location'].search_read(
                [('id', 'child_of', warehouse.view_location_id.id)],
                ['id']
            )]
        return replenish_data['warehouses'][warehouse.id]

    def _get_reserved_qty(self, move_raw, warehouse, replenish_data):
        if not replenish_data['qty_reserved'].get(move_raw):
            total_reserved = 0
            wh_location_ids = self._get_warehouse_locations(warehouse, replenish_data)
            linked_moves = self.env['stock.move'].browse(move_raw._rollup_move_origs()).filtered(lambda m: m.location_id.id in wh_location_ids or m.location_dest_id.id not in wh_location_ids)
            for move in linked_moves:
                if move.state not in ('partially_available', 'assigned'):
                    continue
                # count reserved stock in move_raw's uom
                reserved = move.product_uom._compute_quantity(move.reserved_availability, move_raw.product_uom)
                # check if the move reserved qty was counted before (happens if multiple outs share pick/pack)
                reserved = min(reserved - move.product_uom._compute_quantity(replenish_data['qty_already_reserved'][move], move_raw.product_uom), move_raw.product_uom_qty)
                total_reserved += reserved
                replenish_data['qty_already_reserved'][move] += move_raw.product_uom._compute_quantity(reserved, move.product_uom)
                if float_compare(total_reserved, move_raw.product_qty, precision_rounding=move.product_id.uom_id.rounding) >= 0:
                    break
            replenish_data['qty_reserved'][move_raw] = total_reserved

        return replenish_data['qty_reserved'][move_raw]
