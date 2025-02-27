from ast import literal_eval

from odoo import api, fields, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    mailing_domain = fields.Char(compute='_compute_mailing_domain', readonly=False, store=True)
    event_id = fields.Many2one('event.event', string='Related Event')

    @api.depends('card_campaign_id', 'event_id', 'mailing_model_name')
    def _compute_mailing_domain(self):
        super()._compute_mailing_domain()
        # we consider if the card campaign is based on an (allowed) model, from the event module, that has an "event_id" field
        # it's always relevant to limit the domain to the related event
        for mailing in self.filtered(lambda m: (
            m.event_id and m.card_campaign_id
            and m.card_campaign_id.res_model.startswith('event.')
            and m.card_campaign_id.res_model in (
                allowed_model_name for allowed_model_name, _ in m.card_campaign_id._get_model_selection()
            )
        )):
            if 'event_id' in self.env[mailing.card_campaign_id.res_model]:
                event_domain = [('event_id', '=', mailing.event_id.id)]
                try:
                    original_domain = literal_eval(mailing.mailing_domain or '[]')
                except ValueError:
                    original_domain = []
                if not any(leaf == event_domain for leaf in original_domain):
                    mailing.mailing_domain = repr(original_domain + event_domain)
