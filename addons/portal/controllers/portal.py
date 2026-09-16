import math
import re
from urllib.parse import quote, urlsplit, urlunsplit

from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from odoo import SUPERUSER_ID, _
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.http import Controller, prepare_content_disposition_header, request, route
from odoo.libs.debug_log import DebugLog
from odoo.tools import clean_context, consteq, single_email_re, str2bool
from odoo.tools.translate import LazyTranslate

from odoo.addons.portal.utils import get_url_with_params as _get_url_with_params
from odoo.addons.web.controllers.utils import _is_local_url

_debug = DebugLog(__name__)

_lt = LazyTranslate(__name__)


def pager(url, total, page=1, step=30, scope=5, url_args=None):
    step = max(1, step)
    page_count = max(1, math.ceil(max(0, total) / step))

    page = max(1, min(int(page if str(page).isdecimal() else 1), page_count))

    page_previous = max(1, page - 1)
    page_next = min(page_count, page + 1)
    query = {k: v for k, v in (url_args or {}).items() if v is not None}
    base_url = urlsplit(_get_url_with_params(url, query, doseq=True))

    def get_url(page):
        path = f"{base_url.path}/page/{page}" if page > 1 else base_url.path
        return urlunsplit(base_url._replace(path=path))

    scope = max(scope, 3)
    if page_count <= scope:
        page_list = list(range(1, page_count + 1))
    elif page <= scope - 2:
        page_list = list(range(1, scope)) + ["…", page_count]
    elif page >= page_count - (scope - 3):
        page_list = [1, "…"] + list(range(page_count - (scope - 2), page_count + 1))
    else:
        half = (scope - 3) // 2
        window = list(range(page - half, page + half + 1))
        page_list = [1]
        if window[0] > 2:
            page_list.append("…")
        page_list += window
        if window[-1] < page_count - 1:
            page_list.append("…")
        page_list.append(page_count)

    pages = [
        {"num": p, "url": get_url(p) if p != "…" else None, "is_current": p == page}
        for p in page_list
    ]

    return {
        "page_count": page_count,
        "offset": (page - 1) * step,
        "page": {"url": get_url(page), "num": page},
        "page_first": {"url": get_url(1), "num": 1},
        "page_previous": {"url": get_url(page_previous), "num": page_previous},
        "page_next": {"url": get_url(page_next), "num": page_next},
        "page_last": {"url": get_url(page_count), "num": page_count},
        "pages": pages,
    }


def get_records_pager(ids, current, with_token=True):
    if current.id not in ids:
        return {}
    if "access_url" in current._fields:
        attr_name = "access_url"
    elif "website_url" in current._fields:
        attr_name = "website_url"
    else:
        return {}

    idx = ids.index(current.id)
    prev_record = idx != 0 and current.browse(ids[idx - 1])
    next_record = idx < len(ids) - 1 and current.browse(ids[idx + 1])

    return {
        "prev_record": _pager_url(prev_record, attr_name, with_token),
        "next_record": _pager_url(next_record, attr_name, with_token),
    }


def _pager_url(record, attr_name, with_token=True):
    if not record:
        return False
    if not record[attr_name]:
        return False
    if attr_name == "access_url" and with_token:
        return _get_url_with_params(
            record[attr_name], {"access_token": record._portal_get_or_create_token()}
        )
    return record[attr_name]


def _parse_record_id(raw_id):
    if not raw_id:
        return None
    try:
        return int(raw_id)
    except TypeError, ValueError:
        _debug.logic("record_id_rejected", raw=str(raw_id))
        raise NotFound from None


def _parse_bool_param(raw_value):
    return str2bool(raw_value or "false", default=False)


def _parse_callback_url(raw_callback, default):
    return raw_callback if _is_local_url(raw_callback) else default


def _as_password_field(raw_value):
    return raw_value if isinstance(raw_value, str) else ""


def _parse_counter_names(raw_counters):
    if not isinstance(raw_counters, (list, tuple, set, frozenset)):
        return []
    return [name for name in raw_counters if isinstance(name, str)]


def _is_zip_before_city(address_fields):
    return (
        "zip" in address_fields
        and "city" in address_fields
        and address_fields.index("zip") < address_fields.index("city")
    )


