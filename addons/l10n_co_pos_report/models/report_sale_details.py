# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.osv.expression import AND


class PosOrder(models.AbstractModel):
    _name = 'report.l10n_co_pos_report.report_saledetails'
    _inherit = 'report.point_of_sale.report_saledetails'
    _description = 'Point of Sale Details'

    @api.model
    def prepare_sale_details(self, domain, date_start, date_stop, config_ids, session_ids, include_products):
        user_currency = self.env.company.currency_id
        report_data = []
        for config_id in config_ids:
            new_domain = AND([domain.copy(), [('config_id', '=', config_id)]])
            orders = self.env['pos.order'].search(new_domain)
            total = 0.0
            products_sold = {}
            taxes = {}
            for order in orders:
                if user_currency != order.pricelist_id.currency_id:
                    total += order.pricelist_id.currency_id._convert(
                        order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
                else:
                    total += order.amount_total
                currency = order.session_id.currency_id

                for line in order.lines:
                    if include_products:
                        key = (line.product_id, line.price_unit, line.discount)
                        products_sold.setdefault(key, 0.0)
                        products_sold[key] += line.qty

                    if line.tax_ids_after_fiscal_position:
                        line_taxes = line.tax_ids_after_fiscal_position.compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                        for tax in line_taxes['taxes']:
                            taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount':0.0, 'base_amount':0.0})
                            taxes[tax['id']]['tax_amount'] += tax['amount']
                            taxes[tax['id']]['base_amount'] += tax['base']
                    else:
                        taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount':0.0, 'base_amount':0.0})
                        taxes[0]['base_amount'] += line.price_subtotal_incl

            payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
            if payment_ids:
                self.env.cr.execute("""
                    SELECT method.name, sum(amount) total,count(DISTINCT payment.pos_order_id)
                    FROM pos_payment AS payment,
                         pos_payment_method AS method
                    WHERE payment.payment_method_id = method.id
                        AND payment.id IN %s
                    GROUP BY method.name
                """, (tuple(payment_ids),))
                payments = self.env.cr.dictfetchall()
            else:
                payments = []
            data = {
                'pos_config': orders.mapped('config_id'),
                'include_products': include_products,
                'currency_precision': user_currency.decimal_places,
                'first_ref': orders and orders[-1].name,
                'last_ref': orders and orders[0].name,
                'total_paid': user_currency.round(total),
                'payments': payments,
                'total_payment_count': sum(payment.get('count') for payment in payments),
                'company_name': self.env.company.name,
                'taxes': list(taxes.values()),
                'products': sorted([{
                    'product_id': product.id,
                    'product_name': product.name,
                    'code': product.default_code,
                    'quantity': qty,
                    'price_unit': price_unit,
                    'discount': discount,
                    'uom': product.uom_id.name
                } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
            }
            report_data.append(data)
        return {'sale_details': report_data}
