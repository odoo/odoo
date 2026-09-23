from odoo import api, fields, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale_collect import const


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    custom_mode = fields.Selection(selection_add=[("on_site", "Pay on site")])

    def _get_default_payment_method_codes(self):
        self.check_singleton()
        if self.custom_mode != "on_site":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    @api.model
    def _get_compatible_providers(
        self,
        company_id,
        *args,
        sale_order_id=None,
        website_id=None,
        report=None,
        **kwargs,
    ):
        compatible_providers = super()._get_compatible_providers(
            company_id,
            *args,
            sale_order_id=sale_order_id,
            website_id=website_id,
            report=report,
            **kwargs,
        )
        order = self.env["sale.order"].browse(sale_order_id).exists()

        if order.carrier_id.delivery_type != "in_store" or not any(
            product.type == "consu" for product in order.line_ids.product_id
        ):
            unfiltered_providers = compatible_providers
            compatible_providers = compatible_providers.filtered(
                lambda p: p.code != "custom" or p.custom_mode != "on_site"
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - compatible_providers,
                available=False,
                reason=self.env._("no in-store delivery methods available"),
            )

        return compatible_providers
