import logging

from odoo import api, fields, models
from odoo.tools.misc import html_escape

_logger = logging.getLogger(__name__)


class SignRequest(models.Model):
    _name = "sign.request"
    _description = "Sign Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, tracking=True, default="/")
    reference = fields.Char(
        string="Reference",
        readonly=True,
        copy=False,
        index=True,
    )
    template_id = fields.Many2one(
        comodel_name="sign.template",
        string="Template",
        ondelete="set null",
    )
    request_item_ids = fields.One2many(
        comodel_name="sign.request.item",
        inverse_name="sign_request_id",
        string="Signers",
        copy=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("signed", "Signed"),
            ("refused", "Refused"),
            ("canceled", "Canceled"),
            ("expired", "Expired"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    completion_date = fields.Datetime(copy=False)
    active = fields.Boolean(default=True)
    color = fields.Integer()
    progress = fields.Char(
        compute="_compute_progress",
        string="Progress",
        store=True,
    )
    nb_closed = fields.Integer(
        compute="_compute_progress",
        string="Closed Signers",
        store=True,
    )
    nb_total = fields.Integer(
        compute="_compute_progress",
        string="Total Signers",
        store=True,
    )
    validity_date = fields.Date()
    reminder = fields.Integer(
        default=0,
        help="Reminder interval in days. Set to 0 to disable reminders.",
    )
    last_reminder = fields.Date(copy=False)
    message = fields.Text()
    completed_document = fields.Binary(copy=False, attachment=True)
    completed_document_name = fields.Char(copy=False)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
    )
    favorited_ids = fields.Many2many(
        comodel_name="res.users",
        relation="sign_request_favorite_user_rel",
        column1="request_id",
        column2="user_id",
        string="Favorite Users",
    )
    log_ids = fields.One2many(
        comodel_name="sign.log",
        inverse_name="sign_request_id",
        string="Logs",
        readonly=True,
    )

    _reference_unique = models.Constraint(
        "UNIQUE(reference)",
        "Request reference must be unique.",
    )

    @api.depends("request_item_ids.state")
    def _compute_progress(self):
        for request in self:
            total = len(request.request_item_ids)
            closed = len(request.request_item_ids.filtered(lambda item: item.state == "completed"))
            request.nb_total = total
            request.nb_closed = closed
            request.progress = "%s/%s signed" % (closed, total)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if not vals.get("reference"):
                vals["reference"] = sequence.next_by_code("sign.request") or "/"
            if not vals.get("name") or vals["name"] == "/":
                vals["name"] = vals["reference"]
            if not vals.get("company_id"):
                vals["company_id"] = self.env.company.id
        requests = super().create(vals_list)
        for request in requests:
            request._log_event("draft", "Sign request created.")
        return requests

    def _log_event(self, event, note=None, request_item=None):
        log_model = self.env["sign.log"].sudo()
        for request in self:
            log_model.create(
                {
                    "sign_request_id": request.id,
                    "sign_request_item_id": request_item.id if request_item else False,
                    "event": event,
                    "note": note or False,
                    "user_id": self.env.user.id,
                }
            )

    def action_open_send_wizard(self):
        self.ensure_one()
        action = self.env.ref("sign.sign_request_send_wizard_action", raise_if_not_found=False)
        if not action:
            return False
        values = action.read()[0]
        values["context"] = {"default_request_id": self.id}
        return values

    def action_draft(self):
        for request in self:
            request.request_item_ids.action_draft()
            request.write(
                {
                    "state": "draft",
                    "completion_date": False,
                }
            )
            request._log_event("draft", "Request moved to draft.")
        return True

    def action_sent(self, signer_ids=None, subject=None, message=None):
        signer_ids = signer_ids or []
        for request in self:
            request_items = request.request_item_ids
            if signer_ids:
                request_items = request_items.filtered(lambda rec: rec.id in signer_ids)
            request_items = request_items.filtered(lambda rec: rec.state in ("draft", "sent"))
            if not request_items:
                continue
            values = {"state": "sent"}
            if message is not None:
                values["message"] = message
            request.write(values)
            request_items.action_sent()
            for request_item in request_items:
                request._send_signature_request_mail(
                    request_item=request_item,
                    subject=subject,
                    message=message,
                )
            request._log_event(
                "sent",
                "Signature request sent to %s signer(s)." % len(request_items),
            )
        return True

    # ── QBO MIGRATION BOUNDARY ─────────────────────────
    # Signed contracts activating subscriptions during
    # the pre-cutover period must be reconciled against
    # QBO historical invoices after migration.
    # Flag: self.company_id and self.reference should be
    # captured by reconciliation routines.
    # ────────────────────────────────────────────────────
    def action_signed(self):
        now = fields.Datetime.now()
        for request in self:
            if request.state == "signed":
                continue
            final_document = request._get_final_document()
            values = {
                "state": "signed",
                "completion_date": now,
            }
            if final_document:
                values["completed_document"] = final_document
                values["completed_document_name"] = "%s.pdf" % (request.reference or request.name)
            request.write(values)
            request.request_item_ids.filtered(
                lambda item: item.state in ("draft", "sent")
            ).write(
                {
                    "state": "completed",
                    "signing_date": now,
                    "refusal_reason": False,
                }
            )
            request._log_event("signed", "Request completed.")
        return True

    def action_refuse(self):
        return self.action_refused(False)

    def action_refused(self, refusal_reason=None):
        for request in self:
            request.write({"state": "refused"})
            request.request_item_ids.filtered(
                lambda item: item.state in ("draft", "sent")
            ).write(
                {
                    "state": "refused",
                    "refusal_reason": refusal_reason or False,
                }
            )
            request._log_event("refused", refusal_reason or "Request refused.")
        return True

    def action_cancel(self):
        for request in self:
            request.write({"state": "canceled"})
            request.request_item_ids.filtered(lambda item: item.state == "sent").write(
                {"state": "draft"}
            )
            request._log_event("canceled", "Request canceled.")
        return True

    def _send_signature_request_mail(self, request_item, subject=None, message=None):
        self.ensure_one()
        if not request_item.signer_email:
            _logger.warning(
                "sign: signer email missing for request item %s in request %s",
                request_item.id,
                self.id,
            )
            return False

        link = request_item._get_sign_link()
        signer_name = request_item.signer_name or request_item.partner_id.name or "Signer"
        mail_subject = subject or "Signature request: %s" % (self.name or self.reference)
        mail_message = message if message is not None else (self.message or "Please sign the document.")
        body_html = (
            "<p>Hello %s,</p>"
            "<p>%s</p>"
            '<p><a href="%s">Open document to sign</a></p>'
        ) % (
            html_escape(signer_name),
            html_escape(mail_message),
            html_escape(link),
        )

        mail_vals = {
            "subject": mail_subject,
            "body_html": body_html,
            "email_to": request_item.signer_email,
            "author_id": self.env.user.partner_id.id,
            "model": "sign.request",
            "res_id": self.id,
            "auto_delete": False,
        }
        mail = self.env["mail.mail"].sudo().create(mail_vals)
        mail.send()
        return True

    def _get_final_document(self):
        self.ensure_one()
        # STUB-001 - see GAPS.md
        _logger.warning(
            "sign: _get_final_document not implemented (GAPS.md STUB-001). "
            "Returning template binary where available."
        )
        if self.template_id and self.template_id.attachment_id:
            return self.template_id.attachment_id.datas
        return False

    @api.model
    def send_reminder(self):
        today = fields.Date.context_today(self)
        requests = self.search(
            [
                ("state", "=", "sent"),
                ("reminder", ">", 0),
            ]
        )
        for request in requests:
            try:
                if request.validity_date and request.validity_date < today:
                    request.write({"state": "expired"})
                    request._log_event("expired", "Request expired by validity date.")
                    continue
                if request.last_reminder:
                    elapsed = (today - request.last_reminder).days
                    if elapsed < request.reminder:
                        continue
                pending = request.request_item_ids.filtered(lambda item: item.state == "sent")
                if not pending:
                    continue
                for request_item in pending:
                    request._send_signature_request_mail(
                        request_item=request_item,
                        subject="Reminder: Signature request %s" % (request.name or request.reference),
                    )
                request.write({"last_reminder": today})
                request._log_event(
                    "reminder",
                    "Reminder sent to %s signer(s)." % len(pending),
                )
            except Exception:
                _logger.exception(
                    "sign: send_reminder failed for request %s",
                    request.id,
                )
        return True
