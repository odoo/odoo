import json
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

    move_id = fields.Many2one(comodel_name='account.move', string="Invoice", readonly=True)
    eta_document_uuid = fields.Char(string="Document UUID")
    eta_document_longid = fields.Char(string="Document Long ID")
    eta_submission_id = fields.Char(string="Submission ID")
    state = fields.Selection(
        selection=ETA_SUBMISSION_STATES,
        string="State",
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

    def _set_eta_long_id_from_response_json(self):
        """
        This method is used for upgrade, to migrate the old data of ETA submission to the ETA logs.
        The long_id is not stored in account_move, so we need to set it from the response stored in l10n_eg_eta_json_doc_file.
        """
        self.ensure_one()
        if not self.move_id.l10n_eg_eta_json_doc_file:
            return
        response_json = json.loads(self.move_id.l10n_eg_eta_json_doc_file.content)
        if response_json.get('response', {}).get('l10n_eg_long_id'):
            self.eta_document_longid = response_json['response']['l10n_eg_long_id']
