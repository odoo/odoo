# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BomStructureReport(models.AbstractModel):
    _name = 'report.mrp.mrp_bom_structure_report'

    @api.model
    def _get_child_vals(self, record, level, qty, uom):
        """Get bom.line values.

        :param record: mrp.bom.line record
        :param level: level of recursion
        :param qty: quantity of the product
        :param uom: unit of measurement of a product
        """
        child = {
            'pname': record.product_id.name_get()[0][1],
            'pcode': record.product_id.default_code,
            'puom': record.product_uom_id,
            'uname': record.product_uom_id.name,
            'level': level,
            'code': record.bom_id.code,
        }
        qty_per_bom = record.bom_id.product_qty
        if uom:
            if uom != record.bom_id.product_uom_id:
                qty = uom._compute_quantity(qty, record.bom_id.product_uom_id)
            child['pqty'] = (record.product_qty * qty) / qty_per_bom
        else:
            # for the first case, the ponderation is right
            child['pqty'] = (record.product_qty * qty)
        return child

    def get_children(self, records, level=0):
        result = []

        def _get_rec(records, level, qty=1.0, uom=False):
            for l in records:
                child = self._get_child_vals(l, level, qty, uom)
                result.append(child)
                if l.child_line_ids:
                    if level < 6:
                        level += 1
                    _get_rec(l.child_line_ids, level, qty=child['pqty'], uom=child['puom'])
                    if level > 0 and level < 6:
                        level -= 1
            return result

        children = _get_rec(records, level)

        return children

    @api.multi
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.bom',
            'docs': self.env['mrp.bom'].browse(docids),
            'get_children': self.get_children,
            'data': data,
        }
