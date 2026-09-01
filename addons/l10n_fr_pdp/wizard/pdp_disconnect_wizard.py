from odoo import fields, models
from odoo.exceptions import UserError


class PdpDisconnectWizard(models.TransientModel):
    _name = 'pdp.disconnect.wizard'
    _description = 'Disconnect PDP Wizard'

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )

    def action_confirm(self):
        self.ensure_one()

        if not (edi_user := self.company_id.account_edi_proxy_client_ids.filtered(lambda u: u.proxy_type == 'pdp')):
            raise UserError(self.env._("No active PDP connection found for this company."))

        edi_user._peppol_deregister_participant()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._("Disconnected"),
                'message': self.env._("You have been successfully disconnected. You will remain registered as a receiver on the network for up to 12 months."),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }