from markupsafe import Markup

from odoo import fields, models, _


class L10nPtReprintReason(models.TransientModel):
    """
    Wizard allowing user to enter reason why document is printed more than once.
    """
    _name = 'l10n_pt.reprint.reason'
    _description = 'Reprint Reason Wizard'
    _check_company_auto = True

    reason = fields.Char(string='Reason for reprinting the document', required=True)

    def _prepare_reprint_message(self, document):
        return Markup(
            _("Reason for reprinting document %(document_name)s:<br/>%(reprint_reason)s")
        ) % {
            'document_name': document.name,
            'reprint_reason': self.reason,
        }

    def action_log_and_print(self):
        active_id = self.env.context.get('active_id')
        invoice = self.env['account.move'].browse(active_id)

        invoice.message_post(body=self._prepare_reprint_message(invoice))

        report_action = invoice.action_print_pdf()
        report_action['close_on_report_download'] = True
        return report_action

