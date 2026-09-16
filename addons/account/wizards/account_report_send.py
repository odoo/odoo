from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.documents import mimetype_for
from odoo.tools.misc import get_lang

_debug = DebugLog(__name__)


class AccountReportSend(models.TransientModel):
    _name = "account.report.send"
    _description = "Account Report Send"

    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_partner_ids",
    )
    mode = fields.Selection(
        selection=[
            ("single", "Single Recipient"),
            ("multi", "Multiple Recipients"),
        ],
        compute="_compute_mode",
        store=True,
        readonly=False,
    )

    # == PRINT ==
    enable_download = fields.Boolean()
    checkbox_download = fields.Boolean(string="Download")

    # == MAIL ==
    enable_send_mail = fields.Boolean(default=True)
    checkbox_send_mail = fields.Boolean(
        string="Email",
        default=True,
    )

    display_mail_composer = fields.Boolean(compute="_compute_send_mail_extra_fields")
    warnings = fields.Json(compute="_compute_warnings")
    send_mail_readonly = fields.Boolean(compute="_compute_send_mail_extra_fields")
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email template",
        domain="[('model', '=', 'res.partner')]",
    )

    account_report_id = fields.Many2one(
        comodel_name="account.report",
        string="Report",
    )
    report_options = fields.Json()

    mail_lang = fields.Char(
        string="Lang",
        compute="_compute_mail_lang",
    )
    mail_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Recipients",
        compute="_compute_mail_partner_ids",
        store=True,
        readonly=False,
    )
    mail_subject = fields.Char(
        string="Subject",
        compute="_compute_mail_subject_body",
        store=True,
        readonly=False,
    )
    mail_body = fields.Html(
        string="Contents",
        sanitize_style=True,
        compute="_compute_mail_subject_body",
        store=True,
        readonly=False,
    )
    mail_attachments_widget = fields.Json(
        compute="_compute_mail_attachments_widget",
        store=True,
        readonly=False,
    )

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        # EXTENDS 'base'
        _debug.lifecycle("default_get", records=self)
        results = super().default_get(fields)

        context_options = self.env.context.get("default_report_options", {})
        if "account_report_id" in fields and "account_report_id" not in results:
            report_id = context_options.get("report_id", False)
            results["account_report_id"] = report_id
            results["report_options"] = context_options

        return results

    @api.model
    def _get_mail_field_value(self, partner, mail_template, mail_lang, field, **kwargs):
        if not mail_template:
            return None
        return mail_template.with_context(lang=mail_lang)._render_field(
            field, partner.ids, **kwargs
        )[partner._origin.id]

    def _prepare_mail_attachments_widget(self, partner, mail_template):
        return self._prepare_mail_attachment_placeholders(
            partner
        ) + self._prepare_template_attachment_entries(mail_template)

    def _prepare_wizard_values(self):
        self.check_singleton()
        options = self.report_options
        if not options.get("partner_ids", []):
            options["partner_ids"] = self.partner_ids.ids
        return {
            "mail_template_id": self.mail_template_id.id,
            "checkbox_download": self.checkbox_download,
            "checkbox_send_mail": self.checkbox_send_mail,
            "report_options": options,
        }

    def _prepare_mail_attachment_placeholders(self, partner):
        """Return the placeholder attachment data of the report of a partner.

        Each dictionary holds:

        * id: str, the (fake) id of the attachment, needed as t-key on rendering.
        * name: str, the name of the attachment.
        * mimetype: str, the mimetype of the attachment.
        * placeholder: bool, True to prevent download / deletion.

        :param recordset partner: the partner this report is generated for
        :return: one dictionary per placeholder
        :rtype: list
        """
        # Extend to add placeholders based on the checkboxes.
        self.check_singleton()
        extension = "pdf"
        filename = f"{partner.name} - {self.account_report_id.get_default_report_filename(self.report_options, extension)}"
        return [
            {
                "id": f"placeholder_{filename}",
                "name": filename,
                "mimetype": mimetype_for(extension),
                "placeholder": True,
            }
        ]

    @api.model
    def _prepare_template_attachment_entries(self, mail_template):
        """Return the attachment data of a mail template."""
        return [
            {
                "id": attachment.id,
                "name": attachment.name,
                "mimetype": attachment.mimetype,
                "placeholder": False,
                "mail_template_id": mail_template.id,
            }
            for attachment in mail_template.attachment_ids
        ]

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("partner_ids")
    def _compute_mode(self):
        for wizard in self:
            wizard.mode = "single" if len(wizard.partner_ids) == 1 else "multi"

    @api.depends("checkbox_send_mail")
    def _compute_send_mail_extra_fields(self):
        for wizard in self:
            wizard.display_mail_composer = wizard.mode == "single"
            partners_without_mail_data = wizard.mail_partner_ids.filtered(
                lambda x: not x.email
            )
            wizard.send_mail_readonly = (
                partners_without_mail_data == wizard.mail_partner_ids
            )

    @api.depends("mail_partner_ids", "checkbox_send_mail", "send_mail_readonly")
    @_debug.perf.timed
    def _compute_warnings(self):
        for wizard in self:
            warnings = {}

            partners_without_mail = wizard.mail_partner_ids.filtered(
                lambda x: not x.email
            )
            if wizard.send_mail_readonly or (
                wizard.checkbox_send_mail and partners_without_mail
            ):
                warnings["account_missing_email"] = {
                    "message": _("Partner(s) should have an email address."),
                    "action_text": _("View Partner(s)"),
                    "action": partners_without_mail._get_records_action(
                        name=_("Check Partner(s) Email(s)")
                    ),
                }

            wizard.warnings = warnings

    @api.depends("partner_ids")
    @api.depends_context("lang")
    def _compute_mail_lang(self):
        for wizard in self:
            if wizard.mode == "single":
                wizard.mail_lang = wizard.partner_ids.lang
            else:
                wizard.mail_lang = get_lang(self.env).code

    @api.depends("account_report_id", "report_options")
    def _compute_partner_ids(self):
        for wizard in self:
            wizard.partner_ids = wizard.account_report_id._get_report_send_recipients(
                wizard.report_options
            )

    @api.depends("account_report_id", "report_options", "mail_template_id")
    def _compute_mail_partner_ids(self):
        for wizard in self:
            wizard.mail_partner_ids = wizard.partner_ids

    @api.depends("mail_template_id", "mail_lang", "mode")
    @_debug.perf.timed
    def _compute_mail_subject_body(self):
        for wizard in self:
            if wizard.mode == "single" and wizard.mail_template_id:
                wizard.mail_subject = self._get_mail_field_value(
                    wizard.mail_partner_ids,
                    wizard.mail_template_id,
                    wizard.mail_lang,
                    "subject",
                )
                wizard.mail_body = self._get_mail_field_value(
                    wizard.mail_partner_ids,
                    wizard.mail_template_id,
                    wizard.mail_lang,
                    "body_html",
                    options={"post_process": True},
                )
            else:
                wizard.mail_subject = wizard.mail_body = None

    @api.depends("mail_template_id", "mode")
    def _compute_mail_attachments_widget(self):
        for wizard in self:
            if wizard.mode == "single":
                wizard.mail_attachments_widget = (
                    wizard._prepare_mail_attachments_widget(
                        wizard.mail_partner_ids, wizard.mail_template_id
                    )
                )
            else:
                wizard.mail_attachments_widget = []

    @api.model
    @_debug.perf.timed
    def _action_download(self, attachments):
        """Return the action downloading the attachment, or a zip of them if there is more than one."""
        _debug.lifecycle("_action_download", records=self)
        return {
            "type": "ir.actions.act_url",
            "url": f"/account/download_attachments/{','.join(map(str, attachments.ids))}",
            "close": True,
        }

    @_debug.perf.timed
    def _process_send_and_print(
        self, report, options, recipient_partner_ids=None, wizard=None
    ):
        """Generate the report of each partner of the options, then mail and/or download it.

        :param recordset report: the account.report to generate
        :param dict options: report options; options['partner_ids'] holds the partners to process
        :param list recipient_partner_ids: ids of the partners that will receive the mail message
        :param wizard: the account.report.send wizard; absent when sending by cron, in which
                       case the values stored in report.send_and_print_values are used
        :return: a download action if attachments have to be downloaded, else None
        """
        wizard_vals = (
            report.send_and_print_values if not wizard else wizard._prepare_wizard_values()
        )
        to_email = wizard_vals["checkbox_send_mail"]
        to_download = wizard_vals["checkbox_download"]

        mail_template_id = self.env["mail.template"].browse(
            wizard_vals["mail_template_id"]
        )
        if wizard:
            attachments_ids = [
                att["id"]
                for att in wizard.mail_attachments_widget or []
                if not att["placeholder"]
            ]
        else:
            attachments_ids = mail_template_id.attachment_ids.ids
        _debug.logic(
            "send_mode_resolved",
            report=report,
            from_cron=not wizard,
            to_email=to_email,
            to_download=to_download,
            mail_template=mail_template_id,
            attachments=len(attachments_ids),
        )

        options["unfold_all"] = True

        partner_ids = options.get("partner_ids", [])
        partners = self.env["res.partner"].browse(partner_ids)
        _debug.logic(
            "recipients_resolved",
            report=report,
            partners=partners,
            recipients_defaulted=not recipient_partner_ids,
        )
        if not recipient_partner_ids:
            recipient_partner_ids = partners.filtered("email").ids

        email_from = (
            mail_template_id._render_field("email_from", partner_ids)
            if mail_template_id
            else {}
        )
        downloadable_attachments = self.env["ir.attachment"]

        for partner in partners:
            options["partner_ids"] = partner.ids
            report_attachment = partner._get_partner_account_report_attachment(
                report, options
            )

            if to_email and recipient_partner_ids:
                if wizard and wizard.mode == "single":
                    subject = self.mail_subject
                    body = self.mail_body
                else:
                    subject = self._get_mail_field_value(
                        partner, mail_template_id, partner.lang, "subject"
                    )
                    body = self._get_mail_field_value(
                        partner,
                        mail_template_id,
                        partner.lang,
                        "body_html",
                        options={"post_process": True},
                    )

                partner.message_post(
                    body=body,
                    subject=subject,
                    email_from=email_from.get(partner.id),
                    partner_ids=recipient_partner_ids,
                    attachment_ids=attachments_ids + report_attachment.ids,
                    email_add_signature=False,
                )

            if to_download:
                downloadable_attachments += report_attachment

        _debug.pipeline(
            "partners_processed",
            report=report,
            partners=len(partners),
            mailed=bool(to_email and recipient_partner_ids),
            downloadable_attachments=downloadable_attachments,
        )
        if downloadable_attachments:
            return self._action_download(downloadable_attachments)
        return None

    @_debug.perf.timed
    def action_send_and_print(self, force_synchronous=False):
        """Create the documents and send them to the end customers.

        Multiple statements that are not downloaded are processed asynchronously by cron.

        :param force_synchronous: process synchronously even in multi mode
        """
        _debug.lifecycle("action_send_and_print", records=self)
        self.check_singleton()

        if (
            self.mode == "multi"
            and self.checkbox_send_mail
            and not self.mail_template_id
        ):
            raise UserError(
                _("Please select a mail template to send multiple statements.")
            )

        force_synchronous = force_synchronous or self.checkbox_download
        process_later = self.mode == "multi" and not force_synchronous
        if _debug.logic.enabled:
            _debug.logic(
                "action_send_and_print",
                reportsend=self,
                mode=self.mode,
                later=process_later,
                mail=self.checkbox_send_mail,
                download=self.checkbox_download,
                partners=self.partner_ids,
            )
        if process_later:
            # Set sending information on report
            if self.account_report_id.send_and_print_values:
                raise UserError(
                    _(
                        "There are currently reports waiting to be sent, please try again later."
                    )
                )

            self.account_report_id.send_and_print_values = self._prepare_wizard_values()

            self.env.ref("account.ir_cron_account_report_send")._trigger()
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": _("Sending statements"),
                    "message": _("Statements are being sent in the background."),
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        options = {
            **self.report_options,
            "partner_ids": self.partner_ids.ids,
        }
        return self._process_send_and_print(
            report=self.account_report_id,
            options=options,
            recipient_partner_ids=self.mail_partner_ids.ids,
            wizard=self,
        )
