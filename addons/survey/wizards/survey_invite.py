import logging
import re
from typing import Any, Self

from odoo import Command, _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.models import ValuesType
from odoo.tools.mail import email_normalize, email_split_and_format

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SurveyInvite(models.TransientModel):
    """Wizard to invite partners to answer a survey."""

    _name = "survey.invite"
    _inherit = ["mixin.mail.composer"]
    _description = "Survey Invitation Wizard"

    @api.model
    def _default_author_id(self) -> Self:
        return self.env.user.partner_id

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="survey_mail_compose_message_ir_attachments_rel",
        column1="wizard_id",
        column2="attachment_id",
        string="Attachments",
        compute="_compute_attachment_ids",
        store=True,
        readonly=False,
        bypass_search_access=True,
    )
    author_id = fields.Many2one(
        comodel_name="res.partner",
        default=_default_author_id,
        index=True,
        ondelete="set null",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="survey_invite_partner_ids",
        column1="invite_id",
        column2="partner_id",
        string="Recipients",
        domain="[ \
            '|', (survey_users_can_signup, '=', 1), \
            '|', (not survey_users_login_required, '=', 1), \
                 ('user_ids', '!=', False), \
        ]",
    )
    existing_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_existing_partner_ids",
        store=False,
        readonly=True,
    )
    emails = fields.Text(string="Additional emails")
    existing_emails = fields.Text(
        string="Existing emails",
        compute="_compute_existing_emails",
        store=False,
        readonly=True,
    )
    existing_mode = fields.Selection(
        selection=[("new", "New invite"), ("resend", "Resend invite")],
        string="Handle existing",
        default="resend",
        required=True,
    )
    existing_text = fields.Text(
        string="Resend Comment",
        compute="_compute_existing_text",
    )
    mail_server_id = fields.Many2one(
        comodel_name="ir.mail_server",
        string="Outgoing mail server",
    )
    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        required=True,
    )
    survey_start_url = fields.Char(
        string="Survey URL",
        compute="_compute_survey_start_url",
    )
    survey_access_mode = fields.Selection(
        related="survey_id.access_mode",
        readonly=True,
    )
    survey_users_login_required = fields.Boolean(
        related="survey_id.users_login_required",
        readonly=True,
    )
    survey_users_can_signup = fields.Boolean(related="survey_id.users_can_signup")
    deadline = fields.Datetime(string="Answer deadline")
    send_email = fields.Boolean(
        compute="_compute_send_email",
        inverse="_inverse_send_email",
    )

    @api.depends("survey_access_mode")
    def _compute_send_email(self) -> None:
        for record in self:
            record.send_email = record.survey_access_mode == "token"

    def _inverse_send_email(self) -> None:
        pass

    @api.depends("partner_ids", "survey_id")
    def _compute_existing_partner_ids(self) -> None:
        for wizard in self:
            wizard.existing_partner_ids = list(
                set(wizard.survey_id.user_input_ids.partner_id.ids)
                & set(wizard.partner_ids.ids)
            )

    @api.depends("emails", "survey_id")
    def _compute_existing_emails(self) -> None:
        for wizard in self:
            emails = list(set(emails_split.split(wizard.emails or "")))
            existing_emails = wizard.survey_id.mapped("user_input_ids.email")
            wizard.existing_emails = "\n".join(
                email for email in emails if email in existing_emails
            )

    @api.depends("existing_partner_ids", "existing_emails")
    def _compute_existing_text(self) -> None:
        for wizard in self:
            existing_text = False
            if wizard.existing_partner_ids:
                partner_names = ", ".join(wizard.mapped("existing_partner_ids.name"))
                existing_text = f"{_('The following customers have already received an invite')}: {partner_names}."
            if wizard.existing_emails:
                existing_text = f"{existing_text}\n" if existing_text else ""
                existing_text += f"{_('The following emails have already received an invite')}: {wizard.existing_emails}."

            wizard.existing_text = existing_text

    @api.depends("survey_id.access_token")
    def _compute_survey_start_url(self) -> None:
        for invite in self:
            invite.survey_start_url = (
                tools.urls.urljoin(
                    invite.survey_id.get_base_url(), invite.survey_id.get_start_url()
                )
                if invite.survey_id
                else False
            )

    @api.depends("survey_id")
    def _compute_render_model(self) -> None:
        self.render_model = "survey.user_input"

    @api.constrains("template_id")
    def _check_template_renders_user_inputs(self) -> None:
        for invite in self.filtered("template_id"):
            if invite.template_id.model != "survey.user_input":
                raise UserError(
                    _(
                        'The email template "%(template)s" is not a survey '
                        "invitation template: it renders %(model)s rather than "
                        "survey participations. Set its model to "
                        '"Survey User Input" or pick another template.',
                        template=invite.template_id.display_name,
                        model=invite.template_id.model or _("no model"),
                    )
                )

    @api.onchange("emails")
    def _onchange_emails(self) -> None:
        if self.emails and (
            self.survey_users_login_required and not self.survey_id.users_can_signup
        ):
            raise UserError(
                _(
                    "This survey does not allow external people to participate. You should create user accounts or update survey access mode accordingly."
                )
            )
        if not self.emails:
            return
        valid, error = [], []
        emails = list(set(emails_split.split(self.emails or "")))
        for email in emails:
            email_check = email_split_and_format(email)
            if not email_check:
                error.append(email)
            else:
                valid.extend(email_check)
        if error:
            raise UserError(
                _("Some emails you just entered are incorrect: %s", ", ".join(error))
            )
        self.emails = "\n".join(valid)

    @api.onchange("partner_ids")
    def _onchange_partner_ids(self) -> None:
        if self.survey_users_login_required and self.partner_ids:
            if not self.survey_id.users_can_signup:
                invalid_partners = self.env["res.partner"].search(
                    [("user_ids", "=", False), ("id", "in", self.partner_ids.ids)]
                )
                if invalid_partners:
                    raise UserError(
                        _(
                            "The following recipients have no user account: %s. You should create user accounts for them or allow external signup in configuration.",
                            ", ".join(invalid_partners.mapped("name")),
                        )
                    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        for values in vals_list:
            if values.get("template_id") and not (
                values.get("body") or values.get("subject")
            ):
                template = self.env["mail.template"].browse(values["template_id"])
                if not values.get("subject"):
                    values["subject"] = template.subject
                if not values.get("body"):
                    values["body"] = template.body_html
        return super().create(vals_list)

    @api.depends("template_id", "partner_ids")
    def _compute_subject(self) -> None:
        for invite in self:
            if invite.template_id and invite.template_id.subject:
                invite.subject = invite.template_id.subject
            else:
                invite.subject = _(
                    "Participate to %(survey_name)s",
                    survey_name=invite.survey_id.display_name,
                )

    @api.depends("template_id", "partner_ids")
    def _compute_body(self) -> None:
        for invite in self:
            langs = set(invite.partner_ids.mapped("lang")) - {False}
            if len(langs) == 1:
                invite = invite.with_context(lang=langs.pop())
            super(SurveyInvite, invite)._compute_body()

    @api.depends("template_id")
    def _compute_attachment_ids(self) -> None:
        for invite in self:
            if invite.template_id:
                invite.attachment_ids = invite.template_id.attachment_ids
            else:
                invite.attachment_ids = False

    def _prepare_answers(self, partners: Any, emails: list[str]) -> Any:
        existing_answers = self.env["survey.user_input"].search(
            [
                "&",
                ("survey_id", "=", self.survey_id.id),
                "|",
                ("partner_id", "in", partners.ids),
                ("email", "in", emails),
            ]
        )
        partners_done, emails_done, answers = self._get_done_partners_emails(
            existing_answers
        )

        for new_partner in partners - partners_done:
            answers |= self.survey_id._create_answer(
                partner=new_partner,
                check_attempts=False,
                **self._prepare_answer_params(),
            )
        for new_email in [email for email in emails if email not in emails_done]:
            answers |= self.survey_id._create_answer(
                email=new_email, check_attempts=False, **self._prepare_answer_params()
            )

        return answers

    def _get_done_partners_emails(
        self, existing_answers: Any
    ) -> tuple[Any, list[str], Any]:
        answers = self.env["survey.user_input"]
        partners_done = self.env["res.partner"]
        emails_done = []
        if existing_answers and self.existing_mode == "resend":
            newest_first = existing_answers.sorted("create_date", reverse=True)
            latest_by_partner = {}
            latest_by_email = {}
            for answer in newest_first:
                if answer.partner_id:
                    latest_by_partner.setdefault(answer.partner_id, answer)
                if answer.email:
                    latest_by_email.setdefault(answer.email, answer)

            # Iterate the keys that were actually indexed. mapped() on a Char keeps
            # the False of a partner-only participation, and looking that up raised
            # KeyError(False) on the mainline resend flow.
            partners_done = self.env["res.partner"].union(*latest_by_partner)
            emails_done = list(latest_by_email)
            answers = self.env["survey.user_input"].union(
                *latest_by_partner.values(), *latest_by_email.values()
            )
        return (partners_done, emails_done, answers)

    def _prepare_answer_params(self) -> dict[str, Any]:
        return {
            "deadline": self.deadline,
        }

    def _send_mails(self, answers: Any) -> Any:
        """Render each field once for the whole batch.

        _render_field takes a list of ids; calling it per recipient from a Python loop
        made a 1000-address invite 2000 single-record template renders.
        """
        if not answers:
            return self.env["mail.mail"]
        rendered = {
            field: self._render_field(field, answers.ids)
            for field in ("subject", "body")
        }
        if self.template_id.email_from:
            rendered["email_from"] = self.template_id._render_field(
                "email_from", answers.ids
            )
        return (
            self.env["mail.mail"]
            .sudo()
            .create([self._prepare_mail_values(answer, rendered) for answer in answers])
        )

    def _prepare_mail_values(
        self, answer: Any, rendered: dict[str, Any]
    ) -> dict[str, Any]:
        email_from = (
            rendered["email_from"][answer.id]
            if "email_from" in rendered
            else self.author_id.email_formatted
        )
        if not email_from:
            raise UserError(
                _(
                    "Unable to post message, please configure the sender's email address."
                )
            )
        subject = rendered["subject"][answer.id]
        body = rendered["body"][answer.id]
        mail_values = {
            "attachment_ids": [Command.link(att.id) for att in self.attachment_ids],
            "auto_delete": True,
            "author_id": self.author_id.id,
            "body_html": body,
            "email_from": email_from,
            "model": None,
            "res_id": None,
            "subject": subject,
        }
        if answer.partner_id:
            mail_values["recipient_ids"] = [Command.link(answer.partner_id.id)]
        else:
            mail_values["email_to"] = answer.email

        email_layout_xmlid = self.env.context.get(
            "default_email_layout_xmlid", self.env.context.get("notif_layout")
        )
        if email_layout_xmlid:
            mail_values["body_html"] = self._render_encapsulate(
                email_layout_xmlid,
                mail_values["body_html"],
                context_record=self.survey_id,
            )
        return mail_values

    def action_invite(self) -> dict[str, Any]:
        self.check_singleton()
        invite = self
        Partner = self.env["res.partner"]

        valid_partners = invite.partner_ids
        langs = set(valid_partners.mapped("lang")) - {False}
        if len(langs) == 1:
            invite = invite.with_context(lang=langs.pop())
        valid_emails = []
        for email in emails_split.split(invite.emails or ""):
            partner = False
            email_normalized = email_normalize(email)
            if email_normalized:
                domain = [("email_normalized", "=", email_normalized)]
                if invite.survey_users_login_required:
                    domain.append(("user_ids", "!=", False))
                partner = Partner.search(domain, limit=1)  # noqa: E8507 - one lookup per email of the invite
            if partner:
                valid_partners |= partner
            else:
                email_formatted = email_split_and_format(email)
                if email_formatted:
                    valid_emails.extend(email_formatted)

        if not valid_partners and not valid_emails:
            raise UserError(_("Please enter at least one valid recipient."))

        invite._send_mails(invite._prepare_answers(valid_partners, valid_emails))

        return {"type": "ir.actions.act_window_close"}
