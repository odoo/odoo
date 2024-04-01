
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import lxml.html
from requests.exceptions import ConnectionError, HTTPError, Timeout
from odoo.exceptions import UserError

def verify_signed_invoice(json_data):
    try:
        url = "https://einvoice1.gst.gov.in/Others/VSignedInvoice"
        get_res = requests.get(url, timeout=100)
        cookies = get_res.cookies.get_dict()
        get_res_text = get_res.text
        get_res_html = lxml.html.fromstring(get_res_text)
        requestverificationtoken = get_res_html.xpath('//input[@name="__RequestVerificationToken"]/@value')
        if not requestverificationtoken:
            return get_res_text
        payload = {
            'submit': 'Upload',
            '__RequestVerificationToken': requestverificationtoken[0],
        }
        files = [('file', ('json_data.json', json_data.encode(), 'application/json'))]
        response = requests.post(url, cookies=cookies, data=payload, files=files, timeout=100)
        response_html = response.text
        response_html = response_html.replace('href="/', 'href="https://einvoice1.gst.gov.in/')
        response_html = response_html.replace('src="/', 'src="https://einvoice1.gst.gov.in/')
        return response_html

    except ConnectionError:
        raise UserError("Failed to establish connection to the server.")
    except Timeout:
        raise UserError("Request timed out. Please try again later.")
    except HTTPError as e:
        raise UserError("HTTP Error: {}".format(e.response.status_code))
    except Exception as e:
        raise UserError("An unexpected error occurred: {}".format(str(e)))
