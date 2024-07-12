from odoo import fields, models


class L10nPtCancelWizard(models.TransientModel):
    _inherit = "l10n_pt.cancel"

    # What annulling the documents means, shown before they are (e.g. an annulment the AT needs too).
    l10n_pt_notice = fields.Text(readonly=True)

    def button_cancel(self):
        self.ensure_one()
        if self.env.context.get('model') == 'stock.picking':
            pickings = self.env['stock.picking'].browse(self.env.context.get('picking_ids'))
            issued = pickings._l10n_pt_issued().filtered(lambda p: p.state not in ('done', 'cancel'))
            issued.l10n_pt_cancel_reason = self.l10n_pt_cancel_reason.strip()
            return pickings.action_cancel()
        return super().button_cancel()
