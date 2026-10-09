# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import utils as payment_utils


def format_partner_name(partner_name):
    """Format the partner name to comply with the payload structure of the API request.

    :param str partner_name: The name of the partner making the payment.
    :return: The formatted partner name.
    :rtype: dict
    """
    first_name, last_name = payment_utils.split_partner_name(partner_name)
    return {"firstName": first_name, "lastName": last_name}


def include_partner_addresses(tx_sudo):
    """Include the billing and delivery addresses of the transaction to the payload of the API
    request.

    Either address is omitted if not set on the transaction.

    Note: `self.ensure_one()`

    :param payment.transaction tx_sudo: The sudoed transaction of the payment.
    :return: The subset of the API payload that includes the billing and delivery addresses.
    :rtype: dict
    """
    tx_sudo.ensure_one()
    partner_addresses = {}
    if tx_sudo.billing_partner_id:
        partner_addresses["billingAddress"] = format_partner_address(tx_sudo.billing_partner_id)
    if tx_sudo.delivery_partner_id:
        partner_addresses["deliveryAddress"] = format_partner_address(tx_sudo.delivery_partner_id)
    return partner_addresses


def format_partner_address(partner):
    """Format the partner address to comply with the payload structure of the API request.

    :param res.partner partner: The partner making the payment.
    :return: The formatted partner address.
    :rtype: dict
    """
    street_data = partner._get_street_split()
    # Unlike what is stated in https://docs.adyen.com/risk-management/avs-checks/, not all fields
    # are required at all time. Thus, we fall back to 'Unknown' when a field is not set to avoid
    # blocking the payment (empty string are not accepted) or passing `False` (which may not pass
    # the fraud check).
    return {
        "city": partner.city or "Unknown",
        "country": partner.country_id.code or "ZZ",  # 'ZZ' if the country is not known.
        "stateOrProvince": partner.state_id.code or "Unknown",  # The state is not always required.
        "postalCode": partner.zip or "",
        # Fill in the address fields if the format is supported, or fallback to the raw address.
        "street": street_data.get("street_name", partner.street) or "Unknown",
        "houseNumberOrName": street_data.get("street_number") or "",
    }
