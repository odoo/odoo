# -*- coding: utf-8 -*-

import copy
import json
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_compare, float_repr, float_round, float_is_zero, format_date, get_lang
from datetime import datetime, timedelta
from math import log10


class ReportMrpReport_Mo_Overview(models.AbstractModel):
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
        docs = []
        for prod_id in docids:
            doc = self._get_report_data(prod_id)
            docs.append(self._include_pdf_specifics(doc, data))
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.production',
            'docs': docs,
        }

    def _include_pdf_specifics(self, doc, data=None):
        def get_color(decorator):
            return f"text-{decorator}" if decorator else ''

        if not data:
            data = {}
        footer_colspan = 2  # Name & Quantity
        doc['show_replenishments'] = data.get('replenishments') == '1'
        if doc['show_replenishments']:
            footer_colspan += 1
        doc['show_availabilities'] = data.get('availabilities') == '1'
        if doc['show_availabilities']:
            footer_colspan += 2  # Free to use / On Hand & Reserved
        doc['show_receipts'] = data.get('receipts') == '1'
        if doc['show_receipts']:
            footer_colspan += 1
        doc['show_unit_costs'] = data.get('unitCosts') == '1'
        if doc['show_unit_costs']:
            footer_colspan += 1
        doc['show_mo_costs'] = data.get('moCosts') == '1'
        doc['show_bom_costs'] = data.get('bomCosts') == '1'
        doc['show_real_costs'] = data.get('realCosts') == '1'
        doc['show_uom'] = self.env.user.has_group('uom.group_uom')
        if doc['show_uom']:
            footer_colspan += 1
        doc['data_mo_unit_cost'] = doc['summary'].get('mo_cost', 0) / (doc['summary'].get('quantity') or 1)
        doc['data_bom_unit_cost'] = doc['summary'].get('bom_cost', 0) / (doc['summary'].get('quantity') or 1)
        doc['data_real_unit_cost'] = doc['summary'].get('real_cost', 0) / (doc['summary'].get('quantity') or 1)
        doc['unfolded_ids'] = set(json.loads(data.get('unfoldedIds', '[]')))
        doc['footer_colspan'] = footer_colspan
        doc['get_color'] = get_color
        return doc

    def _get_display_context(self):
        return {
            'show_uom': self.env.user.has_group('uom.group_uom'),
        }

    def _get_report_data(self, production_id):
        production = self.env['mrp.production'].browse(production_id)
        # Necessary to fetch the right quantities for multi-warehouse
        production = production.with_context(warehouse_id=production.warehouse_id.id)

        components = self._get_components_data(production, level=1, current_index='')
        operations = self._get_operations_data(production, level=1, current_index='')
        initial_mo_cost, initial_bom_cost, initial_real_cost = self._compute_cost_sums(components, operations)

        if production.bom_id:
            currency = (production.company_id or self.env.company).currency_id
            missing_components = (bom_line for bom_line in production.bom_id.bom_line_ids if bom_line not in (production.move_raw_ids.bom_line_id + self._get_kit_bom_lines(production.bom_id)))
            missing_operations = (bom_line for bom_line in production.bom_id.operation_ids if bom_line not in production.workorder_ids.operation_id)
            for line in missing_components:
                line_cost = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line.product_qty
                initial_bom_cost += currency.round(line_cost * production.product_uom_qty / production.bom_id.product_qty)
            for operation in missing_operations:
                cost = (operation._get_duration_expected(production.product_id, production.product_qty) / 60.0) * operation.workcenter_id.costs_hour
                bom_cost = self.env.company.currency_id.round(cost)
                initial_bom_cost += currency.round(bom_cost * production.product_uom_qty / production.bom_id.product_qty)

        remaining_cost_share, byproducts = self._get_byproducts_data(production, initial_mo_cost, initial_bom_cost, initial_real_cost, level=1, current_index='')
        summary = self._get_mo_summary(production, components, operations, initial_mo_cost, initial_bom_cost, initial_real_cost, remaining_cost_share)
        extra_lines = self._get_report_extra_lines(summary, components, operations, production)
        return {
            'id': production.id,
            'name': production.display_name,
            'summary': summary,
            'components': components,
            'operations': operations,
            'byproducts': byproducts,
            'extras': extra_lines,
            'cost_breakdown': self._get_cost_breakdown_data(production, extra_lines, remaining_cost_share),
        }

    def _get_report_extra_lines(self, summary, components, operations, production):
        currency = summary.get('currency', self.env.company.currency_id)
        unit_mo_cost = currency.round(summary.get('mo_cost', 0) / (summary.get('quantity') or 1))
        unit_bom_cost = currency.round(summary.get('bom_cost', 0) / (summary.get('quantity') or 1))
        unit_real_cost = currency.round(summary.get('real_cost', 0) / (summary.get('quantity') or 1))
        extras = {
            'unit_mo_cost': unit_mo_cost,
            'unit_bom_cost': unit_bom_cost,
            'unit_real_cost': unit_real_cost,
        }
        if production.state == 'done':
            production_qty = summary.get('quantity') or 1.0
            extras['total_mo_cost_components'] = sum(compo.get('summary', {}).get('mo_cost', 0.0) for compo in components)
            extras['total_bom_cost_components'] = sum(compo.get('summary', {}).get('bom_cost', 0.0) for compo in components)
            extras['total_real_cost_components'] = sum(compo.get('summary', {}).get('real_cost', 0.0) for compo in components)
            extras['unit_mo_cost_components'] = extras['total_mo_cost_components'] / production_qty
            extras['unit_bom_cost_components'] = extras['total_bom_cost_components'] / production_qty
            extras['unit_real_cost_components'] = extras['total_real_cost_components'] / production_qty
            extras['total_mo_cost_operations'] = operations.get('summary', {}).get('mo_cost', 0.0)
            extras['total_bom_cost_operations'] = operations.get('summary', {}).get('bom_cost', 0.0)
            extras['total_real_cost_operations'] = operations.get('summary', {}).get('real_cost', 0.0)
            extras['unit_mo_cost_operations'] = extras['total_mo_cost_operations'] / production_qty
            extras['unit_bom_cost_operations'] = extras['total_bom_cost_operations'] / production_qty
            extras['unit_real_cost_operations'] = extras['total_real_cost_operations'] / production_qty
            extras['total_mo_cost'] = extras['total_mo_cost_components'] + extras['total_mo_cost_operations']
            extras['total_bom_cost'] = extras['total_bom_cost_components'] + extras['total_bom_cost_operations']
            extras['total_real_cost'] = extras['total_real_cost_components'] + extras['total_real_cost_operations']
        return extras

    def _get_cost_breakdown_data(self, production, extras, remaining_cost_share):
        if production.state != 'done' or not production.move_byproduct_ids:
            return []

        # Prepare byproducts data
        quantities_by_product = defaultdict(float)
        total_cost_by_product = defaultdict(float)
        component_cost_by_product = defaultdict(float)
        operation_cost_by_product = defaultdict(float)
        for bp_move in production.move_byproduct_ids:
            # Byproducts without cost share are irrelevant in a cost breakdrown.
            if bp_move.state == 'cancel' or float_is_zero(bp_move.cost_share, precision_digits=2):
                continue
            # As UoMs can vary, we use the default UoM of each product
            quantities_by_product[bp_move.product_id] += bp_move.product_uom._compute_quantity(bp_move.quantity, bp_move.product_id.uom_id, rounding_method='HALF-UP')
            cost_share = bp_move.cost_share / 100
            total_cost_by_product[bp_move.product_id] += extras['total_real_cost'] * cost_share
            component_cost_by_product[bp_move.product_id] += extras['total_real_cost_components'] * cost_share
            operation_cost_by_product[bp_move.product_id] += extras['total_real_cost_operations'] * cost_share

        # Add finished product to its own default UoM (not the production UoM)
        breakdown_lines = [self._format_cost_breakdown_lines(0, production.product_id.display_name, production.product_id.uom_id.display_name,
                                                             (extras['total_real_cost_components'] * remaining_cost_share) / production.product_uom_qty,
                                                             (extras['total_real_cost_operations'] * remaining_cost_share) / production.product_uom_qty,
                                                             (extras['total_real_cost'] * remaining_cost_share) / production.product_uom_qty)]
        for index, product in enumerate(quantities_by_product.keys()):
            breakdown_lines.append(self._format_cost_breakdown_lines(index + 1, product.display_name, product.uom_id.display_name,
                                                                     component_cost_by_product[product] / quantities_by_product[product],
                                                                     operation_cost_by_product[product] / quantities_by_product[product],
                                                                     total_cost_by_product[product] / quantities_by_product[product]))
        return breakdown_lines

    def _format_cost_breakdown_lines(self, index, product_name, uom_name, component_cost, operation_cost, total_cost):
        return {
            'index': f"BR{index}",
            'name': product_name,
            'unit_avg_cost_component': component_cost,
            'unit_avg_cost_operation': operation_cost,
            'unit_avg_total_cost': total_cost,
            'uom_name': uom_name,
        }

    def _get_mo_summary(self, production, components, operations, current_mo_cost, current_bom_cost, current_real_cost, remaining_cost_share):
        currency = (production.company_id or self.env.company).currency_id
        product = production.product_id
        mo_cost = current_mo_cost * remaining_cost_share
        bom_cost = current_bom_cost * remaining_cost_share
        real_cost = current_real_cost * remaining_cost_share
        decorator = self._get_comparison_decorator(real_cost if self._is_production_started(production) else bom_cost, mo_cost, currency.rounding)
        mo_cost_decorator = decorator if any(compo['summary']['mo_cost_decorator'] == decorator for compo in (components + [operations])) else False
        real_cost_temp_decorator = self._get_comparison_decorator(mo_cost, real_cost, currency.rounding) if self._is_production_started(production) else False
        real_cost_decorator = real_cost_temp_decorator if any(compo['summary']['real_cost_decorator'] == real_cost_temp_decorator for compo in (components + [operations])) else False
        return {
            'level': 0,
            'model': production._name,
            'id': production.id,
            'name': production.product_id.display_name,
            'product_model': production.product_id._name,
            'product_id': production.product_id.id,
            'state': production.state,
            'formatted_state': self._format_state(production, components),
            'has_bom': bool(production.bom_id),
            'quantity': production.product_qty if production.state != 'done' else production.qty_produced,
            'uom_name': production.product_uom_id.display_name,
            'uom_precision': self._get_uom_precision(production.product_uom_id.rounding or 0.01),
            'quantity_free': product.uom_id._compute_quantity(max(product.free_qty, 0), production.product_uom_id) if product.is_storable else False,
            'quantity_on_hand': product.uom_id._compute_quantity(product.qty_available, production.product_uom_id) if product.is_storable else False,
            'quantity_reserved': 0.0,
            'receipt': self._check_planned_start(production.date_deadline, self._get_replenishment_receipt(production, components)),
            'unit_cost': self._get_unit_cost(production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id)),
            'mo_cost': currency.round(mo_cost),
            'mo_cost_decorator': mo_cost_decorator,
            'real_cost_decorator': real_cost_decorator if not mo_cost_decorator else False,
            'bom_cost': currency.round(bom_cost),
            'real_cost': currency.round(real_cost),
            'currency_id': currency.id,
            'currency': currency,
        }

    def _get_unit_cost(self, move):
        if not move:
            return 0.0
        return move.product_id.uom_id._compute_price(move.product_id.standard_price, move.product_uom)

    def _format_state(self, record, components=False):
        """ For MOs, provide a custom state based on the demand vs quantities available for components.
        All other records types will provide their standard state value.
        :param dict components: components in the structure provided by `_get_components_data`
        :return: string to be used as custom state
        """
        if record._name != 'mrp.production' or record.state not in ('draft', 'confirmed') or not components:
            return dict(record._fields['state']._description_selection(self.env)).get(record.state)
        components_qty_to_produce = defaultdict(float)
        components_qty_reserved = defaultdict(float)
        components_qty_free = defaultdict(float)
        for component in components:
            component = component["summary"]
            product = component["product"]
            if not product.is_storable:
                continue
            uom = component["uom"]
            components_qty_to_produce[product] += uom._compute_quantity(component["quantity"], product.uom_id)
            components_qty_reserved[product] += uom._compute_quantity(component["quantity_reserved"], product.uom_id)
            components_qty_free[product] = uom._compute_quantity(component["quantity_free"], product.uom_id)
        producible_qty = record.product_qty
        for product, comp_qty_to_produce in components_qty_to_produce.items():
            if float_is_zero(comp_qty_to_produce, precision_rounding=product.uom_id.rounding):
                continue
            comp_producible_qty = float_round(
                record.product_qty * (components_qty_reserved[product] + components_qty_free[product]) / comp_qty_to_produce,
                precision_rounding=record.product_uom_id.rounding, rounding_method='DOWN'
            )
            if float_compare(comp_producible_qty, 0, precision_rounding=record.product_uom_id.rounding) <= 0:
                return _("Not Ready")
            producible_qty = min(comp_producible_qty, producible_qty)
        if float_compare(producible_qty, 0, precision_rounding=record.product_uom_id.rounding) <= 0:
            return _("Not Ready")
        elif float_compare(producible_qty, record.product_qty, precision_rounding=record.product_uom_id.rounding) == -1:
            producible_qty = float_repr(producible_qty, self.env['decimal.precision'].precision_get('Product Unit'))
            return _("%(producible_qty)s Ready", producible_qty=producible_qty)
        return _("Ready")

    def _get_uom_precision(self, uom_rounding):
        return max(0, int(-(log10(uom_rounding))))

    def _get_comparison_decorator(self, expected, current, rounding):
        compare = float_compare(current, expected, precision_rounding=rounding)
        if compare == 0 or expected is False or current is False:
            return False
        elif compare > 0:
            return 'danger'
        else:
            return 'success'

    def _get_bom_operation_cost(self, workorder, production, kit_operation=False):
        operations = production.bom_id.operation_ids + kit_operation if kit_operation else production.bom_id.operation_ids
        if workorder.operation_id not in operations:
            return False
        capacity = workorder.operation_id.workcenter_id._get_capacity(production.product_id)
        operation_cycle = float_round(production.product_uom_qty / capacity, precision_rounding=1, rounding_method='UP')
        return workorder.operation_id._compute_operation_cost() * operation_cycle

    def _get_operations_data(self, production, level=0, current_index=False):
        if production.state == "done":
            return self._get_finished_operation_data(production, level, current_index)
        currency = (production.company_id or self.env.company).currency_id
        operation_uom = _("Minutes")
        operations = []
        total_expected_time = 0.0
        total_current_time = 0.0
        total_bom_cost = False
        total_expected_cost = 0.0
        total_real_cost = 0.0
        for index, workorder in enumerate(production.workorder_ids):
            wo_duration = workorder.get_duration()
            mo_cost = workorder._compute_expected_operation_cost()
            bom_cost = self._get_bom_operation_cost(workorder, production, kit_operation=self._get_kit_operations(production.bom_id))
            real_cost = workorder._compute_current_operation_cost()
            real_cost_decorator = False
            mo_cost_decorator = False
            if self._is_production_started(production):
                mo_cost = mo_cost if workorder.duration_expected else workorder._get_current_theorical_operation_cost()
                real_cost_decorator = self._get_comparison_decorator(mo_cost, real_cost, 0.01)
            elif production.state == "confirmed":
                if workorder.operation_id not in production.bom_id.operation_ids:
                    bom_cost = 0
                mo_cost_decorator = self._get_comparison_decorator(bom_cost, mo_cost, 0.01)
            else:
                if not production.bom_id:
                    bom_cost = mo_cost
                mo_cost_decorator = 'danger' if isinstance(bom_cost, bool) and not bom_cost else self._get_comparison_decorator(bom_cost, mo_cost, 0.01)
            is_workorder_started = not float_is_zero(wo_duration, precision_digits=2)

            operations.append({
                'level': level,
                'index': f"{current_index}W{index}",
                'model': workorder._name,
                'id': workorder.id,
                'name': workorder.name,
                'state': workorder.state,
                'formatted_state': self._format_state(workorder),
                'quantity': workorder.duration_expected if float_is_zero(wo_duration, precision_digits=2) else wo_duration,
                'uom_name': operation_uom,
                'production_id': production.id,
                'unit_cost': mo_cost / (workorder.duration_expected or 1),
                'mo_cost': mo_cost,
                'mo_cost_decorator': mo_cost_decorator,
                'bom_cost': bom_cost,
                'real_cost': real_cost,
                'real_cost_decorator': real_cost_decorator,
                'currency_id': currency.id,
                'currency': currency,
            })
            total_expected_time += workorder.duration_expected
            total_current_time += wo_duration if is_workorder_started else workorder.duration_expected
            total_expected_cost += mo_cost
            total_bom_cost = self._sum_bom_cost(total_bom_cost, bom_cost)
            total_real_cost += real_cost

        mo_cost_decorator = False
        if not self._is_production_started(production):
            mo_cost_decorator = self._get_comparison_decorator(total_bom_cost or 0.0, total_expected_cost, 0.01)

        return {
            'summary': {
                'index': f"{current_index}W",
                'quantity': total_current_time,
                'mo_cost': total_expected_cost,
                'mo_cost_decorator': mo_cost_decorator,
                'bom_cost': total_bom_cost,
                'real_cost': total_real_cost,
                'real_cost_decorator': self._get_comparison_decorator(total_expected_cost, total_real_cost, 0.01) if self._is_production_started(production) else False,
                'uom_name': operation_uom,
                'currency_id': currency.id,
                'currency': currency,
            },
            'details': operations,
        }

    def _get_kit_operations(self, bom):
        operations = self.env['mrp.routing.workcenter']
        for bom_line in bom.bom_line_ids:
            if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom':
                operations += bom_line.child_bom_id.operation_ids + self._get_kit_operations(bom_line.child_bom_id)
        return operations

    def _get_kit_bom_lines(self, bom):
        bom_lines = self.env['mrp.bom.line']
        for bom_line in bom.bom_line_ids:
            if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom':
                bom_lines += bom_line + bom_line.child_bom_id.bom_line_ids + self._get_kit_bom_lines(bom_line.child_bom_id)
        return bom_lines

    def _get_finished_operation_data(self, production, level=0, current_index=False):
        currency = (production.company_id or self.env.company).currency_id
        done_operation_uom = _("Hours")
        operations = []
        total_duration = total_duration_expected = total_cost = total_mo_cost = 0
        total_bom_cost = False
        for index, workorder in enumerate(production.workorder_ids):
            hourly_cost = workorder.costs_hour or workorder.workcenter_id.costs_hour
            duration = workorder.get_duration() / 60
            operation_cost = duration * hourly_cost
            mo_cost = workorder._compute_expected_operation_cost(without_employee_cost=True) if workorder.duration_expected\
                        else workorder._get_current_theorical_operation_cost(without_employee_cost=True)
            bom_cost = self._get_bom_operation_cost(workorder, production)
            total_duration += duration
            total_duration_expected += workorder.duration_expected
            total_cost += operation_cost
            total_mo_cost += mo_cost
            total_bom_cost = self._sum_bom_cost(total_bom_cost, bom_cost)
            operations.append({
                'level': level,
                'index': f"{current_index}W{index}",
                'name': f"{workorder.workcenter_id.display_name}: {workorder.display_name}",
                'quantity': duration,
                'uom_name': done_operation_uom,
                'uom_precision': 4,
                'unit_cost': hourly_cost,
                'mo_cost': currency.round(mo_cost),
                'mo_cost_decorator': False,
                'bom_cost': currency.round(bom_cost) if bom_cost else False,
                'real_cost': currency.round(operation_cost),
                'real_cost_decorator': self._get_comparison_decorator(mo_cost, operation_cost, currency.rounding),
                'currency_id': currency.id,
                'currency': currency,
            })
        return {
            'summary': {
                'index': f"{current_index}W",
                'done': True,
                'quantity': total_duration,
                'mo_cost': total_mo_cost,
                'mo_cost_decorator': False,
                'bom_cost': total_bom_cost,
                'real_cost': total_cost,
                'real_cost_decorator': self._get_comparison_decorator(total_mo_cost, total_cost, currency.rounding),
                'uom_name': done_operation_uom,
                'currency_id': currency.id,
                'currency': currency,
            },
            'details': operations,
        }

    def _get_byproducts_data(self, production, current_mo_cost, current_bom_cost, current_real_cost, level=0, current_index=False):
        currency = (production.company_id or self.env.company).currency_id
        byproducts = []
        byproducts_cost_portion = 0
        total_mo_cost = 0
        total_bom_cost = False
        total_real_cost = 0
        for index, move_bp in enumerate(production.move_byproduct_ids):
            product = move_bp.product_id
            cost_share = move_bp.cost_share / 100
            byproducts_cost_portion += cost_share
            mo_cost = current_mo_cost * cost_share
            bom_cost = current_bom_cost * cost_share
            real_cost = current_real_cost * cost_share
            total_mo_cost += mo_cost
            total_bom_cost = self._sum_bom_cost(total_bom_cost, bom_cost)
            total_real_cost += real_cost
            if self._is_production_started(production):
                mo_cost_decorator = self._get_comparison_decorator(real_cost, mo_cost, currency.rounding)
            else:
                mo_cost_decorator = self._get_comparison_decorator(bom_cost, mo_cost, currency.rounding)
            byproducts.append({
                'level': level,
                'index': f"{current_index}B{index}",
                'model': product._name,
                'id': product.id,
                'name': product.display_name,
                'quantity': move_bp.product_uom_qty if move_bp.state != 'done' else move_bp.quantity,
                'uom_name': move_bp.product_uom.display_name,
                'uom_precision': self._get_uom_precision(move_bp.product_uom.rounding),
                'unit_cost': self._get_unit_cost(move_bp),
                'mo_cost': currency.round(mo_cost),
                'mo_cost_decorator': mo_cost_decorator,
                'bom_cost': currency.round(bom_cost),
                'real_cost': currency.round(real_cost),
                'currency_id': currency.id,
                'currency': currency,
            })

        if self._is_production_started(production):
            mo_cost_decorator = self._get_comparison_decorator(total_real_cost, total_mo_cost, currency.rounding)
        else:
            mo_cost_decorator = self._get_comparison_decorator(total_bom_cost, total_mo_cost, currency.rounding)
        return float_round(1 - byproducts_cost_portion, precision_rounding=0.0001), {
            'summary': {
                'index': f"{current_index}B",
                'mo_cost': currency.round(total_mo_cost),
                'mo_cost_decorator': mo_cost_decorator,
                'bom_cost': currency.round(total_bom_cost),
                'real_cost': currency.round(total_real_cost),
                'currency_id': currency.id,
                'currency': currency,
            },
            'details': byproducts,
        }

    def _compute_cost_sums(self, components, operations=False):
        total_mo_cost = total_bom_cost = total_real_cost = 0
        if operations:
            total_mo_cost = operations.get('summary', {}).get('mo_cost', 0.0)
            total_bom_cost = operations.get('summary', {}).get('bom_cost', 0.0)
            total_real_cost = operations.get('summary', {}).get('real_cost', 0.0)
        for component in components:
            total_mo_cost += component.get('summary', {}).get('mo_cost', 0.0)
            total_bom_cost += component.get('summary', {}).get('bom_cost', 0.0)
            total_real_cost += component.get('summary', {}).get('real_cost', 0.0)
        return total_mo_cost, total_bom_cost, total_real_cost

    def _get_components_data(self, production, replenish_data=False, level=0, current_index=False):
        if not replenish_data:
            replenish_data = {
                'products': {},
                'warehouses': {},
                'qty_already_reserved': defaultdict(float),
                'qty_reserved': {},
            }
        components = []
        if production.state == 'done':
            replenish_data = self._get_replenishment_from_moves(production, replenish_data)
        else:
            replenish_data = self._get_replenishments_from_forecast(production, replenish_data)
        for count, move_raw in enumerate(production.move_raw_ids):
            if production.state == 'done' and float_is_zero(move_raw.quantity, precision_rounding=move_raw.product_uom.rounding):
                # If a product wasn't consumed in the MO by the time it is done, no need to display it on the final Overview.
                continue
            component_index = f"{current_index}{count}"
            replenishments = self._get_replenishment_lines(production, move_raw, replenish_data, level, component_index)
            # If not enough replenishment -> To Order / Might get "non-available" in summary since all component won't be there in time
            components.append({
                'summary': self._format_component_move(production, move_raw, replenishments, replenish_data, level, component_index),
                'replenishments': replenishments
            })

        return components

    def _format_component_move(self, production, move_raw, replenishments, replenish_data, level, index):
        currency = (production.company_id or self.env.company).currency_id
        product = move_raw.product_id
        expected_quantity = move_raw.product_uom_qty
        current_quantity = move_raw.quantity
        replenish_mo_cost, _dummy_bom_cost, _dummy_real_cost = self._compute_cost_sums(replenishments)
        replenish_quantity = sum(rep.get('summary', {}).get('quantity', 0.0) for rep in replenishments)
        mo_quantity = current_quantity if production.state == 'done' else expected_quantity
        missing_quantity = mo_quantity - replenish_quantity
        missing_quantity_cost = self._get_component_real_cost(move_raw, missing_quantity)
        mo_cost = currency.round(replenish_mo_cost + missing_quantity_cost)
        real_cost = currency.round(self._get_component_real_cost(move_raw, current_quantity if move_raw.picked else 0))
        if production.bom_id:
            if move_raw.bom_line_id:
                bom_cost = currency.round(self._get_component_real_cost(move_raw, move_raw.bom_line_id.product_qty * production.product_uom_qty / production.bom_id.product_qty))
            else:
                bom_cost = False
        else:
            bom_cost = currency.round(self._get_component_real_cost(move_raw, expected_quantity))
        cost_to_compare = real_cost if production.state != 'confirmed' else bom_cost
        if production.state == 'draft':
            mo_cost_decorator = self._get_comparison_decorator(bom_cost, mo_cost, currency.rounding)
        else:
            cost_to_compare = real_cost if production.state != 'confirmed' else bom_cost
            mo_cost_decorator = self._get_comparison_decorator(cost_to_compare, mo_cost, currency.rounding)
        component = {
            'level': level,
            'index': index,
            'id': product.id,
            'model': product._name,
            'name': product.display_name,
            'product_model': product._name,
            'product': product,
            'product_id': product.id,
            'quantity': expected_quantity if move_raw.state != 'done' else current_quantity,
            'uom': move_raw.product_uom,
            'uom_name': move_raw.product_uom.display_name,
            'uom_precision': self._get_uom_precision(move_raw.product_uom.rounding),
            'quantity_free': product.uom_id._compute_quantity(max(product.free_qty, 0), move_raw.product_uom) if product.is_storable else False,
            'quantity_on_hand': product.uom_id._compute_quantity(product.qty_available, move_raw.product_uom) if product.is_storable else False,
            'quantity_reserved': self._get_reserved_qty(move_raw, production.warehouse_id, replenish_data),
            'receipt': self._check_planned_start(production.date_start, self._get_component_receipt(product, move_raw, production.warehouse_id, replenishments, replenish_data)),
            'unit_cost': self._get_unit_cost(move_raw),
            'mo_cost': mo_cost,
            'mo_cost_decorator': 'danger' if isinstance(bom_cost, bool) and not bom_cost and not self._is_production_started(production) else mo_cost_decorator,
            'bom_cost': bom_cost,
            'real_cost': real_cost,
            'real_cost_decorator': False,
            'currency_id': currency.id,
            'currency': currency,
        }
        if not product.is_storable:
            return component
        if any(rep.get('summary', {}).get('model') == 'to_order' for rep in replenishments):
            # Means that there's an extra "To Order" line summing up what's left to order.
            component['formatted_state'] = _("To Order")
            component['state'] = 'to_order'

        return component

    def _get_component_real_cost(self, move_raw, quantity):
        if float_is_zero(quantity, precision_rounding=move_raw.product_uom.rounding):
            return 0
        return self._get_unit_cost(move_raw) * quantity

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
        if not product.is_storable or move.state == 'done':
            return self._format_receipt_date('available')

        has_to_order_line = any(rep.get('summary', {}).get('model') == 'to_order' for rep in replenishments)
        reserved_quantity = self._get_reserved_qty(move, warehouse, replenish_data)
        missing_quantity = move.product_uom_qty - reserved_quantity
        free_qty = product.uom_id._compute_quantity(product.free_qty, move.product_uom)
        if float_compare(missing_quantity, 0.0, precision_rounding=move.product_uom.rounding) <= 0 \
           or (not has_to_order_line
               and float_compare(missing_quantity, free_qty, precision_rounding=move.product_uom.rounding) <= 0):
            return self._format_receipt_date('available')

        replenishments_with_date = list(filter(lambda r: r.get('summary', {}).get('receipt', {}).get('date'), replenishments))
        max_date = max([get(rep, 'date', True) for rep in replenishments_with_date], default=fields.Date.today())
        if has_to_order_line or any(get(rep, 'type', True) == 'estimated' for rep in replenishments):
            return self._format_receipt_date('estimated', max_date)
        else:
            return self._format_receipt_date('expected', max_date)

    def _get_replenishment_lines(self, production, move_raw, replenish_data, level, current_index):
        product = move_raw.product_id
        quantity = move_raw.product_uom_qty if move_raw.state != 'done' else move_raw.quantity
        reserved_quantity = self._get_reserved_qty(move_raw, production.warehouse_id, replenish_data)
        currency = (production.company_id or self.env.company).currency_id
        forecast = replenish_data['products'][product.id].get('forecast', [])
        current_lines = filter(lambda line: line.get('document_in', False) and line.get('document_out', False)
                               and line['document_out'].get('id', False) == production.id and not line.get('already_used'), forecast)
        total_ordered = 0
        replenishments = []
        for count, forecast_line in enumerate(current_lines):
            if float_compare(total_ordered, quantity - reserved_quantity, precision_rounding=move_raw.product_uom.rounding) >= 0:
                # If a same product is used twice in the same MO, don't duplicate the replenishment lines
                break
            doc_in = self.env[forecast_line['document_in']['_name']].browse(forecast_line['document_in']['id'])
            replenishment_index = f"{current_index}{count}"
            replenishment = {}
            forecast_uom_id = forecast_line['uom_id']
            line_quantity = min(quantity, forecast_uom_id._compute_quantity(forecast_line['quantity'], move_raw.product_uom))  # Avoid over-rounding
            bom_quantity = production.product_uom_qty * move_raw.bom_line_id.product_qty - (quantity - line_quantity)
            replenishment['summary'] = {
                'level': level + 1,
                'index': replenishment_index,
                'id': doc_in.id,
                'model': doc_in._name,
                'name': doc_in.display_name,
                'product_model': product._name,
                'product_id': product.id,
                'state': doc_in.state,
                'quantity': line_quantity,
                'uom_name': move_raw.product_uom.display_name,
                'uom_precision': self._get_uom_precision(forecast_line['uom_id']['rounding']),
                'unit_cost': self._get_unit_cost(move_raw),
                'mo_cost': forecast_line.get('cost', self._get_replenishment_mo_cost(product, line_quantity, move_raw.product_uom, currency, forecast_line.get('move_in'))),
                'bom_cost': currency.round(self._get_component_real_cost(move_raw, bom_quantity)) if bom_quantity else False,
                'real_cost': currency.round(self._get_component_real_cost(move_raw, line_quantity)),
                'currency_id': currency.id,
                'currency': currency,
            }
            forecast_line['already_used'] = True
            if doc_in._name == 'mrp.production':
                replenishment['components'] = self._get_components_data(doc_in, replenish_data, level + 2, replenishment_index)
                replenishment['operations'] = self._get_operations_data(doc_in, level + 2, replenishment_index)
                initial_mo_cost, initial_bom_cost, initial_real_cost = self._compute_cost_sums(replenishment['components'], replenishment['operations'])
                remaining_cost_share, byproducts = self._get_byproducts_data(doc_in, initial_mo_cost, initial_bom_cost, initial_real_cost, level + 2, replenishment_index)
                replenishment['byproducts'] = byproducts
                replenishment['summary']['mo_cost'] = initial_mo_cost * remaining_cost_share
                replenishment['summary']['bom_cost'] = initial_bom_cost * remaining_cost_share
                replenishment['summary']['real_cost'] = initial_real_cost * remaining_cost_share

            if self._is_doc_in_done(doc_in):
                replenishment['summary']['receipt'] = self._format_receipt_date('available')
            else:
                replenishment['summary']['receipt'] = self._check_planned_start(production.date_start, self._get_replenishment_receipt(doc_in, replenishment.get('components', [])))

            if self._is_production_started(production):
                replenishment['summary']['mo_cost_decorator'] = self._get_comparison_decorator(replenishment['summary']['real_cost'], replenishment['summary']['mo_cost'], replenishment['summary']['currency'].rounding)
            else:
                replenishment['summary']['mo_cost_decorator'] = self._get_comparison_decorator(replenishment['summary']['bom_cost'], replenishment['summary']['mo_cost'], replenishment['summary']['currency'].rounding)
            replenishment['summary']['formatted_state'] = self._format_state(doc_in, replenishment['components']) if doc_in._name == 'mrp.production' else self._format_state(doc_in)
            replenishments.append(replenishment)
            total_ordered += replenishment['summary']['quantity']

        # Add "In transit" line if necessary
        in_transit_line = self._add_transit_line(move_raw, forecast, production, level, current_index)
        if in_transit_line:
            total_ordered += in_transit_line['summary']['quantity']
            replenishments.append(in_transit_line)

        # Avoid creating a "to_order" line to compensate for missing stock (i.e. negative free_qty).
        free_qty = max(0, product.uom_id._compute_quantity(product.free_qty, move_raw.product_uom))
        available_qty = reserved_quantity + free_qty + total_ordered
        missing_quantity = quantity - available_qty
        bom_missing_quantity = production.product_uom_qty * move_raw.bom_line_id.product_qty - (reserved_quantity + free_qty + total_ordered)

        if product.is_storable and production.state not in ('done', 'cancel')\
           and float_compare(missing_quantity, 0, precision_rounding=move_raw.product_uom.rounding) > 0:
            # Need to order more products to fulfill the need
            resupply_rules = self._get_resupply_rules(production, product, replenish_data)
            rules_delay = sum(rule.delay for rule in resupply_rules)
            resupply_data = self._get_resupply_data(resupply_rules, rules_delay, missing_quantity, move_raw.product_uom, product, production)

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
                'real_cost': currency.round(product.standard_price * move_raw.product_uom._compute_quantity(available_qty, product.uom_id)),
                'currency_id': currency.id,
                'currency': currency,
            }}
            if resupply_data:
                mo_cost = resupply_data['currency']._convert(resupply_data['cost'], currency, (production.company_id or self.env.company), fields.Date.today())
                to_order_line['summary']['mo_cost'] = mo_cost
                to_order_line['summary']['bom_cost'] = currency.round(self._get_component_real_cost(move_raw, bom_missing_quantity))
                to_order_line['summary']['receipt'] = self._check_planned_start(production.date_start, self._format_receipt_date('estimated', fields.Datetime.today() + timedelta(days=resupply_data['delay'])))
            else:
                to_order_line['summary']['mo_cost'] = currency.round(product.standard_price * move_raw.product_uom._compute_quantity(missing_quantity, product.uom_id))
                to_order_line['summary']['bom_cost'] = currency.round(self._get_component_real_cost(move_raw, bom_missing_quantity))
                to_order_line['summary']['receipt'] = self._format_receipt_date('unavailable')
            to_order_line['summary']['unit_cost'] = currency.round(to_order_line['summary']['mo_cost'] / missing_quantity)

            if self._is_production_started(production):
                to_order_line['summary']['mo_cost_decorator'] = self._get_comparison_decorator(to_order_line['summary']['real_cost'], to_order_line['summary']['mo_cost'], currency.rounding)
            else:
                to_order_line['summary']['mo_cost_decorator'] = self._get_comparison_decorator(to_order_line['summary']['bom_cost'], to_order_line['summary']['mo_cost'], currency.rounding)

            replenishments.append(to_order_line)

        return replenishments

    def _add_transit_line(self, move_raw, forecast, production, level, current_index):
        def is_related_to_production(document, production):
            if not document:
                return False
            return document.get('_name') == production._name and document.get('id') == production.id

        in_transit = next(filter(lambda line: line.get('in_transit') and is_related_to_production(line.get('document_out'), production), forecast), None)
        if not in_transit or is_related_to_production(in_transit.get('reservation'), production):
            return None

        product = move_raw.product_id
        currency = (production.company_id or self.env.company).currency_id
        lg = self.env['res.lang']._get_data(code=self.env.user.lang) or get_lang(self.env)
        receipt_date = datetime.strptime(in_transit['delivery_date'], lg.date_format)
        bom_missing_qty = max(0, production.product_uom_qty * move_raw.bom_line_id.product_qty - (move_raw.product_uom_qty - in_transit['quantity']))
        mo_cost = self._get_replenishment_mo_cost(product, in_transit['quantity'], in_transit['uom_id'], currency)
        bom_cost = self._get_replenishment_mo_cost(product, bom_missing_qty, in_transit['uom_id'], currency) if production.bom_id else False
        real_cost = product.standard_price * in_transit['uom_id']._compute_quantity(in_transit['quantity'], product.uom_id)
        if self._is_production_started(production) or not production.bom_id:
            mo_cost_decorator = self._get_comparison_decorator(real_cost, mo_cost, currency.rounding)
        else:
            mo_cost_decorator = self._get_comparison_decorator(bom_cost, mo_cost, currency.rounding)
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
            'mo_cost': mo_cost,
            'mo_cost_decorator': mo_cost_decorator,
            'bom_cost': bom_cost,
            'real_cost': currency.round(real_cost),
            'receipt': self._check_planned_start(production.date_start, self._format_receipt_date('expected', receipt_date)),
            'currency_id': currency.id,
            'currency': currency,
        }}

    def _is_production_started(self, production):
        return production.state not in {"draft", "confirmed"}

    def _get_replenishment_mo_cost(self, product, quantity, uom_id, currency, move_in=False):
        return currency.round(product.standard_price * uom_id._compute_quantity(quantity, product.uom_id))

    def _is_doc_in_done(self, doc_in):
        if doc_in._name == 'mrp.production':
            return doc_in.state == 'done'
        return False

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
            forecast_lines = self._add_origins_to_forecast(forecast_lines)
            for product in unknown_products:
                extra_docs = self._get_extra_replenishments(product)
                # Sorting the extra documents so that the ones flagged with an explicit production_id are on top of the list.
                extra_docs.sort(key=lambda ex: ex.get('production_id', False), reverse=True)
                product_forecast_lines = list(filter(lambda line: line.get('product', {}).get('id') == product.id, forecast_lines))
                updated_forecast_lines = self._add_extra_in_forecast(product_forecast_lines, extra_docs, product.uom_id.rounding)
                replenish_data = self._set_replenish_data(updated_forecast_lines, product, replenish_data)

        return replenish_data

    def _get_replenishment_from_moves(self, production, replenish_data):
        # Go through the component's move see if we can find an incoming origin
        for component_move in production.move_raw_ids:
            product_lines = []
            product = component_move.product_id
            required_qty = component_move.product_uom_qty
            for move_origin in self.env['stock.move'].browse(component_move._rollup_move_origs()):
                doc_origin = self._get_origin(move_origin)
                if doc_origin:
                    to_uom_qty = move_origin.product_uom._compute_quantity(move_origin.product_uom_qty, component_move.product_uom)
                    used_qty = min(required_qty, to_uom_qty)
                    required_qty -= used_qty
                    # Create a fake "forecast line" so it will be processed as normal afterwards with only the required info
                    product_lines.append({
                        'document_in': {'_name': doc_origin._name, 'id': doc_origin.id},
                        'document_out': {'_name': 'mrp.production', 'id': production.id},
                        'quantity': used_qty,
                        'uom_id': component_move.product_uom,
                        'move_in': move_origin,
                        'product': product,
                    })
                if float_compare(required_qty, 0, precision_rounding=component_move.product_uom.rounding) <= 0:
                    break
            replenish_data = self._set_replenish_data(product_lines, product, replenish_data)

        return replenish_data

    def _set_replenish_data(self, new_lines, product, replenish_data):
        if product.id not in replenish_data['products']:
            replenish_data['products'][product.id] = {'forecast': []}
        replenish_data['products'][product.id]['forecast'] += new_lines
        return replenish_data

    def _get_resupply_rules(self, production, product, replenish_data):
        if not replenish_data['products'][product.id].get('resupply_rules'):
            replenish_data['products'][product.id]['resupply_rules'] = product._get_rules_from_location(production.warehouse_id.lot_stock_id)
        return replenish_data['products'][product.id]['resupply_rules']

    def _add_origins_to_forecast(self, forecast_lines):
        # Keeps the link to its origin even when the product is now in stock.
        new_lines = []
        for line in filter(lambda line: not line.get('document_in', False) and line.get('move_out', False) and line.get('replenishment_filled', False), forecast_lines):
            move_out_qty = line['move_out'].product_uom._compute_quantity(line['move_out'].product_uom_qty, line['uom_id'])
            for move_origin in self.env['stock.move'].browse(line['move_out']._rollup_move_origs()):
                doc_origin = self._get_origin(move_origin)
                if doc_origin:
                    # Remove 'in_transit' for MTO replenishments
                    line['in_transit'] = False
                    move_origin_qty = move_origin.product_uom._compute_quantity(move_origin.product_uom_qty, line['uom_id'])
                    # Move quantity matches forecast, can add origin to the line
                    if float_compare(line['quantity'], move_origin_qty, precision_rounding=line['uom_id'].rounding) == 0:
                        line['document_in'] = {'_name': doc_origin._name, 'id': doc_origin.id}
                        line['move_in'] = move_origin
                        break

                    # Quantity doesn't match, either multiple origins for a single line or multiple lines for a single origin
                    used_quantity = min(move_out_qty, move_origin_qty)
                    new_line = copy.copy(line)
                    new_line['quantity'] = used_quantity
                    new_line['document_in'] = {'_name': doc_origin._name, 'id': doc_origin.id}
                    new_line['move_in'] = move_origin
                    new_lines.append(new_line)
                    # Remove used quantity from original forecast line
                    line['quantity'] -= used_quantity

                    move_out_qty -= used_quantity
                    if float_compare(move_out_qty, 0, precision_rounding=line['move_out'].product_uom.rounding) <= 0:
                        break
        return new_lines + forecast_lines

    def _get_origin(self, move):
        if move.production_id:
            return move.production_id
        return False

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

    def _get_resupply_data(self, rules, rules_delay, quantity, uom_id, product, production):
        manufacture_rules = [rule for rule in rules if rule.action == 'manufacture']
        if manufacture_rules:
            # Need to get rules from Production location to get delays before production
            wh_manufacture_rules = product._get_rules_from_location(product.property_stock_production, route_ids=production.warehouse_id.route_ids)
            wh_manufacture_rules -= rules
            rules_delay += sum(rule.delay for rule in wh_manufacture_rules)
            related_bom = self.env['mrp.bom']._bom_find(product)[product]
            if not related_bom:
                return False
            return {
                'delay': related_bom.produce_delay + rules_delay,
                'cost': product.standard_price * uom_id._compute_quantity(quantity, product.uom_id),
                'currency': (production.company_id or self.env.company).currency_id,
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
            linked_moves = self.env['stock.move'].browse(move_raw._rollup_move_origs()).filtered(lambda m: m.location_id.id in wh_location_ids)
            for move in linked_moves:
                if move.state not in ('partially_available', 'assigned'):
                    continue
                # count reserved stock in move_raw's uom
                reserved = move.product_uom._compute_quantity(move.quantity, move_raw.product_uom)
                # check if the move reserved qty was counted before (happens if multiple outs share pick/pack)
                reserved = min(reserved - move.product_uom._compute_quantity(replenish_data['qty_already_reserved'][move], move_raw.product_uom), move_raw.product_uom_qty)
                total_reserved += reserved
                replenish_data['qty_already_reserved'][move] += move_raw.product_uom._compute_quantity(reserved, move.product_uom)
                if float_compare(total_reserved, move_raw.product_qty, precision_rounding=move.product_id.uom_id.rounding) >= 0:
                    break
            replenish_data['qty_reserved'][move_raw] = total_reserved

        return replenish_data['qty_reserved'][move_raw]

    def _sum_bom_cost(self, current_total, increment):
        if current_total is False and increment is False:
            return False
        return current_total + increment
