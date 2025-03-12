from odoo import _, api, fields, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    mailing_domain = fields.Char(compute='_compute_mailing_domain', readonly=False, store=True)
    event_id = fields.Many2one('event.event')

    @api.depends('card_campaign_id', 'mailing_model_name')
    def _compute_mailing_domain(self):
        super()._compute_mailing_domain()
        for mailing in self.filtered(lambda m: m.event_id and m.card_campaign_id and m.card_campaign_id.res_model.startswith('event.')):
            if 'event_id' in self.env[mailing.card_campaign_id.res_model]: 
                mailing.mailing_domain = repr([('event_id', '=', mailing.event_id.id)])
