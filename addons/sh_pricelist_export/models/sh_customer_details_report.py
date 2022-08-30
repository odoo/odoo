# JUAN PABLO YAÑEZ CHAPITAL

from odoo import api, fields, models


class ReportCustomerPricelistDetails(models.AbstractModel):

    _name = 'report.sh_pricelist_export.sh_customer_pricelist_report'
    _description = 'Customer Pricelist abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):

        active_ids = self.env.context.get('active_ids')
        search_partner = self.env['res.partner'].search(
            [('id', 'in', active_ids)])
        product_dic = {}
        customer_list = []

        if search_partner:
            for partner in search_partner:
                partner_pricelist = partner.property_product_pricelist
                product_list = []
                for product in self.env['product.template'].search([]):
                    price_unit = partner_pricelist._compute_price_rule(
                        [(product, 1.0, partner)], date=fields.Date.today(), uom_id=product.uom_id.id)[product.id][0]
                    discount_amount = 0.0
                    if product.list_price > price_unit:
                        discount_amount = product.list_price - price_unit
                        discount = (100 * (discount_amount))/product.list_price
                    else:
                        discount = 0.0
                    vals = {
                        'name': product.name or False,
                        'default_code': product.default_code or '',
                        'barcode': product.barcode or False,
                        'list_price': product.list_price or False,
                        'discount': float(discount),
                        'price': price_unit or False,
                        'discount_amount': discount_amount
                    }
                    product_list.append(vals)
                product_dic.update({partner: product_list})
                customer_list.append(partner.name)

        print("\n\n\n product_dic", product_dic)
        print("\n\n\n customer_list", customer_list)
        data = {
            'product_dic': product_dic,
            'customer_list': customer_list,
        }
        return data
