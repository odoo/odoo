from odoo import api, models
from odoo.exceptions import UserError
from odoo.addons.l10n_fr_pdp.models.pdp_flow import FLOW_SENT_STATES


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _l10n_fr_pdp_no_delete_fro_sent_flow(self):
        res_ids = self.filtered(lambda att: att.res_model == 'l10n.fr.pdp.reports.flow').mapped('res_id')
        if res_ids and self.env['l10n.fr.pdp.reports.flow'].search_count(
            [('id', 'in', res_ids), ('state', 'in', FLOW_SENT_STATES)],
            limit=1,
        ):
            raise UserError(self.env._("You can't delete an attachment linked to a sent Flow."))
