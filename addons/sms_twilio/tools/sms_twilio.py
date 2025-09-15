import base64
import hashlib
import hmac

from werkzeug.urls import url_join

from odoo.addons.phone_validation.tools import phone_validation


def get_twilio_from_number(company, to_number):
    """
    :return: the Twilio number from which we'll send the SMS depending on the country of destination (to_number)
    """
    country_code = phone_validation.phone_get_country_code_for_number(to_number)
    from_number = company.sms_twilio_number_ids
    if not from_number or not country_code:
        return from_number[:1]
    return from_number.sorted(
        lambda rec: rec.country_code == country_code,
        reverse=True,
    )[0]


def get_twilio_status_callback_url(company, uuid):
    base_url = company.get_base_url()  # When testing locally, this should be replaced by a real url (not localhost, e.g. with ngrok)
    return url_join(base_url, f'/sms_twilio/status/{uuid}')


def generate_twilio_sms_callback_signature(company, sms_uuid, callback_params):
    url = get_twilio_status_callback_url(company, sms_uuid)
    # Sort the POST parameters by key and concatenate them to URL
    sorted_params = ''.join(f"{k}{v}" for k, v in sorted(callback_params.items()))
    data = url + sorted_params

    # Compute HMAC-SHA1 digest and then base64 encode
    return base64.b64encode(
        hmac.new(
            company.sms_twilio_auth_token.encode(),
            data.encode(),
            hashlib.sha1
        ).digest()
    ).decode()
