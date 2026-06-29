from odoo import fields, models


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
        model = self._context.get('active_model')
        records = self.env[model].browse(self._context.get('active_ids'))
        if model == 'account.move':
            res = records.with_context(allow_draft_hashed_entries=True).button_cancel()
        elif model == 'account.payment':
            res = records.action_cancel()
        records.l10n_pt_cancel_reason = self.l10n_pt_cancel_reason.strip()
        # Reset print version, since cancelled documents also have an Original and Reprint version
        records.l10n_pt_print_version = None
        return res
