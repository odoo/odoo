from markupsafe import Markup

from odoo import fields, models
from odoo.exceptions import UserError


class L10nPtReprintReason(models.TransientModel):
    """
    Asks why a document is printed again: PT certification requires the reason to be recorded, here
    in the document's chatter.
    """
    _name = 'l10n_pt.reprint.reason'
    _description = 'Reprint Reason Wizard'
    _check_company_auto = True

    reason = fields.Char(string='Reason for reprinting the document', required=True)

    def _l10n_pt_reprint_actions(self):
        """The print actions the wizard resumes once the reason is given, by the model it was opened from."""
        return {
            'account.move': {'action_print_pdf'},
            'account.move.send.wizard': {'action_send_and_print'},
        }

    def _get_report_action(self, model, documents, action_name=None):
        documents = documents.with_context(has_reprint_reason=True)
        if model == 'account.payment':
            return self.env.ref('account.action_report_payment_receipt').report_action(documents)
        # The action to resume comes from the context, i.e. from the client: only a known print action is run.
        if action_name not in self._l10n_pt_reprint_actions().get(model, ()):
            raise UserError(self.env._("These documents cannot be printed from here."))
        return getattr(documents, action_name)()

    def action_log_and_print(self):
        active_ids = self.env.context.get('active_ids')
        model = self.env.context.get('active_model')
        documents = self.env[model].browse(active_ids)

        if model == 'account.move.send.wizard':
            # The send wizard resumes the print, but the reason is posted on its invoices.
            wizard = documents
            documents = documents.move_id
        else:
            wizard = None

        # Of several documents printed at once, only the reprints get the reason.
        for document in documents.filtered(lambda d: d.l10n_pt_print_version):
            msg = self.env._("Reason for reprinting document %(name)s:", name=document.name) + Markup("<br/>") + (self.reason or "")
            document.message_post(body=msg)

        report_action = self._get_report_action(model, wizard or documents, self.env.context.get('action_to_return'))
        report_action['close_on_report_download'] = True
        return report_action
