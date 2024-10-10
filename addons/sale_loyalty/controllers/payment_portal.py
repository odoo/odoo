# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.fields import Command

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):
    @route('/topup/pay', type='http', methods=['GET', 'POST'], auth='user', website=True, sitemap=False)
    def topup_pay(self, **kwargs):
        product = request.env['product.product'].sudo().browse(int(kwargs['trigger_product_id']))
        partner_id = request.env.user.partner_id
        currency_id = request.env.company.currency_id
        taxes = product.taxes_id.filtered(lambda t: t.company_id == request.env.company)
        tax_data = taxes.compute_all(
            product.lst_price,
            currency=currency_id,
            quantity=1,
            product=product,
            partner=partner_id,
        )
        kwargs['amount'] = tax_data['total_included']
        kwargs['is_topup'] = True
        kwargs['access_token'] = payment_utils.generate_access_token(
            partner_id,
            kwargs['amount'],
            currency_id.id,
        )

        return self.payment_pay(**kwargs)

    @route('/topup/transaction/<int:product_id>', type='jsonrpc', auth='user')
    def topup_transaction(self, product_id, **kwargs):
        partner_id = request.env.user.partner_id.id
        sale_order = request.env['sale.order'].sudo().create({
            'partner_id': partner_id,
            'order_line': [Command.create({
                'product_id': product_id,
                'product_uom_qty': 1,
            })],
        })
        self._validate_transaction_kwargs(kwargs, additional_allowed_keys=('access_token',))
        kwargs.update({
            'partner_id': partner_id,
            'currency_id': request.env.company.currency_id.id,
            'sale_order_id': sale_order.id,
        })
        tx_sudo = self._create_transaction(
            custom_create_values={'sale_order_ids': [Command.set([sale_order.id])]},
            **kwargs,
        )
        tx_sudo.landing_route = sale_order.get_portal_url()
        return tx_sudo._get_processing_values()

    def _get_extra_payment_form_values(self, is_topup=False, trigger_product_id=None, **kwargs):
        res = super()._get_extra_payment_form_values(
            is_topup=is_topup,
            trigger_product_id=trigger_product_id,
            **kwargs
        )

        if is_topup:
            res.update({
                'transaction_route': f'/topup/transaction/{trigger_product_id}'
            })
        return res
