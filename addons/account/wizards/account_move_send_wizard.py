from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import get_lang

from odoo.addons.mail.wizards.mail_compose_message import _reopen

_debug = DebugLog(__name__)


class AccountMoveSendWizard(models.TransientModel):
    _name = "account.move.send.wizard"
    _inherit = ["mixin.account.move.send", "mixin.mail.composer"]
    _description = "Account Move Send Wizard"

    move_id = fields.Many2one(
        comodel_name="account.move",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="move_id.company_id",
    )
    alerts = fields.Json(compute="_compute_alerts")
    sending_methods = fields.Json(
        compute="_compute_sending_methods",
        inverse="_inverse_sending_methods",
    )
    sending_method_checkboxes = fields.Json(
        compute="_compute_sending_method_checkboxes",
        precompute=True,
        store=True,
        readonly=False,
    )
    display_attachments_widget = fields.Boolean(
        compute="_compute_display_attachments_widget"
    )
    extra_edis = fields.Json(
        compute="_compute_extra_edis",
        inverse="_inverse_extra_edis",
    )
    extra_edi_checkboxes = fields.Json(
        compute="_compute_extra_edi_checkboxes",
        precompute=True,
        store=True,
        readonly=False,
    )
    invoice_edi_format = fields.Selection(
        selection=lambda self: (
            self.env["res.partner"]._fields["invoice_edi_format"].selection
        ),
        compute="_compute_invoice_edi_format",
    )
    pdf_report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Invoice report",
        compute="_compute_pdf_report_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_pdf_report_ids)]",
    )
    available_pdf_report_ids = fields.One2many(
        comodel_name="ir.actions.report",
        compute="_compute_available_pdf_report_ids",
    )

    display_pdf_report_id = fields.Boolean(compute="_compute_display_pdf_report_id")

    template_id = fields.Many2one(
        compute="_compute_template_id",
        compute_sudo=True,
        store=True,
        readonly=False,
        domain="[('model', '=', 'account.move')]",
    )
    lang = fields.Char(
        compute="_compute_lang",
        precompute=False,
        compute_sudo=True,
    )
    mail_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="To",
        compute="_compute_mail_partner_ids",
        store=True,
        readonly=False,
    )
    mail_attachments_widget = fields.Json(
        compute="_compute_mail_attachments_widget",
        store=True,
        readonly=False,
    )
    attachments_not_supported = fields.Json(
        compute="_compute_attachments_not_supported"
    )

    model = fields.Char(
        string="Related Document Model",
        compute="_compute_model",
        store=True,
        readonly=False,
    )
    res_ids = fields.Text(
        string="Related Document IDs",
        compute="_compute_res_ids",
        store=True,
        readonly=False,
    )
    template_name = fields.Char()

    @api.model
    @_debug.perf.timed
    def default_get(self, fields_list):
        _debug.lifecycle("default_get", records=self)
        results = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if "move_id" in fields_list and "move_id" not in results and active_ids:
            results["move_id"] = active_ids[0]
        return results

    @api.depends("sending_methods", "extra_edis", "mail_partner_ids")
    def _compute_alerts(self):
        for wizard in self:
            move_data = {
                wizard.move_id: {
                    "sending_methods": wizard.sending_methods or {},
                    "invoice_edi_format": wizard.invoice_edi_format,
                    "extra_edis": wizard.extra_edis or {},
                    "mail_partner_ids": wizard.mail_partner_ids,
                }
            }
            wizard.alerts = self._get_alerts(wizard.move_id, move_data)

    @api.depends("sending_method_checkboxes")
    def _compute_sending_methods(self):
        for wizard in self:
            wizard.sending_methods = self._get_selected_checkboxes(
                wizard.sending_method_checkboxes
            )

    def _inverse_sending_methods(self):
        for wizard in self:
            wizard.sending_method_checkboxes = {
                method_key: {"checked": True}
                for method_key in wizard.sending_methods or {}
            }

    @api.depends("move_id")
    @_debug.perf.timed
    def _compute_sending_method_checkboxes(self):
        methods = self.env["ir.model.fields"].get_field_selection(
            "res.partner", "invoice_sending_method"
        )

        methods = [method for method in methods if method[0] != "manual"]

        for wizard in self:
            preferred_methods = self._get_default_sending_methods(wizard.move_id)
            default_settings = self._get_default_sending_settings(wizard.move_id)
            wizard.sending_method_checkboxes = {
                method_key: {
                    "checked": (
                        method_key in preferred_methods
                        and (
                            method_key == "email"
                            or self._is_applicable_to_move(
                                method_key,
                                wizard.move_id,
                                **default_settings,
                            )
                        )
                    ),
                    "label": method_label,
                }
                for method_key, method_label in methods
                if self._is_applicable_to_company(method_key, wizard.company_id)
            }

    @api.depends("invoice_edi_format")
    def _compute_display_attachments_widget(self):
        for wizard in self:
            wizard.display_attachments_widget = wizard._display_attachments_widget(
                edi_format=wizard.invoice_edi_format,
                sending_methods=wizard.sending_methods or [],
            )

    @api.depends("extra_edi_checkboxes")
    def _compute_extra_edis(self):
        for wizard in self:
            wizard.extra_edis = self._get_selected_checkboxes(
                wizard.extra_edi_checkboxes
            )

    def _inverse_extra_edis(self):
        for wizard in self:
            wizard.extra_edi_checkboxes = {
                method_key: {"checked": True} for method_key in wizard.extra_edis or {}
            }

    @api.depends("move_id")
    def _compute_extra_edi_checkboxes(self):
        all_extra_edis = self._get_all_extra_edis()
        for wizard in self:
            wizard.extra_edi_checkboxes = {
                edi_key: {
                    "checked": True,
                    "label": all_extra_edis[edi_key]["label"],
                    "help": all_extra_edis[edi_key].get("help"),
                }
                for edi_key in self._get_default_extra_edis(wizard.move_id)
            }

    @api.depends("move_id", "sending_methods")
    def _compute_invoice_edi_format(self):
        for wizard in self:
            wizard.invoice_edi_format = self._get_default_invoice_edi_format(
                wizard.move_id, sending_methods=wizard.sending_methods or {}
            )

    @api.depends("move_id")
    def _compute_pdf_report_id(self):
        for wizard in self:
            wizard.pdf_report_id = self._get_default_pdf_report_id(wizard.move_id)

    @api.depends("move_id")
    def _compute_available_pdf_report_ids(self):
        for wizard in self:
            wizard.available_pdf_report_ids = (
                wizard.move_id._get_available_action_reports()
            )

    @api.depends("move_id")
    def _compute_display_pdf_report_id(self):
        for wizard in self:
            wizard.display_pdf_report_id = (
                len(wizard.available_pdf_report_ids) > 1
                and not wizard.move_id.invoice_pdf_report_id
            )

    @api.depends("move_id")
    def _compute_template_id(self):
        for wizard in self:
            wizard.template_id = self._get_default_mail_template_id(wizard.move_id)

    @api.depends("template_id")
    @api.depends_context("lang")
    def _compute_lang(self):
        for wizard in self:
            wizard.lang = (
                self._get_default_mail_lang(wizard.move_id, wizard.template_id)
                if wizard.template_id
                else get_lang(self.env).code
            )

    @api.depends("template_id", "lang")
    def _compute_mail_partner_ids(self):
        for wizard in self:
            wizard.mail_partner_ids = (
                commercial_partner
                if (commercial_partner := wizard.move_id.commercial_partner_id).email
                else None
            )
            if wizard.template_id:
                wizard.mail_partner_ids = self._get_default_mail_partner_ids(
                    wizard.move_id, wizard.template_id, wizard.lang
                )

    @api.depends("template_id", "lang")
    def _compute_subject(self):
        for wizard in self:
            wizard.subject = None

            if wizard.template_id:
                wizard.subject = self._get_default_mail_subject(
                    wizard.move_id, wizard.template_id, wizard.lang
                )

    @api.depends("template_id", "lang")
    def _compute_body(self):
        for wizard in self:
            wizard.body = None

            if wizard.template_id:
                wizard.body = self._get_default_mail_body(
                    wizard.move_id, wizard.template_id, wizard.lang
                )

    @api.depends("template_id", "invoice_edi_format", "extra_edis", "pdf_report_id")
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            manual_attachments_data = [
                x for x in wizard.mail_attachments_widget or [] if x.get("manual")
            ]
            wizard.mail_attachments_widget = (
                self._prepare_mail_attachments_widget(
                    wizard.move_id,
                    wizard.template_id,
                    invoice_edi_format=wizard.invoice_edi_format,
                    extra_edis=wizard.extra_edis or {},
                    pdf_report=wizard.pdf_report_id,
                )
                + manual_attachments_data
            )

    @api.depends("template_id")
    def _compute_res_ids(self):
        for wizard in self:
            wizard.res_ids = wizard.move_id.ids

    @api.depends("template_id")
    def _compute_model(self):
        for wizard in self:
            if wizard.model:
                continue
            wizard.model = self.env.context.get("active_model")

    @api.depends("sending_methods")
    def _compute_can_edit_body(self):
        for record in self:
            record.can_edit_body = (
                record.sending_methods and "email" in record.sending_methods
            )

    @api.depends("model")
    def _compute_render_model(self):
        self.render_model = "account.move"

    @_debug.perf.timed
    def open_template_creation_wizard(self):
        _debug.lifecycle("open_template_creation_wizard", records=self)
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "view_id": self.env.ref(
                "mail.mail_compose_message_view_form_template_save"
            ).id,
            "name": _("Create a Mail Template"),
            "res_model": "account.move.send.wizard",
            "context": {"dialog_size": "medium"},
            "target": "new",
            "res_id": self.id,
        }

    def create_mail_template(self):
        self.check_singleton()
        if not self.model or self.model not in self.env:
            raise UserError(
                _("Template creation from composer requires a valid model.")
            )
        model_id = self.env["ir.model"]._get_id(self.model)
        values = {
            "name": self.template_name or self.subject,
            "subject": self.subject,
            "body_html": self.body,
            "model_id": model_id,
            "use_default_to": True,
            "user_id": self.env.uid,
        }
        template = self.env["mail.template"].create(values)

        self.write({"template_id": template.id})
        return _reopen(
            self,
            self.id,
            self.model,
            context={**self.env.context, "dialog_size": "large"},
        )

    def cancel_save_template(self):
        self.check_singleton()
        return _reopen(
            self,
            self.id,
            self.model,
            context={**self.env.context, "dialog_size": "large"},
        )

    @api.depends("invoice_edi_format", "mail_attachments_widget")
    def _compute_attachments_not_supported(self):
        for wizard in self:
            wizard.attachments_not_supported = {}

    @api.constrains("move_id")
    @_debug.perf.timed
    def _check_move_id_constraints(self):
        for wizard in self:
            self._check_move_constraints(wizard.move_id)

    @api.model
    def _get_selected_checkboxes(self, json_checkboxes):
        if not json_checkboxes:
            return []
        return [
            checkbox_key
            for checkbox_key, checkbox_vals in json_checkboxes.items()
            if checkbox_vals["checked"]
        ]

    def _get_sending_settings(self):
        self.check_singleton()
        send_settings = {
            "sending_methods": self.sending_methods or [],
            "invoice_edi_format": self.invoice_edi_format,
            "extra_edis": self.extra_edis or [],
            "pdf_report": self.pdf_report_id,
            "author_user_id": self.env.user.id,
            "author_partner_id": self.env.user.partner_id.id,
        }
        if self.sending_methods and "email" in self.sending_methods:
            send_settings.update(
                {
                    "mail_template": self.template_id,
                    "mail_lang": self.lang,
                    "mail_body": self.body,
                    "mail_subject": self.subject,
                    "mail_partner_ids": self.mail_partner_ids.ids,
                }
            )
        if self.display_attachments_widget:
            send_settings["mail_attachments_widget"] = self.mail_attachments_widget
        _debug.pipeline(
            "sending_settings_built",
            wizard=self,
            sending_methods=send_settings.get("sending_methods"),
            invoice_edi_format=send_settings.get("invoice_edi_format"),
            with_mail="mail_template" in send_settings,
            with_attachments_widget="mail_attachments_widget" in send_settings,
        )
        return send_settings

    def _update_preferred_settings(self):
        self.check_singleton()
        if (
            not self.move_id.partner_id.invoice_template_pdf_report_id
            and self.pdf_report_id != self._get_default_pdf_report_id(self.move_id)
        ):
            self.move_id.partner_id.sudo().invoice_template_pdf_report_id = (
                self.pdf_report_id
            )

    @api.model
    @_debug.perf.timed
    def _action_download(self, attachments):
        _debug.lifecycle("_action_download", records=self)
        return {
            "type": "ir.actions.act_url",
            "url": f"/account/download_invoice_attachments/{','.join(map(str, attachments.ids))}",
            "close": True,
        }

    @_debug.perf.timed
    def action_send_and_print(self, allow_fallback_pdf=False):
        _debug.lifecycle("action_send_and_print", records=self)
        self.check_singleton()
        if self.alerts:
            self._raise_danger_alerts(self.alerts)
        self._update_preferred_settings()
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "action_send_and_print",
                sendwizard=self,
                move=self.move_id,
                methods=self.sending_methods,
                edis=self.extra_edis,
                fallback=allow_fallback_pdf,
            )
        attachments = self._generate_and_send_invoices(
            self.move_id,
            **self._get_sending_settings(),
            allow_fallback_pdf=allow_fallback_pdf,
        )
        if attachments and self.sending_methods and "manual" in self.sending_methods:
            return self._action_download(attachments)
        else:
            return {"type": "ir.actions.act_window_close"}
