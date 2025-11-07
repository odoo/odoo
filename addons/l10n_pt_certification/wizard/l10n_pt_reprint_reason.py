from markupsafe import Markup

from odoo import _, fields, models


class L10nPtReprintReason(models.TransientModel):
    """
    Wizard prompting user to enter reason why document is printed more than once. It is a requirement
    for PT Certification that this reason be recorded, for example, in the chatter.
    """
    _name = 'l10n_pt.reprint.reason'
    _description = 'Reprint Reason Wizard'
    _check_company_auto = True

    reason = fields.Char(string='Reason for reprinting the document', required=True)

    def _get_report_action(self, model, documents, action_name=None):
        documents = documents.with_context(has_reprint_reason=True)
        if model == 'account.payment':
            return self.env.ref('account.action_report_payment_receipt').report_action(documents)
        # Action name is passed in the context when calling action_log_and_print, allowing the print flow to continue
        action = getattr(documents, action_name)
        return action()

    def action_log_and_print(self):
        active_ids = self.env.context.get('active_ids')
        model = self.env.context.get('active_model')
        documents = self.env[model].browse(active_ids)

        if model == 'account.move.send.wizard':
            # Wizard is used in `_get_report_action`, but reprint reason message needs to be posted to each document
            wizard = documents
            documents = documents.move_id
        else:
            wizard = None

        # Filter only documents that need a reprint reason to cover the cases where multiple
        # documents are printed at once, and not all are necessarily reprints
        for document in documents.filtered(lambda d: d.l10n_pt_print_version):
            msg = Markup(_("Reason for reprinting document %(name)s:<br/>%(reason)s",
                           name=document.name,
                           reason=self.reason))
            document.message_post(body=msg)

        report_action = self._get_report_action(model, wizard or documents, self._context.get('action_to_return'))
        report_action['close_on_report_download'] = True
        return report_action
