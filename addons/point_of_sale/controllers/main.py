import json
from datetime import date, timedelta

from psycopg.errors import UniqueViolation

from odoo import _, fields, http
from odoo.exceptions import LockError
from odoo.http import request
from odoo.tools import escape_psql, file_open, format_amount, str2bool

from ..tools import debug_log as dbg
from odoo.addons.account.controllers.portal import PortalAccount

_POS_MENU_URL = "/odoo/action-point_of_sale.action_client_pos_menu"


class PosController(PortalAccount):
    @http.route("/pos/service-worker.js", type="http", auth="user")
    def pos_web_service_worker(self):
        return request.prepare_response(
            self._get_pos_service_worker(),
            [
                ("Content-Type", "text/javascript"),
                ("Service-Worker-Allowed", "/pos"),
            ],
        )

    def _get_pos_service_worker(self):
        with file_open("point_of_sale/static/src/app/service_worker.js") as f:
            return f.read()

    @http.route(["/pos/web", "/pos/ui"], type="http", auth="user")
    def old_pos_web(self, config_id=False, from_backend=False, **k):
        return self.pos_web(config_id, from_backend, **k)

    @http.route(
        ["/pos/ui/<config_id>", "/pos/ui/<config_id>/<path:subpath>"],
        auth="user",
        type="http",
    )
    def pos_web(self, config_id=False, from_backend=False, subpath=None, **k):
        is_internal_user = request.env.user._is_internal()
        dbg.lifecycle.debug(
            "[http] /pos/ui config=%s uid=%s from_backend=%s subpath=%s internal=%s",
            config_id,
            request.session.uid,
            from_backend,
            subpath,
            is_internal_user,
        )
        if not is_internal_user:
            return request.prepare_not_found_error()
        if not request.env.user.has_group("point_of_sale.group_pos_user"):
            dbg.logic.debug("[http] /pos/ui: not a pos user, redirect to menu")
            return request.redirect(_POS_MENU_URL)
        if config_id:
            try:
                config_id = int(config_id)
            except TypeError, ValueError:
                return request.prepare_not_found_error()
        pos_config = request.env["pos.config"].sudo().browse(config_id).exists()
        if (
            not pos_config
            or not pos_config.active
            or pos_config.company_id not in request.env.user.company_ids
        ):
            dbg.logic.debug(
                "[http] /pos/ui config=%s unavailable, inactive, or outside user companies",
                config_id,
            )
            return request.redirect(_POS_MENU_URL)
        pos_config = pos_config.with_company(pos_config.company_id)
        pos_session = pos_config.current_session_id

        dbg.logic.debug(
            "[http] /pos/ui config=%s active=%s has_active_session=%s session=%s",
            pos_config.id,
            pos_config.active,
            pos_config.has_active_session,
            dbg.rec(pos_session),
        )
        if pos_config.has_active_session and (
            not pos_session or pos_session.state not in ("opening_control", "opened")
        ):
            return request.redirect(_POS_MENU_URL)

        if not pos_config.has_active_session:
            try:
                with request.env.cr.savepoint():
                    pos_config.lock_for_update()
                    pos_config.open_ui()
            except LockError:
                dbg.logic.debug(
                    "[http] /pos/ui config %s locked by another opener", pos_config.id
                )
                return request.redirect(_POS_MENU_URL)
            except UniqueViolation as exc:
                if exc.diag.constraint_name != "pos_session_open_per_config_uniq":
                    raise
                # A committed opener can be invisible to this request's snapshot.
                dbg.logic.debug(
                    "[http] /pos/ui config %s opened after this request's snapshot",
                    pos_config.id,
                )
                return request.redirect(_POS_MENU_URL)
            pos_session = pos_config.current_session_id
            dbg.pipeline.debug(
                "[http] /pos/ui opened session %s on config %s",
                dbg.rec(pos_session),
                pos_config.id,
            )

        company = pos_session.company_id
        session_info = request.env["ir.http"].session_info()
        allowed_companies = session_info["user_companies"]["allowed_companies"]
        if company.id not in allowed_companies:
            dbg.logic.debug(
                "[http] /pos/ui company %s not in allowed %s",
                company.id,
                list(allowed_companies),
            )
            return request.redirect(_POS_MENU_URL)
        session_info["user_context"]["allowed_company_ids"] = company.ids
        session_info["user_companies"] = {
            "current_company": company.id,
            "allowed_companies": {company.id: allowed_companies[company.id]},
        }
        session_info["nomenclature_id"] = pos_session.company_id.nomenclature_id.id
        session_info["fallback_nomenclature_id"] = (
            pos_session.config_id.fallback_nomenclature_id.id
        )
        use_lna = pos_session.env["ir.config_parameter"].get_param_bool(
            "point_of_sale.use_lna"
        )
        context = {
            "from_backend": int(str2bool(from_backend, default=False)),
            "use_pos_fake_tours": str2bool(k.get("tours", False), default=False),
            "session_info": session_info,
            "pos_session_id": pos_session.id,
            "pos_config_id": pos_session.config_id.id,
            "access_token": pos_session.config_id.access_token,
            "last_data_change": pos_session.config_id.last_data_change.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "urls_to_cache": json.dumps(
                pos_config._get_urls_to_cache(request.session.debug)
            ),
            "use_lna": use_lna,
        }
        dbg.pipeline.debug(
            "[http] /pos/ui rendering session=%s config=%s company=%s lna=%s",
            pos_session.id,
            pos_session.config_id.id,
            company.id,
            use_lna,
        )
        response = request.render("point_of_sale.index", context)
        response.headers["Cache-Control"] = "no-store"
        return response

    @http.route(["/pos/ping"], type="jsonrpc", auth="user")
    def pos_ping(self):
        return {"response": "pong"}

    @http.route("/pos/sale_details_report", type="http", auth="user")
    def print_sale_details(self, date_start=False, date_stop=False, **kw):
        if not request.env.user.has_group("point_of_sale.group_pos_manager"):
            return request.prepare_not_found_error()
        with dbg.timer(
            request.env, "[http] sale_details_report %s..%s", date_start, date_stop
        ):
            pdf, _ = request.env["ir.actions.report"]._render_qweb_pdf(
                "point_of_sale.sale_details_report",
                data={"date_start": date_start, "date_stop": date_stop},
            )
        pdfhttpheaders = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf)),
        ]
        return request.prepare_response(pdf, headers=pdfhttpheaders)

    @staticmethod
    def _parse_ticket_date(value):
        try:
            ticket_date = date.fromisoformat(value)
        except TypeError, ValueError:
            return None
        # The lookup includes the previous day and the following two days.
        if date.min < ticket_date <= date.max - timedelta(days=2):
            return ticket_date
        return None

    @http.route(
        ["/pos/ticket"], type="http", auth="public", website=True, sitemap=False
    )
    def invoice_request_screen(self, **kwargs):
        errors = {}
        form_values = {}
        dbg.lifecycle.debug(
            "[http] /pos/ticket %s keys=%s",
            request.httprequest.method,
            dbg.keys(kwargs),
        )
        if request.httprequest.method == "POST":
            for field in ["pos_reference", "date_order", "ticket_code"]:
                if not kwargs.get(field):
                    errors[field] = " "
                else:
                    form_values[field] = kwargs[field].strip()
                    if not form_values[field]:
                        errors[field] = " "

            date_order = None
            if not errors:
                date_order = fields.Datetime.to_datetime(
                    self._parse_ticket_date(form_values["date_order"])
                )
                if not date_order:
                    errors["date_order"] = " "

            if errors:
                errors["generic"] = _("Please fill all the required fields.")
            elif len(form_values["pos_reference"]) < 12:
                errors["pos_reference"] = _(
                    "The Ticket Number should be at least 12 characters long."
                )
            else:
                order = (
                    request.env["pos.order"]
                    .sudo()
                    .search(
                        [
                            (
                                "pos_reference",
                                "=like",
                                "%" + escape_psql(form_values["pos_reference"]),
                            ),
                            ("date_order", ">=", date_order - timedelta(days=1)),
                            ("date_order", "<", date_order + timedelta(days=2)),
                            ("ticket_code", "=", form_values["ticket_code"]),
                        ],
                        limit=1,
                    )
                )
                dbg.logic.debug(
                    "[http] /pos/ticket lookup ref=%s date=%s -> %s",
                    form_values["pos_reference"],
                    date_order,
                    dbg.rec(order),
                )
                if order:
                    return request.redirect(
                        "/pos/ticket/validate?access_token=%s" % (order.access_token)
                    )
                else:
                    errors["generic"] = _("No sale order found.")

        elif request.httprequest.method == "GET":
            if kwargs.get("order_uuid"):
                order = (
                    self.env["pos.order"]
                    .sudo()
                    .search([("uuid", "=", kwargs["order_uuid"])], limit=1)
                )
                if order:
                    return request.redirect(
                        "/pos/ticket/validate?access_token=%s" % (order.access_token)
                    )

        return request.render(
            "point_of_sale.ticket_request_with_code",
            {
                "errors": errors,
                "banner_error": " ".join(errors.values()),
                "form_values": form_values,
            },
        )

    @http.route(
        ["/pos/ticket/validate"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def show_ticket_validation_screen(self, access_token="", **kwargs):
        kwargs = self._filter_client_address_params(kwargs)

        if not access_token:
            return request.prepare_not_found_error()
        pos_order = (
            request.env["pos.order"]
            .sudo()
            .search([("access_token", "=", access_token)], limit=1)
        )
        dbg.lifecycle.debug(
            "[http] /pos/ticket/validate %s order=%s state=%s invoiced=%s",
            request.httprequest.method,
            dbg.rec(pos_order),
            pos_order.state if pos_order else None,
            bool(pos_order.account_move) if pos_order else None,
        )
        if not pos_order:
            return request.prepare_not_found_error()

        if pos_order.state not in ("paid", "done"):
            return request.prepare_not_found_error()

        pos_order = pos_order.with_company(pos_order.company_id).with_context(
            allowed_company_ids=pos_order.company_id.ids
        )

        if pos_order.account_move and pos_order.account_move.is_sale_document():
            return self._redirect_to_invoice(pos_order.account_move)

        if not request.env["res.company"]._with_locked_records(
            pos_order, allow_raising=False
        ):
            dbg.logic.debug(
                "[order:%s] ticket validation: order locked", pos_order.uuid
            )
            return request.prepare_response(
                _("Some orders are already being invoiced. Please try again later."),
                status=409,
                headers=[
                    ("Retry-After", "1"),
                    ("Content-Type", "text/plain; charset=utf-8"),
                ],
            )

        pos_order_country = (
            pos_order.company_id.account_config_id.account_fiscal_country_id
        )
        additional_partner_fields = request.env[
            "res.partner"
        ].get_partner_localisation_fields_required_to_invoice(pos_order_country)
        additional_invoice_fields = request.env[
            "account.move"
        ].get_invoice_localisation_fields_required_to_invoice(pos_order_country)

        user_is_connected = not request.env.user._is_public()

        form_values = {"extra_field_values": {}}
        partner = (
            user_is_connected and request.env.user.partner_id
        ) or pos_order.partner_id
        if kwargs and request.httprequest.method == "POST":
            partner_values, prefixed_partner_values, invalid_fields, error_messages = (
                self._parse_ticket_extra_fields(
                    additional_partner_fields, "partner_", kwargs
                )
            )
            form_values["extra_field_values"].update(prefixed_partner_values)
            (
                invoice_values,
                prefixed_invoice_values,
                invalid_invoice_fields,
                invoice_errors,
            ) = self._parse_ticket_extra_fields(
                additional_invoice_fields, "invoice_", kwargs
            )
            form_values["extra_field_values"].update(prefixed_invoice_values)
            invalid_fields |= invalid_invoice_fields
            error_messages += invoice_errors
            address_relations, invalid_address_fields, address_errors = (
                self._parse_ticket_address_relations(kwargs)
            )
            kwargs.update(address_relations)
            invalid_fields |= invalid_address_fields
            error_messages += address_errors
            dbg.logic.debug(
                "[order:%s] ticket form: partner=%s connected=%s invalid=%s",
                pos_order.uuid,
                dbg.rec(partner) if partner else None,
                user_is_connected,
                sorted(invalid_fields),
            )
            if not invalid_fields:
                address_values = (
                    self._get_ticket_address_values(partner)
                    if user_is_connected
                    else {}
                )
                partner, feedback_dict = self._create_or_update_address(
                    partner, **(address_values | kwargs | partner_values)
                )
                dbg.logic.debug(
                    "[order:%s] ticket address validation: invalid=%s",
                    pos_order.uuid,
                    feedback_dict.get("invalid_fields", []),
                )
                form_values.update(feedback_dict)
            form_values.update(
                {
                    "invalid_fields": form_values.get("invalid_fields", [])
                    + list(invalid_fields),
                    "messages": form_values.get("messages", []) + error_messages,
                }
            )
            if not form_values.get("invalid_fields"):
                return self._invoice_order_and_redirect(
                    partner, invoice_values, pos_order
                )

        elif user_is_connected and not (
            additional_partner_fields or additional_invoice_fields
        ):
            return self._invoice_order_and_redirect(partner, {}, pos_order)

        if partner:
            if additional_partner_fields:
                defaults = {
                    "partner_" + field.name: (
                        partner[field.name].id
                        if field.ttype == "many2one"
                        else partner[field.name]
                    )
                    for field in additional_partner_fields
                }
                form_values["extra_field_values"] = (
                    defaults | form_values["extra_field_values"]
                )

            if not partner.country_id or not partner.street:
                form_values["partner_address"] = False
            else:
                form_values["partner_address"] = partner._display_address()

        return request.render(
            "point_of_sale.ticket_validation_screen",
            {
                **self._get_ticket_address_form_values(
                    partner, pos_order_country, kwargs
                ),
                "partner": partner,
                "address_url": f"/my/account?redirect=/pos/ticket/validate?access_token={access_token}",
                "user_is_connected": user_is_connected,
                "format_amount": format_amount,
                "env": request.env,
                "pos_order": pos_order,
                "invoice_required_fields": additional_invoice_fields,
                "partner_required_fields": additional_partner_fields,
                "access_token": access_token,
                "invoice_sending_methods": {"email": _("by Email")},
                **form_values,
            },
        )

    def _parse_ticket_address_relations(self, form_data):
        relation_fields = [
            request.env["ir.model.fields"]._get("res.partner", name)
            for name in ("country_id", "state_id")
            if form_data.get(name)
        ]
        values, _submitted, invalid_fields, messages = self._parse_ticket_extra_fields(
            relation_fields, "", dict(form_data)
        )
        return values, invalid_fields, messages

    def _get_ticket_address_form_values(self, partner, fiscal_country, form_data):
        values = self._prepare_address_form_values(partner, **form_data)
        country = values["country"] or fiscal_country
        submitted = {}
        if request.httprequest.method == "POST":
            submitted = {
                name: form_data[name]
                for name in (
                    "name",
                    "email",
                    "phone",
                    "company_name",
                    "vat",
                    "street",
                    "street2",
                    "city",
                    "zip",
                    "country_id",
                    "state_id",
                )
                if name in form_data
            }
            if "zipcode" in form_data and "zip" not in submitted:
                submitted["zip"] = form_data["zipcode"]
            if "country_id" in submitted:
                try:
                    country_id = int(submitted["country_id"])
                except TypeError, ValueError:
                    country_id = False
                country = request.env["res.country"].sudo().browse(country_id).exists()
        address_fields = country.get_fields_address() if country else ["city", "zip"]
        values.update(
            submitted_address=submitted,
            country=country,
            country_states=country.state_ids,
            zip_before_city=(
                "zip" in address_fields
                and address_fields.index("zip") < address_fields.index("city")
            ),
        )
        return values

    def _get_ticket_address_values(self, partner):
        values = {
            name: partner[name]
            for name in ("name", "email", "street", "street2", "city", "zip")
        }
        values["phone"] = partner.phone_ids._primary().number or False
        values.update(country_id=partner.country_id.id, state_id=partner.state_id.id)
        return values

    def _parse_ticket_extra_fields(self, required_fields, prefix, form_data):
        values, submitted_values = {}, {}
        invalid_fields, messages = set(), []
        for field in required_fields:
            key = prefix + field.name
            is_submitted = key in form_data
            value = form_data.pop(key, "")
            if isinstance(value, str):
                value = value.strip()
            if is_submitted:
                submitted_values[key] = value
            if not value:
                invalid_fields.add(field.name)
                messages.append(
                    _("The field %s must be filled.", field.field_description.lower())
                )
                continue
            try:
                values[field.name] = self._parse_ticket_field_value(field, value)
                submitted_values[key] = values[field.name]
            except TypeError, ValueError:
                invalid_fields.add(field.name)
                messages.append(
                    _(
                        "Please select a valid value for %s.",
                        field.field_description.lower(),
                    )
                )
        return values, submitted_values, invalid_fields, messages

    def _parse_ticket_field_value(self, field, value):
        model_field = request.env[field.model]._fields[field.name]
        if field.ttype == "many2one":
            record_id = int(value)
            if (
                record_id <= 0
                or not request.env[model_field.comodel_name]
                .sudo()
                .browse(record_id)
                .exists()
            ):
                raise ValueError("Missing related record")
            return record_id
        if field.ttype == "selection":
            choices = {
                str(key): key
                for key, label in model_field._description_selection(request.env)
            }
            if str(value) not in choices:
                raise ValueError("Invalid selection")
            return choices[str(value)]
        return value

    def _invoice_order_and_redirect(self, partner, invoice_values, pos_order):
        dbg.pipeline.debug(
            "[order:%s] portal invoice request: partner=%s extra=%s",
            pos_order.uuid,
            dbg.rec(partner),
            dbg.keys(invoice_values),
        )

        pos_order.partner_id = partner
        pos_order.with_context(
            pos_ticket_invoice_values=invoice_values
        ).action_pos_order_invoice()
        return self._redirect_to_invoice(pos_order.account_move)

    def _redirect_to_invoice(self, invoice):
        return request.redirect(
            "/my/invoices/%s?access_token=%s"
            % (invoice.id, invoice._portal_get_or_create_token())
        )
