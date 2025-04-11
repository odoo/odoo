# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests

from odoo import _
from odoo.addons.iap.tools import iap_tools
from odoo.http import request
from odoo.exceptions import UserError
from werkzeug.urls import url_join

_logger = logging.getLogger(__name__)

PROMPT = (
    "Extract details from the image as a JSON object. "
    "Fields: company_name, owners_name(one name), phone_number(main mobile number), email, website, "
    "job_position, address_line_1, address_line_2, city, state(give 2 chars/digits code), "
    "country(give 2 chars ISO code), zip. If a Field is missing or empty, REMOVE that Field from output JSON. "
    "Never guess or add something like 'not specified'. "
    "Return ONLY the JSON object on a SINGLE LINE, without code editor."
)

OPENAI_BASE_URL = "https://api.openai.com"
OPENAI_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"


class BusinessCardScanner:

    def _ocr_from_openai(image_url, api_key):
        """Use OpenAI API to extract business card data."""

        url = url_join(OPENAI_BASE_URL, OPENAI_CHAT_COMPLETIONS_PATH)
        with requests.Session() as session:
            session.headers.update({
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            })
            response = session.post(
                url,
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": [
                            {"type": "text", "text": PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]}
                    ],
                },
                timeout=10,
            )
        if response.status_code == 200:
            response_content = response.json()
            result = response_content['choices'][0]['message']['content']
            extracted_data = json.loads(result)
            return extracted_data
        else:
            raise UserError(
                _("Oops, openAI is unreachable. Please contact your administrator to verify settings.")
            )

    def ocr_from_iap(image_url):
        """Use Odoo's IAP to extract business card data."""

        IrConfigParameter = request.env["ir.config_parameter"].sudo()
        olg_api_endpoint = IrConfigParameter.get_param(
            "web_editor.olg_api_endpoint", "https://olg.api.odoo.com"
        )
        database_id = IrConfigParameter.get_param("database.uuid")
        response = iap_tools.iap_jsonrpc(
            url_join(olg_api_endpoint, "/api/olg/1/chat"),
            params={
                "prompt": PROMPT,
                "conversation_history": [
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {
                            "url": image_url}
                        }
                    ]}
                ],
                "database_id": database_id,
            },
            timeout=10,
        )
        if response['status'] == 'success':
            result = response['content']
            extracted_data = json.loads(result)
            return extracted_data
        else:
            raise UserError(
                _("Oops, openAI is unreachable. Please contact your administrator to verify settings.")
            )

    def extract_data(image_url, api_key):
        """Extract useful information from business cards using OpenAI API or olg IAP"""

        if not image_url:
            return None

        try:
            if api_key:
                return BusinessCardScanner._ocr_from_openai(image_url, api_key)
            else:
                return BusinessCardScanner.ocr_from_iap(image_url)
        except requests.exceptions.RequestException as e:
            raise UserError(_("Network error while processing the business card: %s", str(e)))
        except json.JSONDecodeError:
            raise UserError(_("Failed to parse the response. openAI may have returned an unexpected format."))

    def business_cards_to_leads(self, attachments):
        """Create opportunities from the details extracted from images of business cards"""

        base_url = self.get_base_url()
        api_key = request.env["ir.config_parameter"].sudo().get_param("openai_api_key")

        lead_values = []
        valid_attachments = []

        for attachment in attachments:
            image_url = f"{base_url}/web/image/{attachment.id}?access_token={attachment.access_token}"
            extracted_data = BusinessCardScanner.extract_data(image_url, api_key)
            company_name, contact_name, phone, state, country = (
                extracted_data.get('company_name', ''),
                extracted_data.get('owners_name', ''),
                extracted_data.get('phone_number', ''),
                extracted_data.get('state', ''),
                extracted_data.get('country', '')
            )
            if contact_name:
                name = f"{contact_name}'s opportunity"
            elif company_name:
                name = f"{company_name}'s opportunity"
            else:
                name = ""

            if country:
                search_country = self.env['res.country'].name_search(country, limit=1)
                country_id = search_country[0][0] if search_country else None
            else:
                country_id = None

            if state:
                domain = [('country_id', '=', country_id)] if country_id else None
                search_state = self.env['res.country.state'].name_search(state, domain, limit=1)
                state_id = search_state[0][0] if search_state else None
            else:
                state_id = None

            if name:
                lead_values.append({
                    'name': name,
                    'type': 'opportunity',
                    'contact_name': contact_name,
                    'partner_name': company_name,
                    'phone': phone,
                    'email_from': extracted_data.get('email', ''),
                    'website': extracted_data.get('website', ''),
                    'function': extracted_data.get('job_position', ''),
                    'street': extracted_data.get('address_line_1', ''),
                    'street2': extracted_data.get('address_line_2', ''),
                    'city': extracted_data.get('city', ''),
                    'state_id': state_id,
                    'country_id': country_id,
                    'zip': extracted_data.get('zip', '')
                })
                valid_attachments.append(attachment)
            else:
                _logger.warning("we could not read sufficient information from the provided business card - %s", attachment.name)

        leads = self.env['crm.lead'].create(lead_values)

        for lead in leads:
            lead.phone = lead._phone_format(number=lead.phone)

        return leads, valid_attachments
