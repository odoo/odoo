"""WooCommerce customer/address data → Odoo res.partner field values."""

import logging

_logger = logging.getLogger(__name__)


class CustomerMapper:
    """Transforms WooCommerce customer/address JSON to Odoo res.partner vals."""

    # ── Full Customer ─────────────────────────────────────────────────────────

    @classmethod
    def to_partner_vals(cls, wc_customer, country_id=None, state_id=None):
        """Map a WooCommerce customer record to res.partner create/write vals.

        :param wc_customer: dict from GET /customers/<id>
        :param country_id: resolved res.country ID for billing country
        :param state_id: resolved res.country.state ID for billing state
        :returns: dict for res.partner.create() / .write()
        """
        billing = wc_customer.get('billing', {})
        first = (billing.get('first_name') or wc_customer.get('first_name') or '').strip()
        last = (billing.get('last_name') or wc_customer.get('last_name') or '').strip()
        name = f'{first} {last}'.strip() or wc_customer.get('username') or 'Unknown Customer'

        vals = {
            'name': name,
            'email': (billing.get('email') or wc_customer.get('email') or '').strip() or False,
            'phone': (billing.get('phone') or '').strip() or False,
            'is_company': False,
            'customer_rank': 1,
        }

        # Billing address
        street = (billing.get('address_1') or '').strip()
        street2 = (billing.get('address_2') or '').strip()
        if street:
            vals['street'] = street
        if street2:
            vals['street2'] = street2

        city = (billing.get('city') or '').strip()
        if city:
            vals['city'] = city

        zip_code = (billing.get('postcode') or '').strip()
        if zip_code:
            vals['zip'] = zip_code

        company_name = (billing.get('company') or '').strip()
        if company_name:
            vals['company_name'] = company_name

        if country_id:
            vals['country_id'] = country_id
        if state_id:
            vals['state_id'] = state_id

        return vals

    # ── Guest / Order Billing Address ─────────────────────────────────────────

    @classmethod
    def billing_to_partner_vals(cls, billing, country_id=None, state_id=None):
        """Map WooCommerce order billing address to res.partner vals.

        Used for guest orders where wc_customer_id == 0.

        :param billing: dict from order['billing']
        :returns: dict for res.partner.create() / .write()
        """
        first = (billing.get('first_name') or '').strip()
        last = (billing.get('last_name') or '').strip()
        name = f'{first} {last}'.strip() or billing.get('email') or 'Guest Customer'

        vals = {
            'name': name,
            'email': (billing.get('email') or '').strip() or False,
            'phone': (billing.get('phone') or '').strip() or False,
            'is_company': False,
            'customer_rank': 1,
            'street': (billing.get('address_1') or '').strip() or False,
            'street2': (billing.get('address_2') or '').strip() or False,
            'city': (billing.get('city') or '').strip() or False,
            'zip': (billing.get('postcode') or '').strip() or False,
        }

        company_name = (billing.get('company') or '').strip()
        if company_name:
            vals['company_name'] = company_name

        if country_id:
            vals['country_id'] = country_id
        if state_id:
            vals['state_id'] = state_id

        # Remove False values to avoid overwriting existing data on update
        return {k: v for k, v in vals.items() if v is not False}

    # ── Shipping Address ──────────────────────────────────────────────────────

    @classmethod
    def shipping_to_partner_vals(cls, shipping, parent_id, country_id=None, state_id=None):
        """Map WooCommerce order shipping address to a delivery res.partner.

        :param shipping: dict from order['shipping']
        :param parent_id: ID of the parent partner (invoice/commercial partner)
        :returns: dict for res.partner.create()
        """
        first = (shipping.get('first_name') or '').strip()
        last = (shipping.get('last_name') or '').strip()
        name = f'{first} {last}'.strip() or 'Shipping Address'

        return {
            'name': name,
            'type': 'delivery',
            'parent_id': parent_id,
            'street': (shipping.get('address_1') or '').strip() or False,
            'street2': (shipping.get('address_2') or '').strip() or False,
            'city': (shipping.get('city') or '').strip() or False,
            'zip': (shipping.get('postcode') or '').strip() or False,
            'country_id': country_id or False,
            'state_id': state_id or False,
            'phone': (shipping.get('phone') or '').strip() or False,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def extract_email(wc_customer_or_billing):
        """Extract a normalized email from a customer or billing dict."""
        return (wc_customer_or_billing.get('email') or '').strip().lower() or None
