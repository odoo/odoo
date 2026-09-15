import base64
import logging
import re

import psycopg
from markupsafe import Markup
from psycopg import IntegrityError
from werkzeug.exceptions import BadRequest

from odoo import SUPERUSER_ID, Command, http
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.text import nl2br, nl2br_enclose
from odoo.tools import plaintext2html
from odoo.tools.misc import consteq, hmac
from odoo.tools.translate import LazyTranslate, _

from ..tools import website_form_signature_payload

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class WebsiteForm(http.Controller):
    @http.route(
        "/website/form",
        type="http",
        auth="public",
        methods=["POST"],
        multilang=False,
        readonly=True,
    )
    def website_form_empty(self, **kwargs):
        return ""

    @http.route(
        "/website/form/<string:model_name>",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
        captcha="website_form",
    )
    def website_form(self, model_name, **kwargs):  # noqa: E8528 - a visitor's form; a signed-in session's CSRF token is checked in the body
        csrf_token = request.params.pop("csrf_token", None)
        if request.session.uid and not request.is_valid_csrf(csrf_token):
            _debug.logic("form_refused", reason="invalid_csrf", model=model_name)
            raise BadRequest("Session expired (invalid CSRF token)")
        _debug.pipeline("form_submitted", model=model_name, fields=sorted(kwargs))

        try:
            with request.env.cr.savepoint() as sp:
                kwargs = dict(request.params)
                kwargs.pop("model_name")
                res = self._handle_website_form(model_name, **kwargs)
                try:
                    sp.close(rollback=False)
                except psycopg.errors.InvalidSavepointSpecification:
                    sp.closed = True
                return res
        except (ValidationError, UserError) as e:
            _debug.logic("form_refused", reason="validation", model=model_name)
            return request.prepare_json_response(
                {
                    "error": e.args[0],
                }
            )
        except IntegrityError:
            _debug.logic("form_refused", reason="integrity_error", model=model_name)
            return request.prepare_json_response(False)

    def _handle_website_form(self, model_name, **kwargs):
        model_record = (
            request.env["ir.model"]
            .sudo()
            .search([("model", "=", model_name), ("website_form_access", "=", True)])
        )
        if not model_record:
            _debug.logic(
                "form_refused", reason="model_not_form_enabled", model=model_name
            )
            return request.prepare_json_response(
                {"error": _("The form's specified model does not exist")}
            )

        if model_name == "mail.mail":
            signature = kwargs.get("website_form_signature", "")
            extra_recipients = {
                name: kwargs.get(name) or ""
                for name in ("email_cc", "email_bcc")
                if name in kwargs
            }
            value = website_form_signature_payload(
                kwargs.get("email_to"), extra_recipients
            )
            hash_value = hmac(model_record.env, "website_form_signature", value)
            if not consteq(signature, hash_value):
                _logger.debug("Rejected website mail form before record creation")
                _debug.logic(
                    "form_refused",
                    reason="bad_mail_signature",
                    recipients=sorted(extra_recipients),
                )
                raise AccessDenied(self.env._("invalid website_form_signature"))

        try:
            data = self.extract_data(model_record, kwargs)
        except ValidationError as e:
            _debug.logic(
                "form_refused",
                reason="field_errors",
                model=model_name,
                fields=e.args[0],
            )
            return request.prepare_json_response({"error_fields": e.args[0]})

        id_record = self.create_record(
            request,
            model_record,
            data["record"],
            data["custom"],
            data.get("meta"),
        )
        if id_record:
            self.create_attachments(model_record, id_record, data["attachments"])

            if model_name == "mail.mail":
                request.env[model_name].sudo().browse(id_record).send()

        request.session["form_builder_model_model"] = model_record.model
        request.session["form_builder_model"] = model_record.name
        request.session["form_builder_id"] = id_record

        _debug.lifecycle(
            "form_record_created",
            model=model_name,
            record=id_record,
            attachments=len(data["attachments"]),
        )
        return request.prepare_json_response({"id": id_record})

    _meta_label = _lt("Metadata")

    def identity(self, field_label, field_input):
        return field_input

    def integer(self, field_label, field_input):
        return int(field_input)

    def floating(self, field_label, field_input):
        return float(field_input)

    def html(self, field_label, field_input):
        return plaintext2html(field_input)

    def boolean(self, field_label, field_input):
        return bool(field_input)

    def binary(self, field_label, field_input):
        return base64.b64encode(field_input.read())

    def one2many(self, field_label, field_input):
        return [int(i) for i in field_input.split(",")]

    def many2many(self, field_label, field_input, *args):
        return [
            (args[0] if args else (6, 0)) + (self.one2many(field_label, field_input),)
        ]

    def tags(self, field_label, field_input):
        return [
            tag.replace("\\,", ",").replace("\\\\", "\\")
            for tag in re.split(r"(?<!\\),", field_input)
        ]

    _input_filters = {
        "char": identity,
        "text": identity,
        "html": html,
        "date": identity,
        "datetime": identity,
        "many2one": integer,
        "one2many": one2many,
        "many2many": many2many,
        "selection": identity,
        "boolean": boolean,
        "integer": integer,
        "float": floating,
        "binary": binary,
        "monetary": floating,
        "tags": tags,
    }

    def _extract_authorized_field(self, data, authorized_fields, field_name, value):
        if "_property" in authorized_fields[field_name]:
            field_data = authorized_fields[field_name]
            properties_field_name = field_data["_property"]["field"]
            del field_data["_property"]
            properties = data["record"].setdefault(properties_field_name, [])
            property_type = authorized_fields[field_name]["type"]
            filter_type = "one2many" if property_type == "many2many" else property_type
            field_data["value"] = self._input_filters[filter_type](
                self, field_name, value
            )
            properties.append(field_data)
            return
        input_filter = self._input_filters[authorized_fields[field_name]["type"]]
        data["record"][field_name] = input_filter(self, field_name, value)

    def _extract_request_metadata(self):
        if not (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("website_form_enable_metadata")
        ):
            return ""
        environ = request.httprequest.headers.environ
        _debug.logic("form_metadata_collected")
        return "%s : %s\n%s : %s\n%s : %s\n%s : %s\n" % (
            "IP",
            environ.get("REMOTE_ADDR"),
            "USER_AGENT",
            environ.get("HTTP_USER_AGENT"),
            "ACCEPT_LANGUAGE",
            environ.get("HTTP_ACCEPT_LANGUAGE"),
            "REFERER",
            environ.get("HTTP_REFERER"),
        )

    def extract_data(self, model_sudo, values):
        if not model_sudo.env.su:
            raise ValueError("model_sudo should get passed with sudo")
        dest_model = request.env[model_sudo.model]

        data = {
            "record": {},
            "attachments": [],
            "custom": "",
            "meta": "",
        }

        authorized_fields = model_sudo.with_user(
            SUPERUSER_ID
        )._get_fields_form_writable(values)
        error_fields = []
        custom_fields = []

        for field_name, field_value in values.items():
            field_name = field_name.replace(r"&quot;", '"')

            if hasattr(field_value, "filename"):
                field_name = field_name.split("[", 1)[0]

                if (
                    field_name in authorized_fields
                    and authorized_fields[field_name]["type"] == "binary"
                ):
                    data["record"][field_name] = base64.b64encode(field_value.read())
                    field_value.stream.seek(0)
                    if (
                        authorized_fields[field_name]["manual"]
                        and field_name + "_filename" in dest_model
                    ):
                        data["record"][field_name + "_filename"] = field_value.filename
                else:
                    field_value.field_name = field_name
                    data["attachments"].append(field_value)

            elif field_name in authorized_fields:
                try:
                    self._extract_authorized_field(
                        data, authorized_fields, field_name, field_value
                    )
                except ValueError:
                    _debug.logic(
                        "form_field_rejected",
                        model=dest_model._name,
                        field=field_name,
                        type=authorized_fields[field_name]["type"],
                    )
                    error_fields.append(field_name)

                if dest_model._name == "mail.mail" and field_name == "email_from":
                    custom_fields.append((_("email"), field_value))

            elif (
                request.env["ir.model.fields"]._formbuilder_field_name(
                    dest_model._name, field_name
                )
                == "phone_ids"
                and "phone_ids" in authorized_fields
            ):
                if field_value:
                    data["record"]["phone_ids"] = [
                        Command.create({"number": field_value, "type": "mobile"})
                    ]
            elif field_name not in ("context", "website_form_signature"):
                custom_fields.append((field_name, field_value))

        data["custom"] = "\n".join(["%s : %s" % v for v in custom_fields])

        data["meta"] += self._extract_request_metadata()

        if hasattr(dest_model, "website_form_input_filter"):
            data["record"] = dest_model.website_form_input_filter(
                request, data["record"]
            )

        missing_required_fields = [
            label
            for label, field in authorized_fields.items()
            if field["required"] and label not in data["record"]
        ]
        if any(error_fields):
            _debug.logic(
                "form_extract_refused",
                model=dest_model._name,
                errors=error_fields,
                missing=missing_required_fields,
            )
            raise ValidationError(error_fields + missing_required_fields)

        _debug.pipeline(
            "form_data_extracted",
            model=dest_model._name,
            fields=len(data["record"]),
            attachments=len(data["attachments"]),
            custom=len(custom_fields),
        )
        return data

    def create_record(self, request, model_sudo, values, custom, meta=None):
        if not model_sudo.env.su:
            raise ValueError("model_sudo should get passed with sudo")
        model_name = model_sudo.model
        if model_name == "mail.mail":
            email_from = _(
                '"%(company)s form submission" <%(email)s>',
                company=request.env.company.name,
                email=request.env.company.email,
            )
            values.update(
                {"reply_to": values.get("email_from"), "email_from": email_from}
            )
        record = (
            request.env[model_name]
            .with_user(SUPERUSER_ID)
            .with_context(
                mail_create_nosubscribe=True,
            )
            .create(values)
        )

        if custom or meta:
            _custom_label = "%s\n___________\n\n" % _("Other Information:")
            if model_name == "mail.mail":
                _custom_label = "%s\n___________\n\n" % _(
                    "This message has been posted on your website!"
                )
            default_field = model_sudo.website_form_default_field_id
            default_field_data = values.get(default_field.name, "")
            custom_content = (
                (default_field_data + "\n\n" if default_field_data else "")
                + (_custom_label + custom + "\n\n" if custom else "")
                + (self._meta_label + "\n________\n\n" + meta if meta else "")
            )

            if default_field.name:
                if default_field.ttype == "html" or model_name == "mail.mail":
                    custom_content = nl2br(custom_content)
                record.update({default_field.name: custom_content})
            elif hasattr(record, "_message_log"):
                _debug.logic("form_custom_content", by="chatter", model=model_name)
                record._message_log(
                    body=nl2br_enclose(custom_content, "p"),
                    message_type="comment",
                )

        return record.id

    def create_attachments(self, model_sudo, id_record, files):
        if not model_sudo.env.su:
            raise ValueError("model_sudo should get passed with sudo")
        model_name = model_sudo.model
        orphan_attachment_ids = []
        record = model_sudo.env[model_name].browse(id_record)
        authorized_fields = model_sudo.with_user(
            SUPERUSER_ID
        )._get_fields_form_writable()
        for file in files:
            custom_field = file.field_name not in authorized_fields
            attachment_value = {
                "name": file.filename,
                "datas": base64.encodebytes(file.read()),
                "res_model": model_name,
                "res_id": record.id,
            }
            attachment_id = request.env["ir.attachment"].sudo().create(attachment_value)
            if attachment_id and not custom_field:
                record_sudo = record.sudo()
                value = [(4, attachment_id.id)]
                if record_sudo._fields[file.field_name].type == "many2one":
                    value = attachment_id.id
                record_sudo[file.field_name] = value
            else:
                orphan_attachment_ids.append(attachment_id.id)
        _debug.lifecycle(
            "form_attachments_created",
            model=model_name,
            record=id_record,
            files=len(files),
            orphans=len(orphan_attachment_ids),
        )

        if (
            model_name != "mail.mail"
            and hasattr(record, "_message_log")
            and orphan_attachment_ids
        ):
            record._message_log(
                attachment_ids=[(6, 0, orphan_attachment_ids)],
                body=Markup(_("<p>Attached files: </p>")),
                message_type="comment",
            )
        elif model_name == "mail.mail" and orphan_attachment_ids:
            for attachment_id_id in orphan_attachment_ids:
                record.attachment_ids = [(4, attachment_id_id)]
