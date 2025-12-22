from odoo import models, _


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        res = super().action_send_mail()
        if self.filtered(lambda l: l.model == 'pos.order'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Email triggered successfully!'),
                    'type': 'success',
                    'next': res
                }
            }
        return res
