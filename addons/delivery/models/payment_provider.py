# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.delivery import const
from odoo.addons.payment import utils as payment_utils


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    custom_mode = fields.Selection(selection_add=[("cash_on_delivery", "Cash On Delivery")])

    def _get_code(self):
        """Override to allow the post processing of transactions to create payments."""
        if self.code == "custom" and self.custom_mode == "cash_on_delivery":
            return "cash_on_delivery"
        return super()._get_code()

    # === CRUD METHODS === #

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        self.ensure_one()
        if self.custom_mode != "cash_on_delivery":
            return super()._get_default_payment_method_codes()
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if self.custom_mode != "cash_on_delivery":
            return vals_list

        for vals in vals_list:
            vals["is_live"] = True
        return vals_list

    # === BUSINESS METHODS === #

    @api.model
    def _find_available_providers(
        self, company_id, partner_id, amount, *args, sale_order_id=None, report=None, **kwargs
    ):
        """Override of payment to exclude COD providers if the delivery method doesn't match, or if
        the amount is not greater than or equal to the order remaining balance.

        :param int company_id: The company to which providers must belong, as a `res.company` id.
        :param int partner_id: The partner making the payment, as a `res.partner` id.
        :param float amount: The amount to pay. `0` for validation transactions.
        :param int sale_order_id: The sales order to be paid, if any, as a `sale.order` id.
        :param dict report: The availability report.
        :return: The available providers.
        :rtype: payment.provider
        """
        available_providers = super()._find_available_providers(
            company_id,
            partner_id,
            amount,
            *args,
            sale_order_id=sale_order_id,
            report=report,
            **kwargs,
        )

        reason = None
        sale_order = self.env["sale.order"].browse(sale_order_id).exists()
        currency = sale_order.currency_id

        if not sale_order:
            reason = self.env._("Cash on delivery is only allowed if a sales order exists")
        elif not sale_order.carrier_id.allow_cash_on_delivery:
            reason = self.env._("Cash on delivery not allowed by selected delivery method")
        elif currency.compare_amounts(amount, sale_order.amount_remaining) < 0:
            reason = self.env._(
                "Cash on delivery not allowed to pay less than the order remaining balance"
            )

        if reason:
            unfiltered_providers = available_providers
            available_providers = available_providers.filtered(
                lambda p: p.custom_mode != "cash_on_delivery"
            )
            payment_utils.add_to_report(
                report, unfiltered_providers - available_providers, available=False, reason=reason
            )

        return available_providers
