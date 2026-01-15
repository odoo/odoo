from odoo import models


class PortalShare(models.TransientModel):
    _inherit = 'portal.share'

    def action_send_mail(self):
        # Extend portal share to subscribe partners when sharing project tasks.
        result = super().action_send_mail()

        # Only subscribe partners if shared from project.task
        if self.res_model == 'project.task':
            self.resource_ref.message_subscribe(partner_ids=self.partner_ids.ids)

        return result
