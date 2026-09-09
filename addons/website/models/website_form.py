from ast import literal_eval

from lxml import etree, html

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class Website(models.Model):
    _inherit = "website"

    def _get_website_form_last_record(self):
        if request and request.session.get("form_builder_model_model"):
            return request.env[request.session["form_builder_model_model"]].browse(
                request.session["form_builder_id"]
            )
        return False


class IrModel(models.Model):
    _name = "ir.model"
    _description = "Models"
    _inherit = ["ir.model"]

    website_form_access = fields.Boolean(
        string="Allowed to use in forms",
        help="Enable the form builder feature for this model.",
    )
    website_form_default_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Field for custom form data",
        domain="[('model', '=', model), ('ttype', '=', 'text')]",
        help="Specify the field which will contain meta and custom form fields datas.",
    )
    website_form_label = fields.Char(
        string="Label for form action",
        translate=True,
        help="Form action label. Ex: crm.lead could be 'Send an e-mail' and project.issue could be 'Create an Issue'.",
    )
    website_form_key = fields.Char(help="Used in FormBuilder Registry")

    def _get_fields_form_writable(self, property_origins=None):
        if self.model == "mail.mail":
            included = {
                "email_from",
                "email_to",
                "email_cc",
                "email_bcc",
                "body",
                "reply_to",
                "subject",
            }
        else:
            included = {
                field.name
                for field in self.env["ir.model.fields"]
                .sudo()
                .search(
                    [
                        ("model_id", "=", self.id),
                        ("website_form_blacklisted", "=", False),
                    ]
                )
            }
        return {
            k: v
            for k, v in self.get_fields_authorized(self.model, property_origins).items()
            if k in included
            or ("_property" in v and v["_property"]["field"] in included)
        }

    @api.model
    def get_fields_authorized(self, model_name, property_origins):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic(
                "form_fields_refused",
                reason="not_restricted_editor",
                model=model_name,
            )
            raise AccessError(
                _("Only website editors can introspect form model fields.")
            )
        model_record = self.sudo().search(
            [("model", "=", model_name), ("website_form_access", "=", True)], limit=1
        )
        if not model_record:
            raise AccessError(_("This model cannot be used in website forms."))
        model = self.env[model_name]
        fields_get = model.fields_get()

        for val in model._inherits.values():
            fields_get.pop(val, None)

        default_values = model.with_user(SUPERUSER_ID).default_get(list(fields_get))
        for field in [f for f in fields_get if f in default_values]:
            fields_get[field]["required"] = False

        for field in list(fields_get):
            if "domain" in fields_get[field] and isinstance(
                fields_get[field]["domain"], str
            ):
                del fields_get[field]["domain"]
            if (
                fields_get[field].get("readonly")
                or field in models.MAGIC_COLUMNS
                or fields_get[field]["type"] in ("many2one_reference", "json")
            ):
                del fields_get[field]
            elif fields_get[field]["type"] == "properties":
                property_field = fields_get[field]
                del fields_get[field]
                if property_origins:
                    definition_record = property_field["definition_record"]
                    if definition_record in property_origins:
                        definition_record_field = property_field[
                            "definition_record_field"
                        ]
                        relation_field = fields_get[definition_record]
                        definition_model = self.env[relation_field["relation"]]
                        if not property_origins[definition_record].isdigit():
                            continue
                        definition_record = definition_model.browse(
                            int(property_origins[definition_record])
                        )
                        properties_definitions = definition_record[
                            definition_record_field
                        ]
                        for property_definition in properties_definitions:
                            if (
                                (
                                    property_definition["type"]
                                    in ["many2one", "many2many"]
                                    and "comodel" not in property_definition
                                )
                                or (
                                    property_definition["type"] == "selection"
                                    and not property_definition["selection"]
                                )
                                or (
                                    property_definition["type"] == "tags"
                                    and not property_definition["tags"]
                                )
                                or (property_definition["type"] == "separator")
                            ):
                                continue
                            property_definition["_property"] = {
                                "field": field,
                            }
                            property_definition["required"] = False
                            if "domain" in property_definition and isinstance(
                                property_definition["domain"], str
                            ):
                                property_definition["domain"] = literal_eval(
                                    property_definition["domain"]
                                )
                                try:
                                    property_definition["domain"] = list(
                                        Domain(property_definition["domain"])
                                    )
                                except Exception:  # noqa: S112  a malformed property domain is skipped, not fatal
                                    continue
                            fields_get[property_definition.get("name")] = (
                                property_definition
                            )

        _debug.pipeline("form_fields", model=model_name, fields=len(fields_get))
        return fields_get

    @api.model
    def get_compatible_form_models(self):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("form_models_refused", reason="not_restricted_editor")
            return []
        return self.sudo().search_read(
            [("website_form_access", "=", True)],
            ["id", "model", "name", "website_form_label", "website_form_key"],
        )


