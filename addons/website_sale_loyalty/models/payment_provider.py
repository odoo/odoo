from odoo import _, models

from odoo.addons.payment import utils as payment_utils


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _get_compatible_providers(self, *args, sale_order_id=None, report=None, **kwargs):
        providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, report=report, **kwargs
        )
        if not sale_order_id:
            return providers
        sale_order = self.env['sale.order'].browse(sale_order_id)
        if sale_order.coupon_point_ids.filtered(lambda pe: pe.coupon_id.program_id.program_type in ['gift_card', 'ewallet']).coupon_id:
            unfiltered_providers = providers
            providers = providers.filtered(
                lambda p: p.code != 'custom' or p.custom_mode != 'on_site'
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - providers,
                available=False,
                reason=_("incompatible with gift cards and eWallets"),
            )
        return providers
