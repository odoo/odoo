# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.fields import Command

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers import portal as payment_portal


class PaymentPortal(payment_portal.PaymentPortal):
    @route('/topup/pay', type='http', methods=['GET', 'POST'], auth='public', website=True, sitemap=False)
    def topup_pay(self, **kwargs):
        _, total_price = kwargs['trigger_product'].split(',')

        kwargs['amount'] = float(total_price)
        kwargs['is_topup'] = True
        kwargs['access_token'] = payment_utils.generate_access_token(
            request.env.user.partner_id.id,
            kwargs['amount'],
            request.env.company.currency_id.id,
        )

        return self.payment_pay(**kwargs)

    @route('/topup/transaction/<int:product_id>', type='json', auth='public')
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

    def _get_extra_payment_form_values(self, **kwargs):
        res = super()._get_extra_payment_form_values(**kwargs)

        if kwargs.get('is_topup'):
            product_id, _ = kwargs['trigger_product'].split(',')
            res.update({
                'transaction_route': f'/topup/transaction/{product_id}'
            })
        return res
