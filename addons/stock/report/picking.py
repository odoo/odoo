# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.report import report_sxw
from openerp.tools.translate import _

class picking(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_internal_picking_src_lines': self.get_internal_picking_src_lines,
            'get_internal_picking_dest_lines': self.get_internal_picking_dest_lines,
            'get_product_desc': self.get_product_desc,
        })
    def get_product_desc(self, move_line):
        desc = move_line.product_id.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc

    def get_internal_picking_src_lines(self, picking):
        res = []
        for line in picking.move_lines:
            if line.state not in ('confirmed', 'done', 'assigned', 'waiting') or line.scrapped:
                continue
            state_label = line.state == 'done' and _('Done') or (line.state == 'confirmed' and _('Waiting Availability') or (line.state == 'assigned' and _('Available') or _('Waiting Availability')))
            row = {
                'state': state_label,
                'description': self.get_product_desc(line),
            }
            if not line.lot_ids:
                row['quantity'] = line.product_uom_qty
                row['lot_id'] = ''
                row['uom'] = line.product_uom.name
                row['location_id'] = line.location_id.name
                row['barcode'] = line.product_id.ean13
                res.append(row)
            else:
                for quant in line.lot_ids:
                    row2 = row.copy()
                    row2['quantity'] = quant.qty
                    row2['uom'] = line.product_id.uom_id.name
                    row2['location_id'] = quant.location_id.name
                    row2['lot_id'] = quant.lot_id and quant.lot_id.name or ''
                    row2['barcode'] = quant.lot_id and quant.lot_id.name or line.product_id.ean13
                    res.append(row2)
        return res

    def get_internal_picking_dest_lines(self, picking):
        res = []
        for line in picking.move_lines:
            row = {'description': self.get_product_desc(line)}
            if not line.putaway_ids:
                row['quantity'] = line.product_uom_qty
                row['uom'] = line.product_uom.name
                row['location_id'] = line.location_dest_id.name
                row['barcode'] = line.product_id.ean13
                row['lot_id'] = ''
                res.append(row)
            else:
                for rec in line.putaway_ids:
                    row2 = row.copy()
                    row2['quantity'] = rec.quantity
                    row2['uom'] = line.product_id.uom_id.name
                    row2['location_id'] = rec.location_id.name
                    row2['lot_id'] = rec.lot_id and rec.lot_id.name or ''
                    row2['barcode'] = rec.lot_id and rec.lot_id.name or line.product_id.ean13
                    res.append(row2)
        return res

report_sxw.report_sxw('report.stock.picking.list', 'stock.picking', 'addons/stock/report/picking.rml', parser=picking)
report_sxw.report_sxw('report.stock.picking.list.internal', 'stock.picking', 'addons/stock/report/picking_internal.rml', parser=picking, header='internal')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
