from ..marketplace_apis.cart import CartAPI
from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    marketplace_product = fields.Many2one('aumet.marketplace_product', string='Marketplace Product', required=False)
    is_marketplace_item = fields.Boolean(string="Is from marketplace", compute="compute_referenced", store=False)
    payment_method = fields.Many2one("aumet.payment_method", string="payment method")

    price_unit = fields.Float(
        'Unit Price', compute='_compute_standard_price', store=False)

    @api.depends('marketplace_product')
    def compute_referenced(self):
        self.is_marketplace_item = True if self.marketplace_product else False

    @api.onchange('marketplace_product')
    def onchange_marketplace_product(self):
        if self.marketplace_product:
            mpapi_response = CartAPI.get_product_details(self.env.user.marketplace_token,
                                                         self.marketplace_product[0].marketplace_id)
            if mpapi_response["data"]["data"]["payment_methods"]:

                return {
                    'domain':
                        {'payment_method': [
                            ('id',
                             'in',
                             [i["paymentMethodId"] for i in mpapi_response["data"]["data"]["payment_methods"]])
                        ]
                        }
                }
            else:
                return

    @api.model
    def fields_get(self, fields=None, attributes=None):
        result = super(ProductTemplate, self).fields_get(fields, attributes)

        payment_method_field = super(ProductTemplate, self).fields_get("payment_method", attributes)

        domains = self.onchange_marketplace_product()

        if domains:
            payment_method_field["payment_method"]["domain"] = domains["domain"]["payment_method"]
            result["payment_method"] = payment_method_field

        return result
