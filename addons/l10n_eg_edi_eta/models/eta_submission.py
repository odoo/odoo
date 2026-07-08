from odoo import fields, models
from odoo.exceptions import UserError

ETA_SUBMISSION_STATES = [
    ('accepted', "Accepted"),
    ('rejected', "Rejected"),
    ('test', "Accepted (Test)"),
    ('cancel', "Cancelled"),
]


class L10nEgEdiEtaSubmission(models.Model):
    _name = 'l10n_eg_edi.eta.submission'
    _description = "ETA Submission Details"

    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    eta_document_uuid = fields.Char(string='Document UUID')
    eta_document_longid = fields.Char(string='Document Long ID')
    eta_submission_id = fields.Char(string='Submission ID')
    state = fields.Selection(
        selection=ETA_SUBMISSION_STATES,
        string='State',
    )
    message = fields.Char(string="Response Message")
    eta_json_filename = fields.Char(string="File")

    def action_retry(self):
        self.ensure_one()
        if alerts := self.move_id._get_l10n_eg_edi_alerts():
            return self.env['account.move.send']._raise_danger_alerts(alerts)

        if error := self.move_id._l10n_eg_eta_send_invoice(notify=True):
            if isinstance(error.get('error'), dict):
                message = error['error'].get('message')
            else:
                message = error.get('error', 'No description found')
            raise UserError(self.env._("Error occured while trying to retry sending invoice: %s", message))

    def action_resign(self):
        self.ensure_one()
        if alerts := self.move_id._get_l10n_eg_edi_alerts():
            return self.env['account.move.send']._raise_danger_alerts(alerts)
        return self.move_id.action_post_sign_invoices()
