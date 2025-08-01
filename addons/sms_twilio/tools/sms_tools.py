from werkzeug.urls import url_join

from odoo import fields

from odoo.addons.phone_validation.tools import phone_validation


def get_country_code_from_phone(phone_number):
    phone_number = phone_number or ""
    return phone_validation.phone_get_region_data_for_number(phone_number).get('code')


def get_twilio_from_number(company, to_number):
    """
    :return: the Twilio number from which we'll send the SMS depending on the country of destination (to_number)
    """
    country_code = get_country_code_from_phone(to_number)
    from_number = company.env['sms.twilio.number'].search([
        ('company_id', '=', company.id),
    ])
    return fields.first(from_number.filtered(lambda n: n.country_code == country_code)) or fields.first(from_number)


def get_twilio_status_callback_url(company, uuid):
    base_url = company.get_base_url()  # When testing locally, this should be replaced by a real url (not localhost, e.g. with ngrok)
    return url_join(base_url, f'/sms_twilio/status/{uuid}')
