# Part of Odoo. See LICENSE file for full copyright and licensing details.

def format_partner_address(partner):
    """ Format the partner address values to PayPal address values. When provided, PayPal requires
    at least a country code, so returns only an email address or an empty dict if partner lacks a
    `country_id`.

    :param res.partner partner: The relevant partner record.
    :return: Address values suitable for PayPal processing.
    :rtype: dict
    """
    address_vals = {'email_address': partner.email} if partner.email else {}
    if not partner.country_id:
        return address_vals

    address_mapping = {
        'address_line_1': partner.street,
        'address_line_2': partner.street2,
        'admin_area_1': partner.state_id.code,
        'admin_area_2': partner.city,
        'postal_code': partner.zip,
        'country_code': partner.country_code,
    }
    address_vals.update(
        address={key: value for key, value in address_mapping.items() if value},
    )
    return address_vals


def format_shipping_address(tx_sudo):
    """ Format the shipping address of the related sales order or invoice to the payload of the API
    request. If no related sales order or invoice exists, or the address is incomplete, the shipping
    address is not included.

    :param payment.transaction tx_sudo: The sudoed transaction of the payment.
    :return: The subset of the API payload that includes the billing and delivery addresses.
    :rtype: dict
    """
    address_vals = {}

    if 'sale_order_ids' in tx_sudo and tx_sudo.sale_order_ids:
        order = next(iter(tx_sudo.sale_order_ids))
        partner_shipping = order.partner_shipping_id
    elif 'invoice_ids' in tx_sudo and tx_sudo.invoice_ids:
        invoice = next(iter(tx_sudo.invoice_ids))
        partner_shipping = invoice.partner_shipping_id
    else:
        return address_vals

    if (
        partner_shipping.street
        and partner_shipping.city
        and (country := partner_shipping.country_id)
        and (partner_shipping.zip or not country.zip_required)
        and (partner_shipping.state_id or not country.state_required)
    ):
        address_vals['shipping'] = format_partner_address(partner_shipping)
    return address_vals
