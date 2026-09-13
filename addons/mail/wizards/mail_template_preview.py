import typing

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from ..models.mail_template import MailTemplate
    from ..models.res_partner import ResPartner
    from odoo.addons.base.models.ir_model import IrModel
    from odoo.addons.bus.models.ir_attachment import IrAttachment

_debug = DebugLog(__name__)


class MailTemplatePreview(models.TransientModel):
    _name = "mail.template.preview"
    _description = "Email Template Preview"
    _MAIL_TEMPLATE_FIELDS = [
        "attachment_ids",
        "body_html",
        "subject",
        "email_cc",
        "email_from",
        "email_to",
        "partner_to",
        "reply_to",
        "scheduled_date",
    ]

    @api.model
    def _selection_target_model(self) -> list:
        return [
            (model.model, model.name)
            for model in self.env["ir.model"].sudo().search([])
        ]

    @api.model
    def _selection_languages(self) -> list[tuple[str, str]]:
        return self.env["res.lang"].get_installed()

    mail_template_id: MailTemplate = fields.Many2one(
        comodel_name="mail.template",
        string="Related Mail Template",
        required=True,
    )
    model_id: IrModel = fields.Many2one(
        comodel_name="ir.model",
        related="mail_template_id.model_id",
        string="Targeted model",
    )
    resource_ref = fields.Reference(
        selection="_selection_target_model",
        string="Record",
        compute="_compute_resource_ref",
        compute_sudo=False,
        store=True,
        readonly=False,
    )
    lang = fields.Selection(
        selection=_selection_languages,
        string="Template Preview Language",
    )
    no_record = fields.Boolean(compute="_compute_no_record")
    error_msg = fields.Char(
        string="Error Message",
        compute="_compute_mail_template_fields",
    )
    subject = fields.Char(compute="_compute_mail_template_fields")
    email_from = fields.Char(
        string="From",
        compute="_compute_mail_template_fields",
        help="Sender address",
    )
    email_to = fields.Char(
        string="To",
        compute="_compute_mail_template_fields",
        help="Comma-separated recipient addresses",
    )
    email_cc = fields.Char(
        string="Cc",
        compute="_compute_mail_template_fields",
        help="Carbon copy recipients",
    )
    reply_to = fields.Char(
        string="Reply-To",
        compute="_compute_mail_template_fields",
        help="Preferred response address",
    )
    scheduled_date = fields.Char(
        compute="_compute_mail_template_fields",
        help="The queue manager will send the email after the date",
    )
    body_html = fields.Html(
        string="Body",
        sanitize=False,
        compute="_compute_mail_template_fields",
    )
    attachment_ids: IrAttachment = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        compute="_compute_mail_template_fields",
    )
    has_attachments = fields.Boolean(compute="_compute_has_attachments")
    has_several_languages_installed = fields.Boolean(
        compute="_compute_has_several_languages_installed"
    )
    partner_ids: ResPartner = fields.Many2many(
        comodel_name="res.partner",
        string="Recipients",
        compute="_compute_mail_template_fields",
    )

    @api.depends("model_id")
    def _compute_no_record(self) -> None:
        for preview, preview_sudo in zip(self, self.sudo(), strict=False):
            model_id = preview_sudo.model_id
            preview.no_record = not model_id or not self.env[  # noqa: E8507  the probed model varies per preview, so no one query spans them
                model_id.model
            ].search_count([], limit=1)

    @api.depends("lang", "resource_ref")
    def _compute_mail_template_fields(self) -> None:
        for preview in self:
            error_msg = False
            mail_template = preview.mail_template_id.with_context(lang=preview.lang)
            if not preview.resource_ref or not preview.resource_ref.id:
                preview._update_mail_attributes()
                preview.error_msg = False
            else:
                try:
                    mail_values = mail_template.with_context(
                        template_preview_lang=preview.lang
                    )._prepare_mail_vals(
                        [preview.resource_ref.id], preview._MAIL_TEMPLATE_FIELDS
                    )[preview.resource_ref.id]
                    preview._update_mail_attributes(values=mail_values)
                except (ValueError, UserError, AccessError) as user_error:
                    preview._update_mail_attributes()
                    error_msg = user_error.args[0]
            preview.error_msg = error_msg

    @api.depends("attachment_ids")
    def _compute_has_attachments(self) -> None:
        for preview in self:
            preview.has_attachments = bool(preview.attachment_ids)

    @api.depends("lang")
    def _compute_has_several_languages_installed(self) -> None:
        for preview in self:
            preview.has_several_languages_installed = bool(
                preview._fields["lang"].selection(preview)
            )

    @api.depends("mail_template_id")
    def _compute_resource_ref(self) -> None:
        to_reset = self.filtered(lambda p: not p.mail_template_id.model)
        to_reset.resource_ref = False
        for preview in self - to_reset:
            mail_template = preview.mail_template_id.sudo()
            model = mail_template.model
            res = self.env[model].search([], limit=1)  # noqa: E8507  the probed model varies per preview, so no one query spans them
            preview.resource_ref = f"{model},{res.id}" if res else False

    def _update_mail_attributes(self, values: dict | None = None) -> None:
        _debug.logic(
            "preview_attributes",
            template=self.mail_template_id.id,
            rendered=values is not None,
            fields=sorted(values) if values else [],
        )
        for field in self._MAIL_TEMPLATE_FIELDS:
            if field == "partner_to":
                continue
            field_value = (
                values.get(field, False) if values else self.mail_template_id[field]
            )
            self[field] = field_value
        self.partner_ids = values.get("partner_ids", False) if values else False
