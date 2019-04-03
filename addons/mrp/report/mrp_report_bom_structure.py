# -*- coding: utf-8 -*-

import json

from odoo import api, models, _
from odoo.tools import float_round


class ReportBomStructure(models.AbstractModel):
    _name = 'report.mrp.report_bom_structure'
    _description = 'BOM Structure Report'

    def _get_report_xslx_values(self, bom_id, quantity, variant, report_name='all'):
        data = self._get_report_values([bom_id], {'report_name': report_name, 'quantity': quantity, 'variant': variant})
        header = self.get_header(report_name)
        columns = self.get_column_key(report_name)
        bom_report_name = self._get_report_name()
        return data, header, columns, bom_report_name

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        for bom_id in docids:
            bom = self.env['mrp.bom'].browse(bom_id)
            report_name = data.get('report_name') or 'all'
            variant = int(data.get('variant'))
            candidates = variant and self.env['product.product'].browse(variant) or bom.product_tmpl_id.product_variant_ids
            for product_variant_id in candidates:
                if data and data.get('childs'):
                    doc = self._get_pdf_line(bom_id, product_id=product_variant_id, qty=float(data.get('quantity')), child_bom_ids=json.loads(data.get('childs')), report_name=report_name, report_type='pdf')
                else:
                    doc = self._get_pdf_line(bom_id, product_id=product_variant_id, qty=float(data.get('quantity')), report_name=report_name, report_type='pdf')
                doc['report_type'] = 'pdf'
                doc['report_name'] = report_name
                docs.append(doc)
            if not candidates:
                if data and data.get('childs'):
                    doc = self._get_pdf_line(bom_id, qty=float(data.get('quantity')), child_bom_ids=json.loads(data.get('childs')),  report_name=report_name, report_type='pdf')
                else:
                    doc = self._get_pdf_line(bom_id, qty=float(data.get('quantity')), report_name=report_name, report_type='pdf')
                doc['report_type'] = 'pdf'
                doc['report_name'] = report_name
                docs.append(doc)
            doc['header'] = self.get_header(report_name)
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.bom',
            'docs': docs,
        }

    @api.model
    def get_html(self, bom_id=False, searchQty=1, searchVariant=False, report_name='all', report_type='html'):
        searchVariant = self.env['product.product'].browse(searchVariant)
        self._get_report_values([bom_id], {'report_name': report_name, 'quantity': searchQty, 'variant': searchVariant})
        res = self._get_report_data(bom_id=bom_id, searchQty=searchQty, report_name=False, searchVariant=searchVariant)
        res['lines']['report_type'] = report_type
        res['lines']['report_name'] = report_name
        res['lines']['has_attachments'] = res['lines']['attachments'] or any(component['attachments'] for component in res['lines']['components'])
        res['lines']['header'] = self.get_header(report_name)
        res['lines'] = self.env.ref('mrp.report_mrp_bom').render({'data': res['lines']})
        return res

    @api.model
    def get_bom(self, bom_id=False, product_id=False, line_qty=False, line_id=False, level=False, report_name=False):
        lines = self._get_bom(bom_id=bom_id, product=product_id, line_qty=line_qty, line_id=line_id, level=level, report_name=report_name)
        return self.env.ref('mrp.report_mrp_bom_line').render({'data': lines})

    @api.model
    def get_operations(self, bom_id=False, qty=0, level=0):
        bom = self.env['mrp.bom'].browse(bom_id)
        lines = self._get_operation_line(bom.routing_id, float_round(qty / bom.product_qty, precision_rounding=1, rounding_method='UP'), level)
        values = {
            'bom_id': bom_id,
            'currency': self.env.user.company_id.currency_id,
            'operations': lines,
            'report_name': 'all',
        }
        return self.env.ref('mrp.report_mrp_operation_line').render({'data': values})

    @api.model
    def _get_report_data(self, bom_id, searchQty=0, searchVariant=False, report_name=False):
        lines = {}
        bom = self.env['mrp.bom'].browse(bom_id)
        bom_quantity = searchQty or bom.product_qty
        bom_product_variants = {}
        bom_uom_name = ''

        if bom:
            bom_uom_name = bom.product_uom_id.name

        # Get variants used for search
        if not bom.product_id:
            for variant in bom.product_tmpl_id.product_variant_ids:
                bom_product_variants[variant.id] = variant.display_name
        lines = self._get_bom(bom_id=bom_id, product=searchVariant, line_qty=bom_quantity, level=1)
        return {
            'lines': lines,
            'variants': bom_product_variants,
            'bom_uom_name': bom_uom_name,
            'quantity': bom_quantity,
            'is_variant_applied': self.env.user.user_has_groups('product.group_product_variant') and len(bom_product_variants) > 1,
            'is_uom_applied': self.env.user.user_has_groups('uom.group_uom')
        }

    def _get_bom(self, bom_id=False, product=False, line_qty=False, line_id=False, level=False, report_name='all'):
        bom = self.env['mrp.bom'].browse(bom_id)
        bom_quantity = line_qty
        if line_id:
            current_line = self.env['mrp.bom.line'].browse(int(line_id))
            bom_quantity = current_line.product_uom_id._compute_quantity(line_qty, bom.product_uom_id)
        # Display bom components for current selected product variant
        if not product:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id

        if product:
            product_id = int(product)
            product = self.env['product.product'].browse(product_id)
            attachments = self.env['mrp.document'].search(['|', '&', ('res_model', '=', 'product.product'),
                                                          ('res_id', '=', product.id), '&', ('res_model', '=', 'product.template'),
                                                          ('res_id', '=', product.product_tmpl_id.id)])
        else:
            product = bom.product_tmpl_id
            attachments = self.env['mrp.document'].search([('res_model', '=', 'product.template'), ('res_id', '=', product.id)])
        operations = self._get_operation_line(bom.routing_id, float_round(bom_quantity / bom.product_qty, precision_rounding=1, rounding_method='UP'), 0)
        lines = {
            'bom': bom,
            'quantity': bom_quantity,
            'name': product.display_name,
            'currency': self.env.user.company_id.currency_id,
            'product': product,
            'code': bom and bom.display_name or '',
            'prod_cost': product.uom_id._compute_price(product.standard_price, bom.product_uom_id) * bom_quantity,
            'total': sum([op['total'] for op in operations]),
            'level': level or 0,
            'operations': operations,
            'operations_cost': sum([op['total'] for op in operations]),
            'attachments': attachments,
            'report_name': report_name,
            'operations_time': sum([op['duration_expected'] for op in operations])
        }
        components, total = self._get_bom_lines(bom, bom_quantity, product, line_id, level)
        lines['components'] = components
        lines['total'] += total
        return lines

    def _get_bom_lines(self, bom, bom_quantity, product, line_id, level):
        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * line.product_qty
            if line._skip_bom_line(product):
                continue
            price = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * line_quantity
            if line.child_bom_id:
                factor = line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id) / line.child_bom_id.product_qty
                sub_total = self._get_price(line.child_bom_id, factor, line.product_id)
            else:
                sub_total = price
            sub_total = self.env.user.company_id.currency_id.round(sub_total)
            components.append({
                'prod_id': line.product_id.id,
                'name': line.product_id.display_name,
                'code': line.child_bom_id and line.child_bom_id.display_name or '',
                'quantity': line_quantity,
                'prod_uom': line.product_uom_id.name,
                'prod_cost': self.env.user.company_id.currency_id.round(price),
                'parent_id': bom.id,
                'line_id': line.id,
                'level': level or 0,
                'total': sub_total,
                'child_bom': line.child_bom_id.id,
                'phantom_bom': line.child_bom_id and line.child_bom_id.type == 'phantom' or False,
                'attachments': self.env['mrp.document'].search(['|', '&',
                    ('res_model', '=', 'product.product'), ('res_id', '=', line.product_id.id), '&', ('res_model', '=', 'product.template'), ('res_id', '=', line.product_id.product_tmpl_id.id)]),
            })
            total += sub_total
        return components, total

    def _get_operation_line(self, routing, qty, level):
        operations = []
        total = 0.0
        for operation in routing.operation_ids:
            operation_cycle = float_round(qty / operation.workcenter_id.capacity, precision_rounding=1, rounding_method='UP')
            duration_expected = operation_cycle * operation.time_cycle + operation.workcenter_id.time_stop + operation.workcenter_id.time_start
            total = ((duration_expected / 60.0) * operation.workcenter_id.costs_hour)
            operations.append({
                'level': level or 0,
                'operation': operation,
                'name': operation.name + ' - ' + operation.workcenter_id.name,
                'duration_expected': duration_expected,
                'total': self.env.user.company_id.currency_id.round(total),
            })
        return operations

    def _get_price(self, bom, factor, product):
        price = 0
        if bom.routing_id:
            # routing are defined on a BoM and don't have a concept of quantity.
            # It means that the operation time are defined for the quantity on
            # the BoM (the user produces a batch of products). E.g the user
            # product a batch of 10 units with a 5 minutes operation, the time
            # will be the 5 for a quantity between 1-10, then doubled for
            # 11-20,...
            operation_cycle = float_round(factor, precision_rounding=1, rounding_method='UP')
            operations = self._get_operation_line(bom.routing_id, operation_cycle, 0)
            price += sum([op['total'] for op in operations])

        for line in bom.bom_line_ids:
            if line._skip_bom_line(product):
                continue
            if line.child_bom_id:
                qty = line.product_uom_id._compute_quantity(line.product_qty * factor, line.child_bom_id.product_uom_id)
                sub_price = self._get_price(line.child_bom_id, qty, line.product_id)
                price += sub_price
            else:
                quantity = line.product_qty * factor
                not_rounded_price = line.product_id.uom_id._compute_price(line.product_id.standard_price, line.product_uom_id) * quantity
                price += self.env.user.company_id.currency_id.round(not_rounded_price)
        return price

    def _get_pdf_line(self, bom_id, product_id=False, qty=1, child_bom_ids=[], unfolded=False, report_name='all', report_type='pdf'):
        data = self._get_bom(bom_id=bom_id, product=product_id, line_qty=qty)
        bom = self.env['mrp.bom'].browse(bom_id)
        product = product_id or bom.product_id or bom.product_tmpl_id.product_variant_id
        pdf_lines = self.get_sub_lines(bom, product, qty, False, 1, child_bom_ids, unfolded, report_name, report_type)
        data['components'] = []
        data['lines'] = pdf_lines
        return data

    def get_sub_lines(self, bom, product_id, line_qty, line_id, level, child_bom_ids=[], unfolded=False, report_name='all', report_type='pdf'):
        data = self._get_bom(bom_id=bom.id, product=product_id, line_qty=line_qty, line_id=line_id, level=level)
        bom_lines = data['components']
        lines = []
        bom_key = self.get_column_key_xlsx(report_name)
        for bom_line in bom_lines:
            dict_data = {}
            for x in range(0, len(bom_key)):
                dict_data.update({bom_key[x]: bom_line.get(bom_key[x])})
            lines.append(dict_data)
            if bom_line['child_bom'] and (unfolded or bom_line['child_bom'] in child_bom_ids):
                line = self.env['mrp.bom.line'].browse(bom_line['line_id'])
                lines += (self.get_sub_lines(line.child_bom_id, line.product_id, bom_line['quantity'], line, level + 1, child_bom_ids, unfolded, report_name, report_type))
        if report_name != "bom_structure":
            if data['operations']:
                lines.append({
                    'name': _('Operations'),
                    'type': 'operation',
                    'quantity': data['operations_time'],
                    'uom': _('minutes'),
                    'total': data['operations_cost'],
                    'level': level,
                })
                for operation in data['operations']:
                    if unfolded or 'operation-' + str(bom.id) in child_bom_ids:
                        lines.append({
                            'name': operation['name'],
                            'type': 'operation',
                            'quantity': operation['duration_expected'],
                            'uom': _('minutes'),
                            'total': operation['total'],
                            'level': level + 1,
                        })
        return lines

    #TO BE OVERWRITTEN
    def _get_report_name(self):
        return _('General Report')

    def get_header(self, report_name):
        data = []
        if report_name in ['all' or 'undefined']:
            data += [
                {'name': 'Product'},
                {'name': 'BoM'},
                {'name': 'Quantity'},
                {'name': 'Product Cost'},
                {'name': 'BoM Cost'}
            ]
        elif report_name == 'bom_structure':
            data += [
                {'name': 'Product'},
                {'name': 'BoM'},
                {'name': 'Quantity'},
                {'name': 'Product Cost'}
            ]
        elif report_name == 'bom_cost':
            data += [
                {'name': 'Product'},
                {'name': 'BoM'},
                {'name': 'Quantity'},
                {'name': 'BoM Cost'}
            ]
        return data

    def get_column_key_xlsx(self, report_name):
        data = ['name', 'quantity', 'prod_uom', 'prod_cost', 'total', 'level', 'code', 'type']
        return data

    def get_column_key(self, report_name):
        if(report_name == "bom_structure"):
            data = ['name', 'code', 'quantity', 'prod_cost']
        elif(report_name == "bom_cost"):
            data = ['name', 'code', 'quantity', 'total']
        else:
            data = ['name', 'code', 'quantity', 'prod_cost', 'total']
        return data
