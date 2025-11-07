from odoo import fields, models
from odoo.exceptions import UserError


class L10nPtCancelWizard(models.TransientModel):
    _name = "l10n_pt.cancel"
    _description = "Wizard to allow the cancellation of documents"

    l10n_pt_cancel_reason = fields.Char(
        string="Cancel Reason",
        required=True,
        help="Reason to cancel this document.",
    )

    def button_cancel(self):
        self.ensure_one()
        model = self.env.context.get('active_model')
        if model not in ('account.move', 'account.payment'):
            raise UserError(self.env._("Only invoices and receipts can be cancelled with this wizard."))
        records = self.env[model].browse(self.env.context.get('active_ids'))
        res = records.button_cancel() if model == 'account.move' else records.action_cancel()
        records.l10n_pt_cancel_reason = self.l10n_pt_cancel_reason.strip()
        return res
