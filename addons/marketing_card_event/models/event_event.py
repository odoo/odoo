from odoo import _, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    def action_open_card_mailing(self):
        self.ensure_one()
        view = self.env.ref('marketing_card_event.mailing_mailing_view_form_event_send_card', False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Cards'),
            'res_model': 'mailing.mailing',
            'context': {
                'default_subject': self.name,
                'default_model_id': self.env['ir.model']._get_id('event.attendee'),
                'default_body_arch': self.env['card.campaign']._action_share_get_default_body(),
                'default_event_id': self.id,
            },
            'views': [[view and view.id, 'form']],
            'target': 'new',
        }
