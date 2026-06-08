# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.website_sale import const


class WebsiteCheckoutStep(models.Model):
    _name = "website.checkout.step"
    _description = "Website Checkout Step"
    _inherit = ["website.published.multi.mixin"]

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer()
    step_href = fields.Char(string="Href", required=True)
    main_button_label = fields.Char(translate=True)
    back_button_label = fields.Char(translate=True)
    website_id = fields.Many2one("website", ondelete="cascade")
    show_in_breadcrumb = fields.Boolean(default=True)

    @api.model
    def _get_step_by_href(self, href, website, *, additional_domain=None):
        domain = Domain([("step_href", "=", href), ("website_id", "=", website.id)])
        if additional_domain is not None:
            domain &= additional_domain
        return self.search(domain, limit=1)

    def _get_next_steps(self, *, additional_domain=None, limit: int | None = None):
        """Get the next steps in the checkout flow based on the sequence."""
        self.ensure_one()
        next_step_domain = Domain([
            ("sequence", ">", self.sequence),
            ("website_id", "=", self.website_id.id),
        ])
        if additional_domain is not None:
            next_step_domain &= additional_domain
        return self.search(next_step_domain, order="sequence", limit=limit)

    def _get_previous_steps(self, *, additional_domain=None, limit: int | None = None):
        """Get the previous steps in the checkout flow based on the sequence."""
        self.ensure_one()
        previous_step_domain = Domain([
            ("sequence", "<", self.sequence),
            ("website_id", "=", self.website_id.id),
        ])
        if additional_domain is not None:
            previous_step_domain &= additional_domain
        return self.search(previous_step_domain, order="sequence DESC", limit=limit)

    @api.model
    @api.private
    def validate_checkout_progress(self, step_href, order_sudo, **kwargs):
        """Check whether all checkout steps preceding `step_href` are valid and complete, and
        return the incomplete page otherwise.

        :param str step_href: Href of the current checkout step
        :param sale.order order_sudo: The current cart, sudoed.
        :param dict kwargs: Extra arguments forwarded to each step validation methods.
        :return: The incomplete or invalid step href if any; otherwise, None.
        :rtype: str | None
        """
        website = kwargs.get("website") or self.env.website
        kwargs.setdefault("website", website)

        current_step_sudo = self.sudo()._get_step_by_href(step_href, website)
        previous_steps_sudo = current_step_sudo._get_previous_steps()

        for previous_step_sudo in previous_steps_sudo.sorted("sequence"):
            if redirect := previous_step_sudo._validate_completion(order_sudo, **kwargs):
                return redirect

    def _validate_completion(self, order_sudo, **kwargs):
        """Route validation to the current step method.

        Note: `self.ensure_one()`

        :param sale.order order_sudo: The current cart, sudoed.
        :param dict kwargs: Additional arguments forwarded to all validation methods.
        :return: The incomplete or invalid step href if any; otherwise, None.
        :rtype: str | None
        """
        self.ensure_one()
        match self.step_href:
            case "/shop/cart":
                return self._check_shop_cart_completion(order_sudo, **kwargs)
            case "/shop/address":
                return self._check_shop_address_completion(order_sudo, **kwargs)
            case "/shop/checkout":
                return self._check_shop_checkout_completion(order_sudo, **kwargs)
            case "/shop/payment":
                return self._check_shop_payment_completion(order_sudo, **kwargs)

    @api.model
    def _check_shop_cart_completion(self, order_sudo, **kwargs):
        """Check whether the `/shop/cart` step is valid and complete, and return the incomplete page
        otherwise.

        :param sale.order order_sudo: The current cart, sudoed.
        :param dict kwargs: Additional arguments for overrides.
        :return: The incomplete or invalid step href if any; otherwise, None.
        :rtype: str | None
        """
        if not order_sudo:
            return const.SHOP_PATH

        # Check that public orders are allowed.
        website = kwargs.get("website") or self.env.website
        if self.env.user._is_public() and website.account_on_checkout == "mandatory":
            return "/web/login?redirect=/shop/checkout"

        if not order_sudo._is_cart_ready_for_checkout():
            return "/shop/cart"

    @api.model
    def _check_shop_address_completion(self, order_sudo, **_kwargs):
        """Check whether the `/shop/address` step is valid and complete, and return the incomplete
        page otherwise.

        :param sale.order order_sudo: The current cart, sudoed.
        :param dict kwargs: Additional arguments for overrides.
        :return: The incomplete or invalid step href if any; otherwise, None.
        :rtype: str | None
        """
        # Check that an address has been added.
        if order_sudo._is_anonymous_cart():
            return "/shop/address"

        # Check that the delivery address is complete.
        delivery_partner_sudo = order_sudo.partner_shipping_id
        if (
            order_sudo._has_deliverable_products()
            and delivery_partner_sudo._can_be_edited_by_current_customer(order_sudo=order_sudo)
            and not delivery_partner_sudo._check_delivery_address(order_sudo=order_sudo)
        ):
            order_sudo._add_warning_alert(
                self.env._(
                    "Your delivery address appears to be incomplete or invalid."
                    " Please ensure all required fields are correctly filled and try again."
                )
            )
            return f"/shop/address?partner_id={delivery_partner_sudo.id}&address_type=delivery"

        # Check that the billing address is complete.
        invoice_partner_sudo = order_sudo.partner_invoice_id
        if invoice_partner_sudo._can_be_edited_by_current_customer(
            order_sudo=order_sudo
        ) and not invoice_partner_sudo._check_billing_address(order_sudo=order_sudo):
            order_sudo._add_warning_alert(
                self.env._(
                    "Your billing address appears to be incomplete or invalid."
                    " Please ensure all required fields are correctly filled and try again."
                )
            )
            return f"/shop/address?partner_id={invoice_partner_sudo.id}&address_type=billing"

    @api.model
    def _check_shop_checkout_completion(self, order_sudo, **_kwargs):
        """Check whether the `/shop/checkout` step is valid and complete, and return the incomplete
        page otherwise.

        :param sale.order order_sudo: The current cart, sudoed.
        :param dict kwargs: Additional arguments for overrides.
        :return: The incomplete or invalid step href if any; otherwise, None.
        :rtype: str | None
        """
        if not order_sudo._is_cart_ready_for_payment():
            return "/shop/checkout"

    @api.model
    def _check_shop_payment_completion(self, order_sudo, **_kwargs):
        """Check whether the `/shop/payment` step is valid and complete, and return the incomplete
        page otherwise.

        :param sale.order order_sudo: The current cart, sudoed.
        :param dict kwargs: Additional arguments for overrides.
        :return: The incomplete or invalid step href if any; otherwise, None.
        :rtype: str | None
        """
        # The commitment date might have been promised days before the actual payment.
        if not order_sudo._is_commitment_date_valid():
            return "/shop/checkout"

        # Ensure prices are still correct after /shop/payment
        if order_sudo._update_cart_taxes_and_prices():
            return "/shop/payment"