class IrModelFields(models.Model):
    _description = "Fields"
    _inherit = "ir.model.fields"

    def init(self):
        self.env.cr.execute(
            "UPDATE ir_model_fields"
            " SET website_form_blacklisted=true"
            " WHERE website_form_blacklisted IS NULL"
        )
        self.env.cr.execute(
            "ALTER TABLE ir_model_fields "
            " ALTER COLUMN website_form_blacklisted SET DEFAULT true"
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_in_website_form(self):
        for model_name, field_name in self.env["website"]._get_fields_html():
            domain = Domain.OR(
                Domain(field_name, "ilike", f'data-model_name="{model}"')
                for model in set(self.mapped("model"))
            )
            records = (
                self.env[model_name].with_context(active_test=False).search(domain)
            )  # noqa: E8507 - one query per (model, html field) pair, over every field at once
            for record in records:
                content = record[field_name]
                if not content:
                    continue
                try:
                    arch_parsed = html.fromstring(content)
                except etree.ParserError, etree.XMLSyntaxError, ValueError:
                    continue
                for field in self:
                    xpath_selector = f'//form[@data-model_name="{field.model}"]//*[@name="{field.name}"]'
                    if arch_parsed.xpath(xpath_selector):
                        _debug.logic(
                            "field_unlink_refused",
                            reason="used_in_website_form",
                            model=field.model,
                            field=field.name,
                            record=record.id,
                        )
                        raise ValidationError(
                            _(
                                "The field '%(field)s' cannot be deleted because it is referenced in a website view.\n"
                                "Model: %(model)s\n"
                                "View: %(view)s",
                                field=field.name,
                                model=field.model,
                                view=record.display_name,
                            )
                        )

    _FORM_FIELD_ALIASES = {"phone": "phone_ids"}

    @api.model
    def _formbuilder_field_name(self, model, name):
        model_fields = self.env[model]._fields
        alias = self._FORM_FIELD_ALIASES.get(name)
        if alias and name not in model_fields and alias in model_fields:
            return alias
        return name

    @api.model
    def formbuilder_whitelist(self, model, fields):
        if not fields:
            return False

        if not self.env.user.has_group("website.group_website_designer"):
            _debug.logic("form_whitelist_refused", reason="not_designer", model=model)
            return False

        fields = [self._formbuilder_field_name(model, field) for field in fields]
        unexisting_fields = [
            field for field in fields if field not in self.env[model]._fields
        ]
        if unexisting_fields:
            _debug.logic(
                "form_whitelist_refused",
                reason="unknown_fields",
                model=model,
                fields=sorted(unexisting_fields),
            )
            raise ValueError(
                "Unable to whitelist field(s) %r for model %r."
                % (unexisting_fields, model)
            )

        self.env.cr.execute(
            "UPDATE ir_model_fields"
            " SET website_form_blacklisted=false"
            " WHERE model=%s AND name = ANY(%s)",
            (model, list(fields)),
        )
        _debug.lifecycle("form_fields_whitelisted", model=model, fields=sorted(fields))
        return True

    website_form_blacklisted = fields.Boolean(
        string="Blacklisted in web forms",
        default=True,
        index=True,
        help="Blacklist this field for web forms",
    )
