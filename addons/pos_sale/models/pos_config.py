# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_down_payment_product(self):
        return self.env.ref('pos_sale.default_downpayment_product', raise_if_not_found=False)

    def _get_default_sol_product(self):
        return self.env.ref('pos_sale.default_sol_product', raise_if_not_found=False)

    def _default_sale_order_payment_method(self):
        payment_method = self.env['pos.payment.method'].with_context(active_test=False).search(
            [
                *self.env['pos.payment.method']._check_company_domain(self.env.company),
                ('use_sale_order_payment', '=', True)
            ],
            limit=1,
        )
        if not payment_method:
            payment_method = self.env['pos.payment.method'].create({
                'name': _('Online Paid SO Payment'),
                'company_id': self.env.company.id,
                'use_sale_order_payment': True,
                'active': False,
            })
        return payment_method

    def _default_payment_methods(self):
        """Filter out settle payment method from default payment methods."""
        payment_methods = super()._default_payment_methods()
        return payment_methods.filtered(lambda pm: not pm.use_sale_order_payment)

    crm_team_id = fields.Many2one(
        'crm.team', string="Sales Team", ondelete="set null", index='btree_not_null',
        help="This Point of sale's sales will be related to this Sales Team.")
    down_payment_product_id = fields.Many2one('product.product',
        string="Down Payment Product",
        default=_get_default_down_payment_product,
        help="This product will be used as down payment on a sale order.")
    default_product_id = fields.Many2one(
        'product.product',
        string="Default Product",
        default=_get_default_sol_product,
        help="This product will be used as default product on productless SOLs."
    )
    sale_order_payment_method_id = fields.Many2one(
        'pos.payment.method',
        string='Sale Order Payment Method',
        default=_default_sale_order_payment_method,
        help="Payment method used to settle Sale Orders that were already paid online."
    )

    def _get_special_products(self):
        res = super()._get_special_products()
        return res | self.env['pos.config'].search([]).mapped(
            lambda config: config.down_payment_product_id | config.default_product_id
        )

    @api.model
    def _ensure_default_configurations(self):
        values = {}
        if downpayment_product := self._get_default_down_payment_product():
            values['down_payment_product_id'] = downpayment_product.id
        if default_sol_product := self._get_default_sol_product():
            values['default_product_id'] = default_sol_product.id
        if sale_order_payment_method := self._default_sale_order_payment_method():
            values['sale_order_payment_method_id'] = sale_order_payment_method.id
        if values:
            self.with_context(active_test=False).search([]).write(values)

    def _get_allowed_payment_methods(self):
        return super()._get_allowed_payment_methods() + self.sale_order_payment_method_id
