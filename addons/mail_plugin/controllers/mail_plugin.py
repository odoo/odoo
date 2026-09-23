import base64
import json
import logging

import requests
from markupsafe import Markup
from werkzeug.exceptions import Forbidden

from odoo import Command, http, tools
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)

LOGO_MAX_BYTES = 5 * 1024 * 1024


class MailPluginController(http.Controller):
    @http.route(
        "/mail_client_extension/modules/get",
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def modules_get(self, **kwargs):
        return {"modules": ["contacts", "crm"]}

    @http.route(
        "/mail_plugin/partner/enrich_and_create_company",
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def res_partner_enrich_and_create_company(self, partner_id: int):

        partner = request.env["res.partner"].browse(partner_id).exists()

        if not partner:
            return {"error": request.env._("This partner does not exist")}

        if partner.parent_id:
            return {
                "error": request.env._(
                    "The partner already has a company related to him"
                )
            }

        normalized_email = partner.email_normalized
        if not normalized_email:
            return {
                "error": request.env._(
                    "The email of this contact is not valid and we can not enrich it"
                )
            }

        company, enrichment_info = self._create_company_from_iap(normalized_email)

        if company:
            partner.write({"parent_id": company.id})

        return {
            "enrichment_info": enrichment_info,
            "company": self._get_company_data(company),
        }

    @http.route(
        "/mail_plugin/partner/enrich_and_update_company",
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def res_partner_enrich_and_update_company(self, partner_id: int):
        partner = request.env["res.partner"].browse(partner_id).exists()

        if not partner:
            return {"error": request.env._("This partner does not exist")}

        if not partner.is_company:
            return {"error": "Contact must be a company"}

        normalized_email = partner.email_normalized
        if not normalized_email:
            return {
                "error": "The email of this contact is not valid and we can not enrich it"
            }

        domain = tools.email_domain_extract(normalized_email)
        iap_data = self._iap_enrich(domain)

        if "enrichment_info" in iap_data:
            return {
                "enrichment_info": iap_data["enrichment_info"],
                "company": self._get_company_data(partner),
            }

        phone_numbers = iap_data.get("phone_numbers")

        partner_values = {}

        if not partner.phone_ids and phone_numbers:
            partner_values.update(
                {
                    "phone_ids": [
                        Command.create({"number": phone_numbers[0], "type": "landline"})
                    ]
                }
            )

        if not partner.iap_enrich_info:
            partner_values.update({"iap_enrich_info": json.dumps(iap_data)})

        if not partner.image_128:
            logo_url = iap_data.get("logo")
            if logo_url:
                try:
                    response = request.env["ir.egress"].request(
                        "GET",
                        logo_url,
                        purpose="mail_plugin_logo",
                        timeout=2,
                        max_bytes=LOGO_MAX_BYTES,
                    )
                    if response.ok:
                        partner_values.update(
                            {"image_1920": base64.b64encode(response.content)}
                        )
                except requests.exceptions.RequestException, ValueError:
                    _logger.info("Could not fetch the logo %s", logo_url, exc_info=True)

        model_fields_to_iap_mapping = {
            "street": "street_name",
            "city": "city",
            "zip": "postal_code",
            "website": "domain",
        }

        partner_values.update(
            {
                model_field: iap_data.get(iap_key)
                for model_field, iap_key in model_fields_to_iap_mapping.items()
                if not partner[model_field]
            }
        )

        partner.write(partner_values)

        partner.message_post_with_source(
            "iap_mail.enrich_company",
            render_values=iap_data,
            subtype_xmlid="mail.mt_note",
        )

        return {
            "enrichment_info": {"type": "company_updated"},
            "company": self._get_company_data(partner),
        }

    @http.route(
        ["/mail_client_extension/partner/get", "/mail_plugin/partner/get"],
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def res_partner_get(
        self,
        email: str | None = None,
        name: str | None = None,
        partner_id: int | None = None,
        **kwargs,
    ):

        if not (partner_id or (name and email)):
            return {
                "error": request.env._(
                    "You need to specify at least the partner_id or the name and the email"
                )
            }

        if partner_id:
            partner = request.env["res.partner"].browse(partner_id).exists()
            return self._get_contact_data(partner)

        normalized_email = tools.email_normalize(email)
        if not normalized_email:
            return {"error": request.env._("Bad Email.")}

        notification_emails = (
            request.env["mail.alias.domain"]
            .sudo()
            .search([])
            .mapped("default_from_email")
        )
        if normalized_email in notification_emails:
            return {
                "partner": {
                    "name": request.env._("Notification"),
                    "email": normalized_email,
                    "enrichment_info": {
                        "type": "odoo_custom_error",
                        "info": request.env._(
                            "This is your notification address. Search the Contact manually to link this email to a record."
                        ),
                    },
                },
            }

        partner = request.env["res.partner"].search(
            [
                "|",
                ("email", "in", [normalized_email, email]),
                ("email_normalized", "=", normalized_email),
            ],
            limit=1,
        )

        response = self._get_contact_data(partner)

        if not response["partner"]:
            response["partner"] = {
                "id": -1,
                "email": email,
                "name": name,
                "enrichment_info": None,
            }
            company = self._find_existing_company(normalized_email)

            can_create_partner = request.env["res.partner"].has_access("create")

            if not company and can_create_partner:
                company, enrichment_info = self._create_company_from_iap(
                    normalized_email
                )
                response["partner"]["enrichment_info"] = enrichment_info
            response["partner"]["company"] = self._get_company_data(company)

        return response

    @http.route(
        "/mail_plugin/partner/search",
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def res_partners_search(self, search_term: str, limit: int = 30, **kwargs):
        normalized_email = tools.email_normalize(search_term)

        if normalized_email:
            filter_domain = [("email_normalized", "ilike", search_term)]
        else:
            filter_domain = [
                "|",
                "|",
                ("complete_name", "ilike", search_term),
                ("ref", "=", search_term),
                ("email", "ilike", search_term),
            ]

        partners = request.env["res.partner"].search(filter_domain, limit=limit)

        partners = [self._get_partner_data(partner) for partner in partners]
        return {"partners": partners}

    @http.route(
        ["/mail_client_extension/partner/create", "/mail_plugin/partner/create"],
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def res_partner_create(self, email: str, name: str, company: int):
        notification_emails = (
            request.env["mail.alias.domain"]
            .sudo()
            .search([])
            .mapped("default_from_email")
        )
        if tools.email_normalize(email) in notification_emails:
            raise Forbidden
        partner_info = {
            "name": name,
            "email": email,
        }

        if company and company > -1:
            partner_info["parent_id"] = company
        partner = request.env["res.partner"].create(partner_info)

        return {"id": partner.id}

    @http.route(
        "/mail_plugin/log_mail_content",
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def log_mail_content(
        self, model: str, res_id: int, message: str, attachments: list | None = None
    ):
        if model not in self._mail_content_logging_models_whitelist():
            raise Forbidden

        if attachments:
            attachments = [
                (name, base64.b64decode(content)) for name, content in attachments
            ]

        request.env[model].browse(res_id).message_post(
            body=Markup(message), attachments=attachments
        )
        return True

    @http.route(
        "/mail_plugin/get_translations",
        type="jsonrpc",
        auth="bearer",
        scope="odoo.plugin.outlook",
        cors="*",
        typed=True,
    )
    def get_translations(self):
        return self._prepare_translations()

    def _iap_enrich(self, domain):
        if domain in iap_tools._MAIL_PROVIDERS:
            return {"enrichment_info": {"type": "missing_data"}}

        enriched_data = {}
        try:
            response = request.env["iap.enrich.api"]._request_enrich({domain: domain})
        except iap_tools.InsufficientCreditError:
            enriched_data["enrichment_info"] = {
                "type": "insufficient_credit",
                "info": request.env["iap.account"].get_credits_url("reveal"),
            }
        except UserError:
            enriched_data["enrichment_info"] = {
                "type": "other",
                "info": "Unknown reason",
            }
        else:
            enriched_data = response.get(domain)
            if not enriched_data:
                enriched_data = {
                    "enrichment_info": {
                        "type": "no_data",
                        "info": "The enrichment API found no data for the email provided.",
                    }
                }
        return enriched_data

    def _find_existing_company(self, email):
        search = self._get_iap_search_term(email)

        partner_iap = (
            request.env["res.partner.iap"]
            .sudo()
            .search([("iap_search_domain", "=", search)], limit=1)
        )
        if partner_iap:
            return partner_iap.partner_id.sudo(False)

        return request.env["res.partner"].search(
            [("is_company", "=", True), ("email_normalized", "=ilike", "%" + search)],
            limit=1,
        )

    def _get_company_data(self, company):
        if not company:
            return {"id": -1}

        try:
            company.check_access("read")
        except AccessError:
            return {"id": company.id, "name": request.env._("No Access")}

        fields_list = ["id", "name", "email", "website"]

        company_values = {fname: company[fname] for fname in fields_list}
        company_values["phone"] = company._phone_get_number().number
        company_values["address"] = {
            "street": company.street,
            "city": company.city,
            "zip": company.zip,
            "country": company.country_id.name if company.country_id else "",
        }
        company_values["additionalInfo"] = (
            json.loads(company.iap_enrich_info) if company.iap_enrich_info else {}
        )
        company_values["image"] = company.image_1920

        return company_values

    def _create_company_from_iap(self, email):
        domain = tools.email_domain_extract(email)
        iap_data = self._iap_enrich(domain)
        if "enrichment_info" in iap_data:
            return None, iap_data["enrichment_info"]

        phone_numbers = iap_data.get("phone_numbers")
        emails = iap_data.get("email")
        new_company_info = {
            "is_company": True,
            "name": iap_data.get("name") or domain,
            "street": iap_data.get("street_name"),
            "city": iap_data.get("city"),
            "zip": iap_data.get("postal_code"),
            "phone_ids": [
                Command.create({"number": phone_numbers[0], "type": "landline"})
            ]
            if phone_numbers
            else None,
            "website": iap_data.get("domain"),
            "email": emails[0] if emails else None,
        }

        logo_url = iap_data.get("logo")
        if logo_url:
            try:
                response = request.env["ir.egress"].request(
                    "GET",
                    logo_url,
                    purpose="mail_plugin_logo",
                    timeout=2,
                    max_bytes=LOGO_MAX_BYTES,
                )
                if response.ok:
                    new_company_info["image_1920"] = base64.b64encode(response.content)
            except (requests.exceptions.RequestException, ValueError) as e:
                _logger.warning(
                    "Download of image for new company %s failed, error %s",
                    new_company_info["name"],
                    e,
                )

        if iap_data.get("country_code"):
            country = request.env["res.country"].search(
                [("code", "=", iap_data["country_code"].upper())]
            )
            if country:
                new_company_info["country_id"] = country.id
                if iap_data.get("state_code"):
                    state = request.env["res.country.state"].search(
                        [
                            ("code", "=", iap_data["state_code"]),
                            ("country_id", "=", country.id),
                        ]
                    )
                    if state:
                        new_company_info["state_id"] = state.id

        new_company_info.update(
            {
                "iap_search_domain": self._get_iap_search_term(email),
                "iap_enrich_info": json.dumps(iap_data),
            }
        )

        new_company = request.env["res.partner"].create(new_company_info)

        new_company.message_post_with_source(
            "iap_mail.enrich_company",
            render_values=iap_data,
            subtype_xmlid="mail.mt_note",
        )

        return new_company, {"type": "company_created"}

    def _get_partner_data(self, partner):

        fields_list = ["id", "name", "email", "is_company"]

        partner_values = {fname: partner[fname] for fname in fields_list}
        partner_values["phone"] = partner._phone_get_number().number
        partner_values["image"] = partner.image_128
        partner_values["title"] = partner.function
        partner_values["enrichment_info"] = None

        try:
            partner.check_access("write")
            partner_values["can_write_on_partner"] = True
        except AccessError:
            partner_values["can_write_on_partner"] = False

        if not partner_values["name"]:
            name, email_normalized = tools.parse_contact_from_email(
                partner_values["email"]
            )
            partner_values["name"] = name or email_normalized

        return partner_values

    def _get_contact_data(self, partner):
        if partner:
            partner_response = self._get_partner_data(partner)
            if partner.is_company:
                partner_response["company"] = self._get_company_data(partner)
            elif partner.parent_id:
                partner_response["company"] = self._get_company_data(partner.parent_id)
            else:
                partner_response["company"] = self._get_company_data(None)
        else:
            partner_response = {}

        return {
            "partner": partner_response,
            "user_companies": request.env.user.company_ids.ids,
            "can_create_partner": request.env["res.partner"].has_access("create"),
        }

    def _mail_content_logging_models_whitelist(self):
        return ["res.partner"]

    def _get_iap_search_term(self, email):
        domain = tools.email_domain_extract(email)
        return (
            ("@" + domain) if domain not in iap_tools._MAIL_DOMAIN_BLACKLIST else email
        )

    def _translation_modules_whitelist(self):
        return ["mail_plugin"]

    def _prepare_translations(self):
        lang = request.env["res.users"].browse(request.env.uid).lang
        translations_per_module = request.env[
            "ir.http"
        ]._get_translations_for_webclient(self._translation_modules_whitelist(), lang)[
            0
        ]
        translations_dict = {}
        for module in self._translation_modules_whitelist():
            translations = translations_per_module.get(module, {})
            messages = translations.get("messages", {})
            for message in messages:
                translations_dict.update({message["id"]: message["string"]})
        return translations_dict
