# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request, route
from odoo.exceptions import ValidationError
from odoo.fields import Command

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):
    @route('/topup/pay', type='http', methods=['GET', 'POST'], auth='user', website=True, sitemap=False)
    def topup_pay(self, **kwargs):
        product = request.env['product.product'].sudo().browse(int(kwargs['trigger_product_id']))
        partner_id = request.env.user.partner_id
        currency = request.env.company.currency_id
        taxes = product.taxes_id.filtered(lambda t: t.company_id == request.env.company)
        tax_data = taxes.compute_all(
            product.lst_price,
            currency=currency,
            quantity=1,
            product=product,
            partner=partner_id,
        )
        kwargs['amount'] = tax_data['total_included']
        kwargs['is_topup'] = True
        kwargs['currency_id'] = currency.id

        return self.payment_pay(**kwargs)

    @route('/topup/transaction/<int:product_id>', type='jsonrpc', auth='user')
    def topup_transaction(self, amount, access_token, currency_id, product_id, **kwargs):
        partner_id = request.env.user.partner_id.id
        amount = self._cast_as_float(amount)
        if not payment_utils.check_access_token(access_token, partner_id, amount, currency_id):
            raise ValidationError(_("The access token is invalid."))

        sale_order = request.env['sale.order'].sudo().create({
            'partner_id': partner_id,
            'require_payment': True,
            'order_line': [Command.create({
                'product_id': product_id,
                'product_uom_qty': 1,
            })],
            'user_id': self.env.ref('base.user_admin').id
        })
        self._validate_transaction_kwargs(kwargs)
        kwargs.update({
            'partner_id': partner_id,
            'currency_id': request.env.company.currency_id.id,
            'sale_order_id': sale_order.id,
        })
        tx_sudo = self._create_transaction(
            amount=amount,
            custom_create_values={'sale_order_ids': [Command.set([sale_order.id])]},
            **kwargs,
        )
        self._update_landing_route(tx_sudo, access_token)
        return tx_sudo._get_processing_values()

    @route('/topup/pay/confirm', type='http', methods=['GET'], auth='user', website=True, sitemap=False)
    def topup_pay_confirmation(self, tx_id=None, access_token=None, **kwargs):
        tx_id = self._cast_as_int(tx_id)
        if not tx_id:
            return request.redirect('/my/home')
        tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id)
        sale_order = tx_sudo.sale_order_ids
        if tx_sudo.state in ['error', 'cancel']:
            sale_order.action_cancel()
            return super().payment_confirm(tx_id, access_token, **kwargs)
        return request.redirect(sale_order.get_portal_url())

    def _get_extra_payment_form_values(self, is_topup=False, trigger_product_id=None, **kwargs):
        res = super()._get_extra_payment_form_values(
            is_topup=is_topup,
            trigger_product_id=trigger_product_id,
            **kwargs
        )

        if is_topup:
            res.update({
                'transaction_route': f'/topup/transaction/{trigger_product_id}',
                'landing_route': '/topup/pay/confirm/',
            })
        return res
