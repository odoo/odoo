from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ApplicantGetRefuseReason(models.TransientModel):
    _name = "applicant.get.refuse.reason"
    _inherit = ["mixin.mail.composer"]
    _description = "Get Refuse Reason"

    def _default_refuse_reason_id(self):
        return self.env["hr.applicant.refuse.reason"].search([], limit=1)

    refuse_reason_id = fields.Many2one(
        comodel_name="hr.applicant.refuse.reason",
        default=_default_refuse_reason_id,
        required=True,
    )
    applicant_ids = fields.Many2many(comodel_name="hr.applicant")
    send_mail = fields.Boolean(
        string="Send Email",
        compute="_compute_send_mail",
        precompute=True,
        store=True,
        readonly=False,
    )
    template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        compute="_compute_template_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('model', '=', 'hr.applicant')]",
    )
    applicant_without_email = fields.Text(
        string="Applicant(s) not having email",
        compute="_compute_applicant_without_email",
    )
    duplicates = fields.Boolean(string="Refuse Duplicate Applications")
    duplicates_count = fields.Integer(compute="_compute_duplicate_applicant_ids_domain")
    duplicate_applicant_ids = fields.Many2many(
        comodel_name="hr.applicant",
        relation="applicant_get_refuse_reason_duplicate_applicants_rel",
        string="Duplicate Applications",
        compute="_compute_duplicate_applicant_ids",
        store=True,
        readonly=False,
    )
    duplicate_applicant_ids_domain = fields.Binary(
        compute="_compute_duplicate_applicant_ids_domain"
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        compute="_compute_from_template_id",
        store=True,
        readonly=False,
        bypass_search_access=True,
    )
    scheduled_date = fields.Char(
        compute="_compute_from_template_id",
        store=True,
        readonly=False,
        help="send emails after that date. This date is considered as being in UTC timezone.",
    )

    @api.depends("refuse_reason_id", "applicant_without_email")
    def _compute_send_mail(self):
        for wizard in self:
            template = wizard.refuse_reason_id.template_id
            wizard.send_mail = template and not wizard.applicant_without_email

    @api.depends("applicant_ids")
    def _compute_applicant_without_email(self):
        for wizard in self:
            applicants = wizard.applicant_ids.filtered(
                lambda x: not x.email_from and not x.partner_id.email
            )
            if applicants:
                wizard.applicant_without_email = "%s\n%s" % (
                    _(
                        "You can't select Send email option.\nThe email will not be sent to the following applicant(s) as they don't have an email address:"
                    ),
                    ", ".join(
                        [i.partner_name or i.display_name or "" for i in applicants]
                    ),
                )
            else:
                wizard.applicant_without_email = False

    @api.depends("applicant_ids")
    def _compute_duplicate_applicant_ids_domain(self):
        for wizard in self:
            domain = (
                wizard.applicant_ids._get_domain_similar_applicants()
                & Domain("id", "not in", wizard.applicant_ids.ids)
                & Domain("application_status", "=", "ongoing")
            )
            wizard.duplicate_applicant_ids_domain = domain
            wizard.duplicates_count = self.env["hr.applicant"].search_count(domain)  # noqa: E8507 - a transient wizard: one record

    @api.depends("duplicates", "duplicate_applicant_ids_domain")
    def _compute_duplicate_applicant_ids(self):
        for wizard in self:
            wizard.duplicate_applicant_ids = (
                self.env["hr.applicant"].search(wizard.duplicate_applicant_ids_domain)  # noqa: E8507 - a transient wizard: one record
                if wizard.duplicates
                else self.env["hr.applicant"]
            )

    @api.depends("refuse_reason_id")
    def _compute_render_model(self):
        self.render_model = "hr.applicant"

    @api.depends("refuse_reason_id")
    def _compute_template_id(self):
        for wizard in self:
            if wizard.refuse_reason_id:
                wizard.template_id = wizard.refuse_reason_id.template_id
            else:
                wizard.template_id = False

    @api.depends("template_id")
    def _compute_from_template_id(self):
        fields_to_copy_name_mapping = {
            "body": "body_html",
            "attachment_ids": "attachment_ids",
            "scheduled_date": "scheduled_date",
            "subject": "subject",
        }
        for wizard in self:
            for (
                wizard_field_name,
                template_field_name,
            ) in fields_to_copy_name_mapping.items():
                if wizard.template_id:
                    wizard[wizard_field_name] = wizard.template_id[template_field_name]
                else:
                    wizard[wizard_field_name] = False

    def action_refuse_reason_apply(self):
        if self.send_mail:
            if not self.env.user.email:
                _debug.logic(
                    "refuse_refused", reason="no_sender_email", user=self.env.user
                )
                raise UserError(
                    _(
                        "Unable to post message, please configure the sender's email address."
                    )
                )
            if any(
                not (applicant.email_from or applicant.partner_id.email)
                for applicant in self.applicant_ids
            ):
                _debug.logic(
                    "refuse_refused",
                    reason="applicant_without_email",
                    applicants=self.applicant_ids,
                )
                raise UserError(
                    _(
                        "At least one applicant doesn't have a email; you can't use send email option."
                    )
                )

        refused_applications = self.applicant_ids
        if self.duplicates_count and self.duplicates:
            refused_applications |= self.duplicate_applicant_ids

            original_by_duplicate = self._get_related_original_applicants()
            _debug.logic(
                "refuse_duplicates",
                originals=self.applicant_ids,
                duplicates=self.duplicate_applicant_ids,
                unmatched=len(self.duplicate_applicant_ids)
                - len(original_by_duplicate),
            )
            self.duplicate_applicant_ids._message_log_batch(
                bodies={
                    duplicate.id: self._duplicate_refusal_body(
                        original_by_duplicate.get(duplicate)
                    )
                    for duplicate in self.duplicate_applicant_ids
                }
            )
        _debug.lifecycle(
            "refuse",
            applicants=refused_applications,
            reason=self.refuse_reason_id,
            mail=self.send_mail,
        )
        refused_applications.write(
            {
                "refuse_reason_id": self.refuse_reason_id.id,
                "active": False,
                "refuse_date": self.env.cr.now(),
            }
        )

        if self.send_mail:
            self._send_refusal_mails()

        return {"type": "ir.actions.act_window_close"}

    def _duplicate_refusal_body(self, original):
        if original:
            return _(
                "Refused automatically because this application has been identified"
                " as a duplicate of %(link)s",
                link=original._get_html_link(),
            )
        return _(
            "Refused automatically because this application has been identified"
            " as a duplicate of another refused application."
        )

    def _duplicate_match_fields(self):
        """Keys that make a duplicate traceable back to a refused application.

        Must stay a superset of what ``_get_domain_similar_applicants`` selects
        on, or a duplicate the wizard offers has no original to point at.
        """
        return (
            *self.env["hr.applicant"]._DUPLICATE_KEY_FIELDS,
            "pool_applicant_id",
        )

    def _get_related_original_applicants(self):
        match_fields = self._duplicate_match_fields()
        original_by_key = {}
        for original in self.applicant_ids:
            for fname in match_fields:
                if value := original[fname]:
                    original_by_key.setdefault((fname, value), original)

        related_original_applicants = {}
        for duplicate in self.duplicate_applicant_ids:
            for fname in match_fields:
                value = duplicate[fname]
                if value and (original := original_by_key.get((fname, value))):
                    related_original_applicants[duplicate] = original
                    break
        return related_original_applicants

    def _send_refusal_mails(self):
        """Render the template once per language, not once per applicant.

        Refusing is a bulk action, and the rendering has to be grouped by
        language rather than done in one call because the template is rendered
        in each recipient's.
        """
        applicants = self.applicant_ids
        lang_by_applicant = self._render_lang(applicants.ids)
        ids_by_lang = defaultdict(list)
        for applicant in applicants:
            ids_by_lang[lang_by_applicant[applicant.id]].append(applicant.id)
        subjects, bodies = {}, {}
        for lang, res_ids in ids_by_lang.items():
            subjects.update(self._render_field("subject", res_ids, set_lang=lang))
            bodies.update(self._render_field("body", res_ids, set_lang=lang))
        _debug.perf.count(
            "refusal_mails", applicants=len(applicants), languages=len(ids_by_lang)
        )
        for applicant in applicants:
            mail_values = self._prepare_mail_values(applicant, subjects, bodies)
            applicant.message_post(**mail_values)

    def _prepare_mail_values(self, applicant, subjects=None, bodies=None):
        if subjects is None or bodies is None:
            lang = self._render_lang(applicant.ids)[applicant.id]
            subjects = self._render_field("subject", applicant.ids, set_lang=lang)
            bodies = self._render_field("body", applicant.ids, set_lang=lang)
        subject = subjects[applicant.id]
        body = bodies[applicant.id]
        email_from = (
            self.template_id.email_from
            if self.template_id and self.template_id.email_from
            else self.env.user.email_formatted
        )
        return {
            "body": body,
            "email_from": email_from,
            "subject": subject,
            "author_id": self.env.user.partner_id.id,
            "incoming_email_to": applicant.email_from or applicant.partner_id.email,
            "scheduled_date": self.scheduled_date,
            "attachment_ids": [Command.link(att.id) for att in self.attachment_ids],
            "body_is_html": True,
        }
