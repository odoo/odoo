from odoo import fields, models


class L10nEgEdiCancelWizard(models.TransientModel):
    _name = 'l10n_eg_edi.cancel.wizard'
    _description = 'Wizard to cancel an invoice in ETA'

    move_ids = fields.Many2many(comodel_name='account.move', required=True)
    l10n_eg_eta_cancellation_reason = fields.Char(string='ETA Reason', required=True)

    def action_cancel_invoice(self):
        self.ensure_one()
        self.move_ids._l10n_eg_edi_cancel_invoices(self.l10n_eg_eta_cancellation_reason, len(self.move_ids) == 1)
