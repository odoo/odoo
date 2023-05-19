# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import lxml

def verify_signed_invoice(json_data):
    url = "https://einvoice1.gst.gov.in/Others/VSignedInvoice"
    get_res = requests.get(url)
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
    response = requests.post(url, cookies=cookies, data=payload, files=files)
    response_html = response.text
    response_html = response_html.replace('href="/', 'href="https://einvoice1.gst.gov.in/')
    response_html = response_html.replace('src="/', 'src="https://einvoice1.gst.gov.in/')
    return response_html