class CustomerPortal(Controller):
    _items_per_page = 80

    _FRAME_OPTIONS_HEADERS = {
        "X-Frame-Options": "SAMEORIGIN",
        "Content-Security-Policy": "frame-ancestors 'self'",
    }

    _RESERVED_ADDRESS_FORM_KEYS = frozenset(
        {
            "address_values",
            "error_messages",
            "extra_form_data",
            "invalid_fields",
            "is_commercial_address",
            "missing_fields",
            "partner_sudo",
            "verify_address_values",
        }
    )

    def _get_reserved_address_form_keys(self):
        return self._RESERVED_ADDRESS_FORM_KEYS

    def _filter_client_address_params(self, client_params):
        reserved = self._get_reserved_address_form_keys()
        return {
            key: value for key, value in client_params.items() if key not in reserved
        }

    def _prepare_portal_layout_values(self):
        sales_user_sudo = request.env["res.users"]
        partner_sudo = request.env.user.partner_id
        for candidate in (
            partner_sudo.user_id,
            partner_sudo.commercial_partner_id.user_id,
        ):
            if candidate and not candidate._is_public():
                sales_user_sudo = candidate
                break

        return {
            "sales_user": sales_user_sudo,
            "page_name": "home",
        }

    def _resolve_searchbar_option(self, options, key, default):
        if isinstance(key, str) and key in options:
            return key
        return default

    def _prepare_home_portal_values(self, counters):
        return {}

    @route(["/my/counters"], type="jsonrpc", auth="user", website=True, readonly=True)
    def counters(self, counters, **kw):
        cache = request.session.get("portal_counters", {}).copy()
        res = self._prepare_home_portal_values(_parse_counter_names(counters))
        cache.update({k: bool(v) for k, v in res.items() if k.endswith("_count")})
        if cache != request.session.get("portal_counters"):
            request.session["portal_counters"] = cache
        return res

    @route(
        ["/my", "/my/home"],
        type="http",
        auth="user",
        website=True,
        list_as_website_content=_lt("User Dashboard"),
    )
    def home(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_home_portal_values([]))
        return request.render("portal.portal_my_home", values)

    @route(["/my/account"], type="http", auth="user", website=True)
    def account(self, **kwargs):
        response = request.render(
            "portal.portal_my_details",
            self._prepare_my_account_rendering_values(**kwargs),
        )
        for header, value in self._FRAME_OPTIONS_HEADERS.items():
            response.headers[header] = value
        return response

    def _prepare_my_account_rendering_values(self, redirect="/my", **kwargs):
        return {
            **self._prepare_portal_layout_values(),
            **self._prepare_address_form_values(
                partner_sudo=request.env.user.partner_id,
                use_delivery_as_billing=True,
                callback=redirect,
            ),
            "page_name": "my_details",
        }

    @route("/my/addresses", type="http", auth="user", readonly=True, website=True)
    def my_addresses(self, **query_params):
        partner_sudo = request.env.user.partner_id
        query_params = self._filter_client_address_params(query_params)
        address_data = self._prepare_address_data(partner_sudo, **query_params)
        has_invoice_type_address = any(
            address.type == "invoice" for address in address_data["billing_addresses"]
        )
        all_addresses = (
            address_data["billing_addresses"] | address_data["delivery_addresses"]
        )
        values = {
            "partner_sudo": partner_sudo,
            **address_data,
            "editable_addresses": all_addresses._filter_editable_by_current_customer(
                **query_params
            ),
            "page_name": "my_addresses",
            "use_delivery_as_billing": not has_invoice_type_address,
            "address_url": "/my/address",
        }
        return request.render("portal.my_addresses", values)

    def _prepare_address_data(self, partner_sudo, /, **_kwargs):
        partner_sudo = partner_sudo.with_context(show_address=1)
        commercial_partner_sudo = partner_sudo.commercial_partner_id
        billing_partners_sudo = (
            partner_sudo.search(
                commercial_partner_sudo._get_domain_billing_address(),
                order="id desc",
            )
            | partner_sudo
        )
        delivery_partners_sudo = (
            partner_sudo.search(
                commercial_partner_sudo._get_domain_delivery_address(),
                order="id desc",
            )
            | partner_sudo
        )

        if partner_sudo != commercial_partner_sudo:
            if not self._is_billing_address_complete(commercial_partner_sudo):
                billing_partners_sudo -= commercial_partner_sudo
            if not self._is_delivery_address_complete(commercial_partner_sudo):
                delivery_partners_sudo -= commercial_partner_sudo

        return {
            "billing_addresses": billing_partners_sudo,
            "delivery_addresses": delivery_partners_sudo,
        }

    def _is_billing_address_complete(self, partner_sudo):
        mandatory_billing_fields = self._get_mandatory_billing_address_fields(
            partner_sudo.country_id
        )
        return self._has_all_address_fields(partner_sudo, mandatory_billing_fields)

    def _get_mandatory_billing_address_fields(self, country_sudo):
        return self._get_mandatory_address_form_fields(country_sudo)

    def _is_delivery_address_complete(self, partner_sudo):
        mandatory_delivery_fields = self._get_mandatory_delivery_address_fields(
            partner_sudo.country_id
        )
        return self._has_all_address_fields(partner_sudo, mandatory_delivery_fields)

    def _has_all_address_fields(self, partner_sudo, field_names):
        if not partner_sudo:
            return False
        return all(
            partner_sudo["phone_ids" if field_name == "phone" else field_name]
            for field_name in field_names
        )

    def _get_mandatory_delivery_address_fields(self, country_sudo):
        return self._get_mandatory_address_form_fields(country_sudo)

    def _get_mandatory_address_form_fields(self, country_sudo):
        base_fields = {"name", "email"}
        if not self._is_address_required():
            return base_fields
        base_fields.add("phone")
        return base_fields | self._get_mandatory_address_fields(country_sudo)

    def _is_address_required(self):
        return True

    def _get_mandatory_address_fields(self, country_sudo):
        field_names = {"street", "city", "country_id"}
        if country_sudo.state_required:
            field_names.add("state_id")
        if country_sudo.zip_required:
            field_names.add("zip")
        return field_names

    @route(
        "/my/address",
        type="http",
        methods=["GET"],
        auth="user",
        website=True,
        sitemap=False,
        readonly=True,
    )
    def portal_address(
        self,
        partner_id=None,
        address_type="billing",
        use_delivery_as_billing=False,
        **query_params,
    ):
        partner_sudo = (
            request.env["res.partner"]
            .with_context(show_address=1)
            .sudo()
            .browse(_parse_record_id(partner_id))
        )

        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer():
            _debug.logic(
                "address_form_refused", reason="not_editable", partner=partner_sudo.id
            )
            raise Forbidden

        _debug.pipeline(
            "address_form", partner=partner_sudo.id, address_type=address_type
        )
        query_params = self._filter_client_address_params(query_params)

        address_form_values = {
            **self._prepare_address_form_values(
                partner_sudo,
                address_type=address_type,
                use_delivery_as_billing=_parse_bool_param(use_delivery_as_billing),
                **query_params,
            ),
            "page_name": "address_form",
        }
        return request.render("portal.address_management", address_form_values)

    def _prepare_address_form_values(
        self,
        partner_sudo,
        address_type="billing",
        use_delivery_as_billing=False,
        callback="",
        **kwargs,
    ):
        callback = _parse_callback_url(callback, "")

        current_partner = request.env["res.partner"]._get_current_partner(**kwargs)
        commercial_partner = current_partner.commercial_partner_id

        if partner_sudo:
            state_id = partner_sudo.state_id.id
            country_sudo = partner_sudo.country_id
            can_edit_vat = partner_sudo.can_edit_vat()
        else:
            country_sudo = current_partner.country_id or self._get_default_country(
                **kwargs
            )
            state_id = current_partner.state_id.id
            can_edit_vat = not current_partner or (
                partner_sudo == current_partner and current_partner.can_edit_vat()
            )
        address_fields = (country_sudo and country_sudo.get_fields_address()) or [
            "city",
            "zip",
        ]

        return {
            "partner_sudo": partner_sudo,
            "partner_id": partner_sudo.id,
            "current_partner": current_partner,
            "commercial_partner": commercial_partner,
            "is_commercial_address": not current_partner
            or partner_sudo == commercial_partner,
            "is_main_address": not current_partner
            or (partner_sudo and partner_sudo == current_partner),
            "commercial_address_update_url": (
                current_partner == commercial_partner
                and "/my/account?redirect=/my/addresses"
            ),
            "address_type": address_type,
            "can_edit_vat": can_edit_vat,
            "can_edit_country": not partner_sudo.country_id
            or partner_sudo._can_edit_country(),
            "callback": callback,
            "country": country_sudo,
            "countries": request.env["res.country"].sudo().search([]),
            "is_used_as_billing": address_type == "billing" or use_delivery_as_billing,
            "use_delivery_as_billing": use_delivery_as_billing,
            "state_id": state_id,
            "country_states": country_sudo.state_ids,
            "zip_before_city": _is_zip_before_city(address_fields),
            "vat_label": request.env._("VAT"),
            "discard_url": callback or "/my/addresses",
        }

    def _get_default_country(self, **kwargs):
        return request.env.user.country_id

    @route(
        "/my/address/submit",
        type="http",
        methods=["POST"],
        auth="user",
        website=True,
        sitemap=False,
    )
    def portal_address_submit(self, partner_id=None, **form_data):
        partner_sudo = (
            request.env["res.partner"]
            .with_context(show_address=1)
            .sudo()
            .browse(_parse_record_id(partner_id))
        )
        if partner_sudo and not partner_sudo._can_be_edited_by_current_customer():
            _debug.logic(
                "address_submit_refused",
                reason="not_editable",
                partner=partner_sudo.id,
            )
            raise Forbidden

        form_data = self._filter_client_address_params(form_data)

        _partner_sudo, feedback_dict = self._create_or_update_address(
            partner_sudo, **form_data
        )

        return request.prepare_json_response(feedback_dict)

    def _create_or_update_address(
        self,
        partner_sudo,
        address_type="billing",
        use_delivery_as_billing=False,
        callback="/my/addresses",
        required_fields=False,
        verify_address_values=True,
        **form_data,
    ):
        if address_type not in ("billing", "delivery"):
            _debug.logic(
                "address_submit_refused",
                reason="bad_address_type",
                address_type=str(address_type),
            )
            raise BadRequest
        verify_address_values = verify_address_values is not False
        use_delivery_as_billing = _parse_bool_param(use_delivery_as_billing)
        callback = _parse_callback_url(callback, "/my/addresses")

        address_values, extra_form_data = self._parse_form_data(form_data)

        current_partner = request.env["res.partner"]._get_current_partner(
            **extra_form_data
        )
        if current_partner and partner_sudo != current_partner:
            # Company name is editable only on the main address, including at checkout.
            extra_form_data.pop("company_name", None)

        if verify_address_values:
            invalid_fields, missing_fields, error_messages = self._get_address_errors(
                address_values,
                partner_sudo,
                address_type,
                use_delivery_as_billing,
                required_fields or "",
                **extra_form_data,
            )
            if error_messages:
                return partner_sudo, {
                    "invalid_fields": list(invalid_fields | missing_fields),
                    "messages": error_messages,
                }

        if not partner_sudo:
            self._complete_address_values(
                address_values, address_type, use_delivery_as_billing, **form_data
            )
            create_context = clean_context(request.env.context)
            create_context.update(
                {
                    "tracking_disable": True,
                    "no_vat_validation": True,
                }
            )
            partner_sudo = (
                request.env["res.partner"]
                .sudo()
                .with_context(create_context)
                .create(self._resolve_address_phone_values(address_values))
            )
        elif not self._are_same_addresses(address_values, partner_sudo):
            if (address_values.get("name") or "").strip() == (
                partner_sudo.name or ""
            ).strip():
                address_values.pop("name", None)
            partner_sudo.write(
                self._resolve_address_phone_values(address_values, partner_sudo)
            )

        if company_name := (extra_form_data.get("company_name") or "").strip():
            commercial_partner = partner_sudo.commercial_partner_id
            if commercial_partner != partner_sudo and commercial_partner.is_company:
                if commercial_partner.name != company_name:
                    commercial_partner.name = company_name
            elif not partner_sudo.is_company:
                partner_sudo._create_parent_from_name(company_name)

        self._handle_extra_form_data(extra_form_data, address_values)

        return partner_sudo, {"redirectUrl": callback}

    def _parse_form_data(self, form_data):
        address_values = {}
        extra_form_data = {}
        if "zipcode" in form_data and not form_data.get("zip"):
            form_data = dict(form_data)
            form_data["zip"] = form_data.pop("zipcode")

        ResPartner = request.env["res.partner"]
        partner_fields = ResPartner._fields
        authorized_partner_fields = ResPartner._get_fields_frontend_writable()
        for key, value in form_data.items():
            if isinstance(value, str):
                value = value.strip()
            if key == "phone" and key in authorized_partner_fields:
                address_values[key] = value or False
            elif key in partner_fields and key in authorized_partner_fields:
                field = partner_fields[key]
                if (
                    field.type == "many2one"
                    and isinstance(value, str)
                    and value.isdigit()
                ):
                    address_values[key] = field.convert_to_cache(int(value), ResPartner)
                else:
                    address_values[key] = field.convert_to_cache(value, ResPartner)
            elif value:
                extra_form_data[key] = value

        return address_values, extra_form_data

    def _get_address_errors(
        self,
        address_values,
        partner_sudo,
        address_type,
        use_delivery_as_billing,
        required_fields,
        **kwargs,
    ):
        invalid_fields = set()
        missing_fields = set()
        error_messages = []

        is_commercial_address = self._is_commercial_address(partner_sudo, **kwargs)

        self._add_address_country_state_errors(
            address_values, partner_sudo, invalid_fields, error_messages
        )
        self._add_address_partner_mutation_errors(
            address_values,
            partner_sudo,
            is_commercial_address,
            invalid_fields,
            error_messages,
            **kwargs,
        )
        self._add_address_email_format_errors(
            address_values, invalid_fields, error_messages
        )
        self._add_address_vat_format_errors(
            address_values, invalid_fields, error_messages
        )
        self._add_address_required_field_errors(
            address_values,
            address_type,
            use_delivery_as_billing,
            required_fields,
            is_commercial_address,
            missing_fields,
            error_messages,
        )

        return invalid_fields, missing_fields, error_messages

    def _add_address_country_state_errors(
        self, address_values, partner_sudo, invalid_fields, error_messages
    ):
        country_id = address_values.get("country_id", partner_sudo.country_id.id)
        state_id = address_values.get("state_id", partner_sudo.state_id.id)
        country = request.env["res.country"].browse(country_id).exists()
        state = request.env["res.country.state"].browse(state_id).exists()
        if country_id and not country:
            invalid_fields.add("country_id")
            error_messages.append(_("Please select a valid country."))
        if state_id and not state:
            invalid_fields.add("state_id")
            error_messages.append(_("Please select a valid state."))
        elif state and country and state.country_id != country:
            invalid_fields.add("state_id")
            error_messages.append(
                _("The selected state does not belong to the selected country.")
            )

    def _is_commercial_address(self, partner_sudo, **kwargs):
        if partner_sudo:
            return partner_sudo == partner_sudo.commercial_partner_id
        return not request.env["res.partner"]._get_current_partner(**kwargs)

    def _add_address_partner_mutation_errors(
        self,
        address_values,
        partner_sudo,
        is_commercial_address,
        invalid_fields,
        error_messages,
        **kwargs,
    ):
        if not partner_sudo:
            return

        name_change = (
            "name" in address_values
            and partner_sudo.name
            and address_values["name"] != partner_sudo.name.strip()
        )
        country_change = (
            "country_id" in address_values
            and partner_sudo.country_id
            and address_values["country_id"] != partner_sudo.country_id.id
        )
        email_change = (
            "email" in address_values
            and partner_sudo.email
            and address_values["email"] != partner_sudo.email
        )

        if country_change and not partner_sudo._can_edit_country():
            invalid_fields.add("country_id")
            error_messages.append(
                _(
                    "Changing your country is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                )
            )

        if (name_change or email_change) and not all(
            partner_sudo.user_ids.mapped("share")
        ):
            if name_change:
                invalid_fields.add("name")
            if email_change:
                invalid_fields.add("email")
            error_messages.append(
                _(
                    "If you are ordering for an external person, please place your order via the"
                    " backend. If you wish to change your name or email address, please do so in"
                    " the account settings or contact your administrator."
                )
            )

        if not is_commercial_address:
            self._enforce_commercial_field_propagation(
                address_values, partner_sudo, invalid_fields, error_messages, **kwargs
            )
        elif (
            "vat" in address_values
            and partner_sudo.vat
            and address_values["vat"] != partner_sudo.vat
            and not partner_sudo.can_edit_vat()
        ):
            invalid_fields.add("vat")
            error_messages.append(
                _(
                    "Changing VAT number is not allowed once document(s) have been issued for your"
                    " account. Please contact us directly for this operation."
                )
            )

    def _enforce_commercial_field_propagation(
        self, address_values, partner_sudo, invalid_fields, error_messages, **kwargs
    ):
        for commercial_field_name in partner_sudo._commercial_fields():
            if commercial_field_name not in address_values:
                continue
            partner_sudo_field = partner_sudo._fields[commercial_field_name]
            partner_sudo_value = partner_sudo_field.convert_to_cache(
                partner_sudo[commercial_field_name],
                partner_sudo,
            )
            if partner_sudo_value != address_values[commercial_field_name] and (
                bool(partner_sudo_value) or bool(address_values[commercial_field_name])
            ):
                invalid_fields.add(commercial_field_name)
                field_description = partner_sudo_field._description_string(request.env)
                if partner_sudo.commercial_partner_id.is_company:
                    error_messages.append(
                        _(
                            "The %(field_name)s is managed on your company account.",
                            field_name=field_description,
                        )
                    )
                else:
                    error_messages.append(
                        _(
                            "The %(field_name)s is managed on your main account address.",
                            field_name=field_description,
                        )
                    )
            else:
                address_values.pop(commercial_field_name, None)

    def _add_address_email_format_errors(
        self, address_values, invalid_fields, error_messages
    ):
        if address_values.get("email") and not single_email_re.match(
            address_values["email"]
        ):
            invalid_fields.add("email")
            error_messages.append(
                _("Invalid Email! Please enter a valid email address.")
            )

    def _add_address_vat_format_errors(
        self, address_values, invalid_fields, error_messages
    ):
        ResPartnerSudo = request.env["res.partner"].sudo()
        if (
            address_values.get("vat")
            and hasattr(ResPartnerSudo, "_check_vat")
            and "vat" not in invalid_fields
            and "country_id" not in invalid_fields
        ):
            partner_dummy = ResPartnerSudo.new(
                {
                    fname: address_values[fname]
                    for fname in self._get_vat_validation_fields()
                    if fname in address_values
                }
            )
            try:
                partner_dummy._check_vat()
            except ValidationError as exception:
                invalid_fields.add("vat")
                error_messages.append(exception.args[0])

    def _add_address_required_field_errors(
        self,
        address_values,
        address_type,
        use_delivery_as_billing,
        required_fields,
        is_commercial_address,
        missing_fields,
        error_messages,
    ):
        required_field_set = {f for f in required_fields.split(",") if f}

        country_id = address_values.get("country_id")
        country = request.env["res.country"].browse(country_id).exists()
        if address_type == "delivery" or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_delivery_address_fields(country)
        if address_type == "billing" or use_delivery_as_billing:
            required_field_set |= self._get_mandatory_billing_address_fields(country)
            if not is_commercial_address:
                commercial_fields = (
                    request.env["res.partner"].sudo()._commercial_fields()
                )
                for fname in commercial_fields:
                    if fname in required_field_set and fname not in address_values:
                        required_field_set.remove(fname)

        address_fields = self._get_mandatory_address_fields(country)
        if any(address_values.get(fname) for fname in address_fields):
            required_field_set |= address_fields

        for field_name in required_field_set:
            if not address_values.get(field_name):
                missing_fields.add(field_name)
        if missing_fields:
            error_messages.append(_("Some required fields are empty."))

    def _get_vat_validation_fields(self):
        return {"country_id", "vat"}

    def _complete_address_values(
        self, address_values, address_type, use_delivery_as_billing, **kwargs
    ):
        address_values["lang"] = request.lang.code
        partner = request.env["res.partner"]._get_current_partner(**kwargs)
        address_values["company_id"] = partner.company_id.id
        commercial_partner = partner.commercial_partner_id
        if use_delivery_as_billing:
            address_values["type"] = "other"
        elif address_type == "billing":
            address_values["type"] = "invoice"
        elif address_type == "delivery":
            address_values["type"] = "delivery"

        if commercial_partner.active:
            address_values["parent_id"] = commercial_partner.id

    def _are_same_addresses(self, address_values, partner):
        ResPartner = request.env["res.partner"]
        for key, new_val in address_values.items():
            if key == "phone":
                val = partner._phone_get_number().number or False
            else:
                val = ResPartner._fields[key].convert_to_cache(partner[key], ResPartner)
            if new_val != val and (val or new_val):
                return False
        return True

    def _resolve_address_phone_values(self, address_values, partner_sudo=None):
        """Resolve/create the shared number and select it for this contact.

        Called after address validation; number creation and the ensuing partner
        write belong to the same request transaction.
        """
        if "phone" not in address_values:
            return address_values
        values = dict(address_values)
        phone = values.pop("phone")
        partner = (
            partner_sudo
            if partner_sudo is not None
            else request.env["res.partner"].sudo()
        )
        current = partner._phone_get_number()
        if phone == (current.number if current else False):
            return values
        number = partner.env["phone.number"].sudo()
        if phone:
            number = number.create(
                {
                    "number": phone,
                    "type": current.type if current else "mobile",
                }
            )
        values.update(partner._prepare_phone_replacement_vals(number))
        return values

    def _handle_extra_form_data(self, extra_form_data, address_values):
        pass

    @route(
        '/my/address/country_info/<model("res.country"):country>',
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        readonly=True,
    )
    def portal_address_country_info(self, country, address_type, **kw):
        address_fields = country.get_fields_address()
        if address_type == "billing":
            required_fields = self._get_mandatory_billing_address_fields(country)
        else:
            required_fields = self._get_mandatory_delivery_address_fields(country)
        return {
            "fields": address_fields,
            "zip_before_city": _is_zip_before_city(address_fields),
            "states": [(st.id, st.name, st.code) for st in country.sudo().state_ids],
            "state_required": country.state_required,
            "phone_code": country.phone_code,
            "required_fields": list(required_fields),
        }

    @route(
        "/my/address/archive",
        type="jsonrpc",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def address_archive(self, partner_id):
        address_sudo = (
            request.env["res.partner"]
            .sudo()
            .browse(_parse_record_id(partner_id))
            .exists()
        )
        if not address_sudo or not address_sudo._can_be_edited_by_current_customer():
            _debug.logic("address_archive_refused", reason="not_editable")
            raise Forbidden

        if address_sudo == request.env.user.partner_id:
            _debug.logic("address_archive_refused", reason="main_address")
            raise UserError(_("You cannot archive your main address"))

        _debug.lifecycle("address_archived", partner=address_sudo.id)
        address_sudo.action_archive()

    @route(
        "/my/security", type="http", auth="user", website=True, methods=["GET", "POST"]
    )
    def security(self, **post):
        values = self._prepare_security_rendering_values()

        if request.httprequest.method == "POST":
            values.update(
                self._update_password(
                    _as_password_field(post.get("old")),
                    _as_password_field(post.get("new1")),
                    _as_password_field(post.get("new2")),
                )
            )

        return request.render(
            "portal.portal_my_security",
            values,
            headers=self._FRAME_OPTIONS_HEADERS,
        )

    def _prepare_security_rendering_values(self):
        values = self._prepare_portal_layout_values()
        values["get_error"] = get_error
        values["allow_api_keys"] = str2bool(
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("portal.allow_api_keys"),
            default=False,
        )
        values["open_deactivate_modal"] = False
        return values

    def _update_password(self, old, new1, new2):
        for k, v in [("old", old), ("new1", new1), ("new2", new2)]:
            if not v:
                _debug.logic("password_change_refused", reason="empty", field=k)
                return {
                    "errors": {
                        "password": {k: _("You cannot leave any password empty.")}
                    }
                }

        if new1 != new2:
            _debug.logic("password_change_refused", reason="mismatch")
            return {
                "errors": {
                    "password": {
                        "new2": _(
                            "The new password and its confirmation must be identical."
                        )
                    }
                }
            }

        try:
            request.env["res.users"].change_password(old, new1)
        except AccessDenied as e:
            msg = e.args[0]
            if msg == AccessDenied().args[0]:
                msg = _(
                    "The old password you provided is incorrect, your password was not changed."
                )
            _debug.logic("password_change_refused", reason="access_denied")
            return {"errors": {"password": {"old": msg}}}
        except UserError as e:
            _debug.logic("password_change_refused", reason="user_error")
            return {"errors": {"password": str(e)}}

        new_token = request.env.user._get_session_token(request.session.sid)
        request.session.session_token = new_token

        _debug.lifecycle("password_changed", user=request.env.uid)
        return {"success": {"password": True}}

    @route(
        "/my/deactivate_account",
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def deactivate_account(self, validation, password, **post):
        values = self._prepare_security_rendering_values()
        values["open_deactivate_modal"] = True
        credential = {
            "login": request.env.user.login,
            "password": password,
            "type": "password",
        }

        if validation != request.env.user.login:
            _debug.logic(
                "deactivate_refused", reason="login_mismatch", user=request.env.uid
            )
            values["errors"] = {"deactivate": "validation"}
        else:
            try:
                request.env.user._check_credentials(credential, {"interactive": True})
                _debug.lifecycle("portal_user_deactivated", user=request.env.uid)
                request.env.user.sudo()._deactivate_portal_user(**post)
                request.session.logout()
                return request.redirect(
                    f"/web/login?message={quote(_('Account deleted!'), safe='/:')}"
                )
            except AccessDenied:
                _debug.logic("deactivate_refused", reason="bad_password")
                values["errors"] = {"deactivate": "password"}
            except UserError as e:
                _debug.logic("deactivate_refused", reason="user_error")
                values["errors"] = {"deactivate": {"other": str(e)}}

        return request.render(
            "portal.portal_my_security",
            values,
            headers=self._FRAME_OPTIONS_HEADERS,
        )

    @route("/portal/attachment/remove", type="jsonrpc", auth="public")
    def attachment_remove(self, attachment_id, access_token=None):
        try:
            attachment_sudo = self._document_check_access(
                "ir.attachment", int(attachment_id), access_token=access_token
            )
        except AccessError, MissingError, TypeError, ValueError:
            _debug.logic("attachment_remove_refused", reason="no_access")
            raise UserError(
                _(
                    "The attachment does not exist or you do not have the rights to access it."
                )
            ) from None

        if (
            attachment_sudo.res_model != "mail.compose.message"
            or attachment_sudo.res_id != 0
        ):
            _debug.logic(
                "attachment_remove_refused",
                reason="not_pending",
                attachment=attachment_sudo.id,
                model=attachment_sudo.res_model,
            )
            raise UserError(
                _(
                    "The attachment %s cannot be removed because it is not in a pending state.",
                    attachment_sudo.name,
                )
            )

        if attachment_sudo.env["mail.message"].search_count(
            [("attachment_ids", "in", attachment_sudo.ids)], limit=1
        ):
            _debug.logic(
                "attachment_remove_refused",
                reason="linked_to_message",
                attachment=attachment_sudo.id,
            )
            raise UserError(
                _(
                    "The attachment %s cannot be removed because it is linked to a message.",
                    attachment_sudo.name,
                )
            )

        _debug.lifecycle("attachment_removed", attachment=attachment_sudo.id)
        return attachment_sudo.unlink()

    def _document_check_access(self, model_name, document_id, access_token=None):
        document = request.env[model_name].browse(document_id)
        document_sudo = document.with_user(SUPERUSER_ID).exists()
        if not document_sudo:
            _debug.logic(
                "document_access",
                verdict="missing",
                model=model_name,
                record=document_id,
            )
            raise MissingError(_("This document does not exist."))
        try:
            document.check_access("read")
        except AccessError:
            stored_token = (
                document_sudo.access_token
                if "access_token" in document_sudo._fields
                else None
            )
            if (
                not access_token
                or not isinstance(access_token, str)
                or not stored_token
                or not consteq(stored_token, access_token)
            ):
                _debug.logic(
                    "document_access",
                    verdict="refused",
                    model=model_name,
                    record=document_id,
                    token_supplied=bool(access_token),
                )
                raise
            _debug.logic(
                "document_access",
                verdict="by_token",
                model=model_name,
                record=document_id,
            )
        return document_sudo

    def _get_page_view_values(
        self,
        document,
        access_token,
        values,
        session_history,
        no_breadcrumbs,
        /,
        **kwargs,
    ):
        values["object"] = document

        if access_token:
            values["no_breadcrumbs"] = no_breadcrumbs
            values["access_token"] = access_token
            values["token"] = access_token

        if kwargs.get("error"):
            values["error"] = kwargs["error"]
        if kwargs.get("warning"):
            values["warning"] = kwargs["warning"]
        if kwargs.get("success"):
            values["success"] = kwargs["success"]
        if kwargs.get("pid"):
            values["pid"] = kwargs["pid"]
        if kwargs.get("hash"):
            values["hash"] = kwargs["hash"]

        history = request.session.get(session_history, [])
        values.update(
            get_records_pager(history, document, with_token=bool(access_token))
        )

        return values

    def _show_report(self, model, report_type, report_ref, download=False):
        if report_type not in ("html", "pdf", "text"):
            _debug.logic(
                "report_refused", reason="bad_type", report_type=str(report_type)
            )
            raise UserError(_("Invalid report type: %s", report_type))

        ReportAction = request.env["ir.actions.report"].sudo()

        if "company_id" in model._fields:
            if len(model.company_id) > 1:
                _debug.logic(
                    "report_refused", reason="multi_company", model=model._name
                )
                raise UserError(_("Multi company reports are not supported."))
            ReportAction = ReportAction.with_company(model.company_id)

        method_name = f"_render_qweb_{report_type}"
        with _debug.perf(
            "portal_report_rendered",
            cr=request.env.cr,
            report=report_ref,
            report_type=report_type,
            records=len(model),
        ):
            report = getattr(ReportAction, method_name)(
                report_ref, list(model.ids), data={"report_type": report_type}
            )[0]
        headers = self._get_http_headers(model, report_type, report, download)
        return request.prepare_response(report, headers=list(headers.items()))

    _REPORT_CONTENT_TYPES = {
        "pdf": "application/pdf",
        "html": "text/html",
        "text": "text/plain",
    }

    def _get_http_headers(self, model, report_type, report, download):
        headers = {
            "Content-Type": self._REPORT_CONTENT_TYPES.get(report_type, "text/html"),
            "Content-Length": (
                len(report)
                if isinstance(report, bytes)
                else len(report.encode("utf-8"))
            ),
        }
        if report_type == "pdf":
            filename = f"{re.sub(r'\W+', '_', model._get_report_base_filename())}.pdf"
            headers["Content-Disposition"] = prepare_content_disposition_header(
                filename, disposition_type="attachment" if download else "inline"
            )
        return headers


def get_error(e, path=""):
    for k in path.split(".") if path else []:
        if not isinstance(e, dict):
            return None
        e = e.get(k)

    return e if isinstance(e, str) else None
