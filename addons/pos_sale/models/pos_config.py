# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_default_down_payment_product(self):
        return self.env.ref('pos_sale.default_downpayment_product', raise_if_not_found=False)

    def _get_default_sol_product(self):
        return self.env.ref('pos_sale.default_sol_product', raise_if_not_found=False)

    def _get_sale_order_payment_method(self, company):
        """Return the company's payment method for settling pre-paid sale orders.

        One per company, created on first use. Archived on purpose: cashiers never pick
        it, POS only sets it on the payment lines it creates when settling such an order.
        """
        PosPaymentMethod = self.env['pos.payment.method']
        payment_method = PosPaymentMethod.with_context(active_test=False).search(
            [
                *PosPaymentMethod._check_company_domain(company),
                ('use_sale_order_payment', '=', True)
            ],
            limit=1,
        )
        return payment_method or PosPaymentMethod.create({
            'name': _('Online Paid SO Payment'),
            'company_id': company.id,
            'use_sale_order_payment': True,
            'active': False,
            'type': 'pay_later',
        })

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
        check_company=True,
        help="Payment method used to settle Sale Orders that were already paid online."
    )

    @api.model_create_multi
    def create(self, vals_list):
        configs = super().create(vals_list)
        # Not a field default: the payment method is company specific, while a default
        # can only look at self.env.company, and creating a record from a default
        # would create one every time a pos.config form is opened.
        missing = configs.filtered(lambda config: not config.sale_order_payment_method_id)
        for company, company_configs in missing.grouped('company_id').items():
            company_configs.sale_order_payment_method_id = self._get_sale_order_payment_method(company)
        return configs

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

        configs = self.with_context(active_test=False).search([])
        if values:
            configs.write(values)

        # The settlement payment method is company specific, so each company gets its own.
        for company, company_configs in configs.grouped('company_id').items():
            company_configs.sale_order_payment_method_id = self._get_sale_order_payment_method(company)

    def _get_allowed_payment_methods(self):
        return super()._get_allowed_payment_methods() | self.sale_order_payment_method_id
