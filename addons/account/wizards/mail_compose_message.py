from ast import literal_eval

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    # Field to annotate the date for account reports.
    # This is set by passing a default in the context when opening the wizard from a message.
    account_reports_annotation_date = fields.Date(string="Annotated For")

    # Set only via a `default_account_reports_finalize_payment` context key, passed by
    # account.return's "send payment instructions" flow (action_send_email_instructions).
    # Guards _action_finalize_payment() so a plain chatter reply on an account.return
    # cannot silently flip its state to Paid.
    account_reports_finalize_payment = fields.Boolean()

    @_debug.perf.timed
    def _prepare_schedule_message_post_values(self, post_values):
        return {
            **super()._prepare_schedule_message_post_values(post_values),
            "account_reports_annotation_date": self.account_reports_annotation_date,
        }

    def _annotate_sent_messages(self, annotation_date, messages):
        if annotation_date:
            self.env["account.report.annotation"].sudo().create(
                [{"message_id": msg.id, "date": annotation_date} for msg in messages]
            )

    @_debug.perf.timed
    def _action_send_mail_comment(self, res_ids):
        # Read the date before the super call; it invalidates the ORM cache.
        _debug.lifecycle("_action_send_mail_comment", records=self)
        annotation_date = self.account_reports_annotation_date
        messages = super()._action_send_mail_comment(res_ids)
        self._annotate_sent_messages(annotation_date, messages)
        return messages

    @_debug.perf.timed
    def _action_send_mail(self, auto_commit=False):
        # Read the date before the super call; it invalidates the ORM cache.
        _debug.lifecycle("_action_send_mail", records=self)
        annotation_date = self.account_reports_annotation_date
        mails, messages = super()._action_send_mail(auto_commit=auto_commit)
        self._annotate_sent_messages(annotation_date, messages)
        return mails, messages

    @_debug.perf.timed
    def action_send_mail(self):
        _debug.lifecycle("action_send_mail", records=self)
        if self.model != "account.return":
            _debug.logic("send_mail_delegated", records=self, model=self.model)
            return super().action_send_mail()

        return_id = self.env["account.return"].browse(literal_eval(self.res_ids))
        _debug.logic(
            "return_mail_sending",
            tax_return=return_id,
            finalize_payment=self.account_reports_finalize_payment,
        )
        if self.account_reports_finalize_payment:
            return_id._action_finalize_payment()
        super().action_send_mail()
        return {
            "type": "ir.actions.client",
            "tag": "action_return_refresh",
            "params": {
                "next_action": {"type": "ir.actions.act_window_close"},
                "return_ids": return_id.ids,
            },
        }
