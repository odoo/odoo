# -*- coding: utf-8 -*-

from woocommerce import API
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import config
config['limit_time_real'] = 1000000

class WooCoupon(models.Model):
    _inherit = 'loyalty.program'
    _description = "Woo Coupon"

    woo_id = fields.Char('WooCommerce ID')
    woo_instance_id = fields.Many2one('woo.instance', ondelete='cascade')
    is_exported = fields.Boolean('Synced In Woocommerce', default=False)
    product_id = fields.Many2one('product.product',string="Product")
    product_ids = fields.Many2many('product.product', string="Woo Products")
    fix_product_discount = fields.Float(string="Fixed Amount")
    discount_type = fields.Selection([('percentage','Percentage discount'),('fixed_amount','Fixed cart discount'),('fixed_product','Fixed product discount')])
    rule_minimum_amount = fields.Float(string="Minimum Spend")
    discount_max_amount = fields.Float(string="Maximum Spend")
    discount_specific_product_ids = fields.Many2many('product.product','product_loyalty_rel','product_id','loyalty_program_id',string="Discount Products")
    discount_fixed_amount = fields.Float(string="Discount Fixed Amount")

    def cron_import_coupon(self):
        woo_instance = self.env['woo.instance'].sudo().search([])
        for rec in woo_instance:
            self.import_woo_coupon(rec)

    def cron_export_coupon(self):
        woo_instance = self.env['woo.instance'].sudo().search([])
        for rec in woo_instance:
            self.export_selected_coupon(rec)

    def import_woo_coupon(self, instance_id):
        page = 1
        while page > 0:
            location = instance_id.url
            cons_key = instance_id.client_id
            sec_key = instance_id.client_secret
            version = 'wc/v3'

            wcapi = API(url=location, consumer_key=cons_key, consumer_secret=sec_key, version=version)

            url = "coupons"

            try:
                response = wcapi.get(url, params={'orderby': 'id', 'order': 'asc', 'per_page': 100, 'page': page})
                page += 1
            except Exception as error:
                raise UserError(_("Please check your connection and try again"))

            if response.status_code == 200 and response.content:
                parsed_data = response.json()
                if len(parsed_data) == 0:
                    page = 0
                if parsed_data:
                    for rec in parsed_data:
                        ''' This will avoid duplications of coupon already having woo_id. '''
                        vals = {}

                        discount_type = False
                        if rec.get("discount_type"):
                            if rec.get("discount_type") == 'percent':
                                discount_type = 'percentage'
                            elif rec.get("discount_type") == 'fixed_cart':
                                vals.update({'discount_fixed_amount': rec.get('amount')})
                                discount_type = 'fixed_amount'
                            elif rec.get("discount_type") == 'fixed_product':
                                discount_type = 'fixed_product'
                                vals.update({'fix_product_discount': rec.get('amount')})

                        if discount_type:
                            vals.update({"discount_type": discount_type})

                        vals.update({
                            'woo_id': rec.get('id'),
                            'name': rec.get('code'),
                            'is_exported': True,
                            'woo_instance_id': instance_id.id,
                            'rule_minimum_amount': rec.get('minimum_amount'),
                            'discount_max_amount': rec.get('maximum_amount'),
                        })

                        products = rec.get('product_ids')
                        product_list = []
                        for product in products:
                            odoo_product = self.env['product.product'].sudo().search([('woo_id', '=', product)], limit=1)
                            product_list.append(odoo_product)

                        if discount_type and discount_type == 'fixed_product':
                            vals.update({
                                'product_ids': [(4, product.id, False) for product in product_list if product]
                            })
                        else:
                            vals.update({
                                'discount_specific_product_ids': [(4, product.id, False) for product in product_list if
                                                                  product]
                            })

                        coupon = self.env['loyalty.program'].sudo().search([('woo_id', '=', rec.get('id'))], limit=1)
                        if not coupon:
                            self.sudo().create(vals)
                        else:
                            coupon.sudo().update(vals)
            else:
                page = 0

    def export_selected_coupon(self, instance_id):
        url = instance_id.url
        cons_key = instance_id.client_id
        sec_key = instance_id.client_secret
        version = 'wc/v3'

        wcapi = API(url=url, consumer_key=cons_key, consumer_secret=sec_key, version=version)

        selected_ids = self.env.context.get('active_ids', [])
        selected_records = self.env['loyalty.program'].sudo().browse(selected_ids)

        if selected_records:
            records = selected_records
        else:
            records = self.env['loyalty.program'].sudo().search([('is_exported', '=', False)])

        rec_list = []

        for rec in records:
            if rec.discount_type == 'percentage':
                discount_type = 'percent'
                amount = rec.discount_percentage
            elif rec.discount_type == 'fixed_amount':
                discount_type = 'fixed_cart'
                amount = rec.discount_fixed_amount
            else:
                discount_type = 'fixed_product'
                amount = rec.fix_product_discount

            vals = {
                "code": rec.name,
                "discount_type": discount_type,
                "amount": str(amount),
                "individual_use": True,
                "exclude_sale_items": True,
                "minimum_amount": str(rec.rule_minimum_amount)
            }

            try:
                result = wcapi.post("coupons", vals)
                if result.status_code == 200 or result.status_code == 201:
                    result = result.json()
                    rec.woo_id = result.get('id')
                    rec.woo_instance_id = instance_id
                    rec.is_exported = True
            except Exception as error:
                raise UserError(_("Please check your connection and try again"))

            rec_list.append(vals)


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('fixed_product', 'Fixed Product Discount')], default="percentage",
        help="Percentage - Entered percentage discount will be provided\n" + "Amount - Entered fixed amount discount will be provided")
