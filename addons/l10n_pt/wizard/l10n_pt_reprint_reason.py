from markupsafe import Markup

from odoo import _, fields, models


class L10nPtReprintReason(models.TransientModel):
    """
    Wizard prompting user to enter reason why document is printed more than once.
    """
    _name = 'l10n_pt.reprint.reason'
    _description = 'Reprint Reason Wizard'
    _check_company_auto = True

    reason = fields.Char(string='Reason for reprinting the document', required=True)

    def _get_report_action(self, model, documents):
        if model == 'account.move':
            return documents.action_print_pdf()
        elif model == 'account.payment':
            return self.env.ref('account.action_report_payment_receipt').report_action(documents)

    def action_log_and_print(self):
        active_ids = self._context.get('active_ids')
        model = self._context.get('active_model')
        documents = self.env[model].browse(active_ids)

        for document in documents:
            msg = Markup(_("Reason for reprinting document %(name)s:<br/>%(reason)s",
                           name=document.name,
                           reason=self.reason))
            document.message_post(body=msg)

        report_action = self._get_report_action(model, documents)
        report_action['close_on_report_download'] = True
        return report_action
