# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import models, fields, api, _
from datetime import datetime, date
from collections import defaultdict, OrderedDict
from dateutil.relativedelta import relativedelta
import math
import xlwt


class ReportSlowMovingInv(models.AbstractModel):
    _name = 'report.flexipharmacy.slow_moving_inv_report_pdf'
    _description = "Report Slow Move Inventory Template"

    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['ir.actions.report']
        report = report_obj._get_report_from_name('flexipharmacy.slow_moving_inv_report_pdf')
        docargs = {
            'doc_ids': self.env['wizard.slow.moving.inventory'].browse(docids[0]),
            'doc_model': report.model,
            'docs': self,
            'summary_data': self.summary_data
        }
        return docargs

    def summary_data(self, obj):
        warehouse_obj = self.env['stock.warehouse']
        if not obj.categ_ids:
            category = [prod_cat_id.id for prod_cat_id in self.env['product.category'].search([])]
        else:
            for category in obj.categ_ids:
                category = self.env['product.category'].search([('complete_name', 'like', category.name)]).ids
        if not obj.warehouse_ids:
            ware_ids = [warehouse_id.id for warehouse_id in warehouse_obj.search([])]
            pos_warehouse_ids = self.env['stock.picking.type'].search(
                [('warehouse_id', 'in', [warehouse_id.id for warehouse_id in warehouse_obj.search([])])]).ids
        else:
            ware_ids = [warehouse_id.id for warehouse_id in obj.warehouse_ids]
            pos_warehouse_ids = self.env['stock.picking.type'].search(
                [('warehouse_id', 'in', [warehouse_id.id for warehouse_id in obj.warehouse_ids])]).ids
        start_date = datetime.now().date()
        end_date = datetime.now().date() - relativedelta(months=obj.avg_month)
        # For Sale Order Query
        slow_inv_sql_sale = """SELECT pp.id as product_id,pt.name as p_name,pt.default_code,pp.default_code as code, 
                                sum(sol.product_uom_qty) as qty,
                                    pc.name as categ_id,pt.uom_id,
                                    avg(sol.price_unit) as cost,so.warehouse_id,
                                    sum(sol.price_unit * sol.product_uom_qty) as value
                                    from sale_order_line sol,sale_order so,
                                    product_template pt,product_product pp,
                                    product_category pc,stock_picking sp
                                    where
                                    sol.order_id = so.id
                                    AND sp.group_id = so.procurement_group_id
                                    AND sol.product_id = pp.id
                                    AND pp.product_tmpl_id = pt.id
                                    AND pt.categ_id = pc.id
                                    AND pc.id in %s
                                    AND so.warehouse_id in %s
                                    AND so.date_order <= '%s'
                                    AND so.date_order >= '%s'
                                    AND sp.state = 'done'
                                    group by pp.id,pt.name,pt.default_code,pc.id,so.warehouse_id,pt.uom_id
                                     order by pt.default_code""" % (" (%s) " % ','.join(map(str, category)),
                                                                    " (%s) " % ','.join(map(str, ware_ids)),
                                                                    str(start_date) + " 23:59:59",
                                                                    str(end_date) + " 00:00:00")
        self._cr.execute(slow_inv_sql_sale)
        slow_move_result_sale = self._cr.dictfetchall()
        categ_dict = defaultdict(list)
        for res in slow_move_result_sale:
            warehouse_id = self.env['stock.warehouse'].browse(res.get('warehouse_id'))
            avg_qty = res.get('qty') / obj.avg_month
            res.update({'warehouses_name': warehouse_id.name,
                        'avg_qty': math.ceil(avg_qty)})
            categ_dict[res.get('categ_id')].append(res)

        lst_final_move_inv = []
        lst_final_move_inv_sale = []
        final_dict = OrderedDict(sorted(categ_dict.items(), key=lambda t: t[0]))
        for res_sale, val_sale in final_dict.items():
            for r in val_sale:
                on_hand = 0
                cost_price = 0
                value = 0
                product_id = self.env['product.product'].browse(r.get('product_id'))
                current_on_hand = self.env['stock.quant'].search([('product_id', '=', r.get('product_id')),
                                                                  ('location_id.usage', '=', 'internal'),
                                                                  ])
                for quant in current_on_hand:
                    on_hand += quant.available_quantity
                    cost_price += product_id.standard_price
                    value += quant.value
                if r['avg_qty']:
                    compare_qty = on_hand / r['avg_qty']
                else:
                    compare_qty = on_hand
                if on_hand and obj.warehouse_ids:
                    final_cost_price = cost_price / len(current_on_hand)
                elif on_hand and not obj.warehouse_ids:
                    final_cost_price = value / on_hand
                else:
                    final_cost_price = 0
                r.update({'compare_qty': math.ceil(compare_qty)})
                uom_id = self.env['uom.uom'].search([('id', '=', r.get('uom_id'))])
                if math.ceil(compare_qty) >= obj.avg_on_hand_month:
                    data_dic_slow_inv = {
                        'default_code': r.get('default_code') or r.get('code'),
                        'p_name': r.get('p_name'),
                        'on_hand': "%.2f" % (on_hand),
                        'final_cost_price': "%.2f" % (final_cost_price),
                        'value': "%.2f" % (value),
                        'compare_qty': math.ceil(compare_qty),
                        'avg_qty': r.get('avg_qty'),
                        'uom_id': uom_id.name,
                    }
                    lst_final_move_inv_sale.append(data_dic_slow_inv)
        # For POS Order Query
        slow_inv_pos = """SELECT pp.id as product, pt.name as p_name, pt.default_code, pc.name as categ_id, pt.uom_id, avg(
                        pol.price_unit) as cost, sum(pol.qty) as qty,sum(pol.price_unit * pol.qty) as value, sp.picking_type_id as warehouse
                        from pos_order_line pol, pos_order pos, product_template pt, product_product pp,
                        product_category pc, stock_picking sp where pol.order_id = pos.id 
                        AND pol.product_id = pp.id
                        AND pp.product_tmpl_id = pt.id
                        AND pt.categ_id = pc.id
                        AND pc.id in %s
                        AND sp.picking_type_id in %s
                        AND pos.date_order <= '%s'
                        AND pos.date_order >= '%s'
                        AND sp.state = 'done'
                        group by pp.id, pt.name, warehouse, pt.default_code, 
                        pc.id, pt.uom_id""" % (" (%s) " % ','.join(map(str, category)),
                                               " (%s) " % ','.join(map(str, pos_warehouse_ids)),
                                               str(start_date) + " 23:59:59",
                                               str(end_date) + " 00:00:00")
        self._cr.execute(slow_inv_pos)
        slow_move_result_pos = self._cr.dictfetchall()
        categ_dict_pos = defaultdict(list)
        for res in slow_move_result_pos:
            picking_type_id = self.env['stock.picking.type'].browse(res.get('warehouse'))
            avg_qty = res.get('qty') / obj.avg_month
            res.update({'warehouses_name': picking_type_id.warehouse_id.name,
                        'avg_qty': math.ceil(avg_qty)})
            categ_dict_pos[res.get('categ_id')].append(res)
        lst_final_move_inv_pos = []
        final_dict_pos = OrderedDict(sorted(categ_dict_pos.items(), key=lambda t: t[0]))
        for res_pos, val_pos in final_dict_pos.items():
            for r in val_pos:
                on_hand = 0
                cost_price = 0
                value = 0
                product_id = self.env['product.product'].browse(r.get('product_id'))
                current_on_hand = self.env['stock.quant'].search([('product_id', '=', r.get('product_id')),
                                                                  ('location_id.usage', '=', 'internal'),
                                                                  ])
                for quant in current_on_hand:
                    on_hand += quant.available_quantity
                    cost_price += product_id.standard_price
                    value += quant.value
                if r['avg_qty']:
                    compare_qty = on_hand / r['avg_qty']
                else:
                    compare_qty = on_hand
                if on_hand and obj.warehouse_ids:
                    final_cost_price = cost_price / len(current_on_hand)
                elif on_hand and not obj.warehouse_ids:
                    final_cost_price = value / on_hand
                else:
                    final_cost_price = 0
                r.update({'compare_qty': math.ceil(compare_qty)})
                uom_id = self.env['uom.uom'].search([('id', '=', r.get('uom_id'))])
                if math.ceil(compare_qty) >= obj.avg_on_hand_month:
                    data_dic_slow_inv_pos = {
                        'default_code': r.get('default_code') or r.get('code'),
                        'p_name': r.get('p_name'),
                        'on_hand': "%.2f" % (on_hand),
                        'final_cost_price': "%.2f" % (final_cost_price),
                        'value': "%.2f" % (value),
                        'compare_qty': math.ceil(compare_qty),
                        'avg_qty': r.get('avg_qty'),
                        'uom_id': uom_id.name,
                    }
                    lst_final_move_inv_pos.append(data_dic_slow_inv_pos)
        if lst_final_move_inv_pos and lst_final_move_inv_sale:
            lst_final_move_inv_sale.extend(lst_final_move_inv_pos)
            for myDict in lst_final_move_inv_sale:
                if myDict not in lst_final_move_inv:
                    lst_final_move_inv.append(myDict)
            return lst_final_move_inv
        elif lst_final_move_inv_pos:
            return lst_final_move_inv_pos
        elif lst_final_move_inv_sale:
            return lst_final_move_inv_sale

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
