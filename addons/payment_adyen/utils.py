import base64
import binascii
import hashlib
import hmac

from odoo.addons.payment import utils as payment_utils


def format_partner_name(partner_name):
    """Format the partner name to comply with the payload structure of the API request.

    :param str partner_name: The name of the partner making the payment.
    :return: The formatted partner name.
    :rtype: dict
    """
    first_name, last_name = payment_utils.split_partner_name(partner_name)
    return {
        "firstName": first_name,
        "lastName": last_name,
    }


def include_partner_addresses(tx_sudo):
    """Include the billing and delivery addresses of the related sales order to the payload of the
    API request.

    If no related sales order exists, the addresses are not included.

    Note: `self.check_singleton()`

    :param payment.transaction tx_sudo: The sudoed transaction of the payment.
    :return: The subset of the API payload that includes the billing and delivery addresses.
    :rtype: dict
    """
    tx_sudo.check_singleton()

    if "sale_order_ids" in tx_sudo._fields:  # The module `sale` is installed.
        order = tx_sudo.sale_order_ids[:1]
        if order:
            return {
                "billingAddress": format_partner_address(order.partner_invoice_id),
                "deliveryAddress": format_partner_address(order.partner_shipping_id),
            }
    return {}


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
        "stateOrProvince": partner.state_id.code
        or "Unknown",  # The state is not always required.
        "postalCode": partner.zip or "",
        # Fill in the address fields if the format is supported, or fallback to the raw address.
        "street": street_data.get("street_name", partner.street) or "Unknown",
        "houseNumberOrName": street_data.get("street_number") or "",
    }


def compute_notification_signature(payload, hmac_key):
    """Compute the signature from the payload.

    See https://docs.adyen.com/development-resources/webhooks/verify-hmac-signatures

    :param dict payload: The notification payload
    :param str hmac_key: The HMAC key of the provider handling the transaction
    :return: The computed signature
    :rtype: str
    """

    def _flatten_dict(_value, _path_base="", _separator="."):
        """Recursively generate a flat representation of a dict.

        :param Object _value: The value to flatten. A dict or an already flat value
        :param str _path_base: They base path for keys of _value, including preceding separators
        :param str _separator: The string to use as a separator in the key path
        """
        if isinstance(_value, dict):  # The inner value is a dict, flatten it
            _path_base = _path_base if not _path_base else _path_base + _separator
            for _key in _value:
                yield from _flatten_dict(_value[_key], _path_base + str(_key))
        else:  # The inner value cannot be flattened, yield it
            yield _path_base, _value

    def _to_escaped_string(_value):
        """Escape payload values that are using illegal symbols and cast them to string.

        String values containing `\\` or `:` are prefixed with `\\`.
        Empty values (`None`) are replaced by an empty string.

        :param Object _value: The value to escape
        :return: The escaped value
        :rtype: string
        """
        if isinstance(_value, str):
            return _value.replace("\\", "\\\\").replace(":", "\\:")
        elif _value is None:
            return ""
        else:
            return str(_value)

    signature_keys = [
        "pspReference",
        "originalReference",
        "merchantAccountCode",
        "merchantReference",
        "amount.value",
        "amount.currency",
        "eventCode",
        "success",
    ]
    # Flatten the payload to allow accessing inner dicts naively
    flattened_payload = dict(_flatten_dict(payload))
    # Build the list of signature values as per the list of required signature keys
    signature_values = [flattened_payload.get(key) for key in signature_keys]
    # Escape values using forbidden symbols
    escaped_values = [_to_escaped_string(value) for value in signature_values]
    # Concatenate values together with ':' as delimiter
    signing_string = ":".join(escaped_values)
    # Convert the HMAC key to the binary representation
    binary_hmac_key = binascii.a2b_hex(hmac_key.encode("ascii"))
    # Calculate the HMAC with the binary representation of the signing string with SHA-256
    binary_hmac = hmac.new(
        binary_hmac_key, signing_string.encode("utf-8"), hashlib.sha256
    )
    # Calculate the signature by encoding the result with Base64
    return base64.b64encode(binary_hmac.digest()).decode()
