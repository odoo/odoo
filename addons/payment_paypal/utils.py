# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


def normalize_paypal_payment_data(data, from_webhook=False):
    """Normalize the payment data received from PayPal.

    The payment data received from PayPal has a different format depending on whether the data
    come from the payment request response (order creation or capture), or from the webhook.

    :param dict data: The data to normalize.
    :param bool from_webhook: Whether the data come from the webhook.
    :return: The normalized data.
    :rtype: dict
    """
    purchase_unit = data["purchase_units"][0]
    result = {
        "payment_source": data["payment_source"],
        "reference_id": purchase_unit.get("reference_id"),
        "purchase_units": data["purchase_units"],
    }
    if from_webhook:
        result.update({
            **purchase_unit,
            "txn_type": data.get("intent"),
            "id": data.get("id"),
            "status": data.get("status"),
        })
    elif captured := purchase_unit.get("payments", {}).get("captures"):
        result.update({**captured[0], "txn_type": "CAPTURE"})
    else:
        _logger.warning("Invalid PayPal response format, can't normalize.")
    return result


def format_partner_address(partner):
    """Format the partner address values to PayPal address values. When provided, PayPal requires
    at least a country code, so returns only an email address or an empty dict if partner lacks a
    `country_id`.

    :param res.partner partner: The relevant partner record.
    :return: Address values suitable for PayPal processing.
    :rtype: dict
    """
    address_vals = {"email_address": partner.email} if partner.email else {}
    if not partner.country_id:
        return address_vals

    address_mapping = {
        "address_line_1": partner.street,
        "address_line_2": partner.street2,
        "admin_area_1": partner.state_id.code,
        "admin_area_2": partner.city,
        "postal_code": partner.zip,
        "country_code": partner.country_code,
    }
    address_vals.update(address={key: value for key, value in address_mapping.items() if value})
    return address_vals


def format_shipping_address(tx_sudo):
    """Format the shipping address of the related sales order or invoice to the payload of the API
    request. If no related sales order or invoice exists, or the address is incomplete, the shipping
    address is not included.

    :param payment.transaction tx_sudo: The sudoed transaction of the payment.
    :return: The subset of the API payload that includes the billing and delivery addresses.
    :rtype: dict
    """
    address_vals = {}

    if "sale_order_ids" in tx_sudo and tx_sudo.sale_order_ids:
        order = tx_sudo.sale_order_ids[0]
        partner_shipping = order.partner_shipping_id
    elif "invoice_ids" in tx_sudo and tx_sudo.invoice_ids:
        invoice = tx_sudo.invoice_ids[0]
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
        address_vals["shipping"] = format_partner_address(partner_shipping)
    return address_vals
