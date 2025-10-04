# Part of Odoo. See LICENSE file for full copyright and licensing details.

def get_publishable_key(provider_sudo):
    """ Return the publishable key for Stripe.

    Note: This method serves as a hook for modules that would fully implement Stripe Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The publishable key
    :rtype: str
    """
    return provider_sudo.stripe_publishable_key


def get_secret_key(provider_sudo):
    """ Return the secret key for Stripe.

    Note: This method serves as a hook for modules that would fully implement Stripe Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :return: The secret key
    :rtype: str
    """
    return provider_sudo.stripe_secret_key


def get_webhook_secret(provider_sudo):
    """ Return the webhook secret for Stripe.

    Note: This method serves as a hook for modules that would fully implement Stripe Connect.

    :param recordset provider_sudo: The provider on which the key should be read, as a sudoed
                                    `payment.provider` record.
    :returns: The webhook secret
    :rtype: str
    """
    return provider_sudo.stripe_webhook_secret


def include_shipping_address(tx_sudo):
    """ Include the shipping address of the related sales order or invoice to the payload of the API
    request. If no related sales order or invoice exists, the addres is not included.

    Note: `self.ensure_one()`

    :param payment.transaction tx_sudo: The sudoed transaction of the payment.
    :return: The subset of the API payload that includes the billing and delivery addresses.
    :rtype: dict
    """
    tx_sudo.ensure_one()

    if 'sale_order_ids' in tx_sudo._fields and tx_sudo.sale_order_ids:
        order = tx_sudo.sale_order_ids[:1]
        return format_shipping_address(order.partner_shipping_id)
    elif 'invoice_ids' in tx_sudo._fields and tx_sudo.invoice_ids:
        invoice = tx_sudo.invoice_ids[:1]
        return format_shipping_address(invoice.partner_shipping_id)
    return {}


def format_shipping_address(shipping_partner):
    """ Format the shipping address to comply with the payload structure of the API request.

    :param res.partner shipping_partner: The shipping partner.
    :return: The formatted shipping address.
    :rtype: dict
    """
    return {
        'shipping[address][city]': shipping_partner.city,
        'shipping[address][country]': shipping_partner.country_id.code,
        'shipping[address][line1]': shipping_partner.street,
        'shipping[address][line2]': shipping_partner.street2,
        'shipping[address][postal_code]': shipping_partner.zip,
        'shipping[address][state]': shipping_partner.state_id.name,
        'shipping[name]': shipping_partner.name or shipping_partner.parent_id.name,
    }
