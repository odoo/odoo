from odoo import models
import pandas as pd
from lxml import etree



class PurchaseOrderReport(models.AbstractModel):
    _name = "report.qweb_report.report_product_stock_inventory_wizard"
    _description = "Purchase order report"

    def _get_report_values(self, docids, data=None):
        # purchase = self.env['purchase.order'].browse(docids)
        product = data['form']['product_ids']
        stock_inventory = self.env['stock.move.line'].search([('product_id', 'in', product)])
        stock_actual = self.env['stock.quant'].search([('product_id', 'in', product),('quantity','>=', 0)])
        purchase_order = self.env['purchase.order.line'].search([('product_id', 'in', product)])
        sale_order = self.env['sale.order.line'].search([('product_id', 'in', product)])
        p_dict = {}

        for i in stock_inventory:
            if i.product_id.name in p_dict:
                p_dict[i.product_id.name]['move'].append(i.move_id.location_dest_id.name)
                p_dict[i.product_id.name]['qty'].append(i.qty_done)
                p_dict[i.product_id.name]['location'].append(i.location_id.name)
                p_dict[i.product_id.name]['istate'].append(i.state)
                p_dict[i.product_id.name]['reference'].append(i.reference)
            else:
                 p_dict[i.product_id.name] = {
                    'move':[i.move_id.name],
                    'qty': [i.qty_done],
                    'location':[i.location_id.name],
                    'istate':[i.state],
                    'reference':[i.reference],
                }

        for i in stock_actual:
            p_dict[i.product_id.name]['quantity'] = i.quantity

        for i in purchase_order:
            if 'purchase_order_name' in p_dict[i.product_id.name].keys():
                p_dict[i.product_id.name]['purchase_order_name'].append(i.order_id.name)
                p_dict[i.product_id.name]['vendor'].append(i.partner_id.name)
                p_dict[i.product_id.name]['order_date'].append(i.order_id.date_order)
                p_dict[i.product_id.name]['pstate'].append(i.state)
                p_dict[i.product_id.name]['price'].append(i.price_unit)
                p_dict[i.product_id.name]['price_total'].append(i.price_total)
                p_dict[i.product_id.name]['product_qty'].append(i.product_uom_qty)
            else:
                p_dict[i.product_id.name]['purchase_order_name'] = [i.order_id.name]
                p_dict[i.product_id.name]['vendor'] = [i.partner_id.name]
                p_dict[i.product_id.name]['order_date'] = [i.order_id.date_order]
                p_dict[i.product_id.name]['pstate'] = [i.state]
                p_dict[i.product_id.name]['price'] = [i.price_unit]
                p_dict[i.product_id.name]['price_total'] = [i.price_total]
                p_dict[i.product_id.name]['product_qty'] = [i.product_uom_qty]

        for i in sale_order:
            if 'sale_order_name' in p_dict[i.product_id.name].keys():
                p_dict[i.product_id.name]['sale_order_name'].append(i.order_id.name)
                p_dict[i.product_id.name]['customer'].append(i.order_id.partner_id.name)
                p_dict[i.product_id.name]['sorder_date'].append(i.order_id.date_order)
                p_dict[i.product_id.name]['sstate'].append(i.state)
                p_dict[i.product_id.name]['sprice'].append(i.price_unit)
                p_dict[i.product_id.name]['sprice_total'].append(i.price_total)
                p_dict[i.product_id.name]['sproduct_qty'].append(i.product_uom_qty)
            else:
                p_dict[i.product_id.name]['sale_order_name'] = [i.order_id.name]
                p_dict[i.product_id.name]['customer'] = [i.order_id.partner_id.name]
                p_dict[i.product_id.name]['sorder_date'] = [i.order_id.date_order]
                p_dict[i.product_id.name]['sstate'] = [i.state]
                p_dict[i.product_id.name]['sprice'] = [i.price_unit]
                p_dict[i.product_id.name]['sprice_total'] = [i.price_total]
                p_dict[i.product_id.name]['sproduct_qty'] = [i.product_uom_qty]

        print(p_dict)
        data['form']['pdata'] = p_dict
        return {
            'doc_model': 'stock.inventory',
            'data': data['form'],
        }
