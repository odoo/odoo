from ast import literal_eval
from markupsafe import Markup

from odoo import _, fields, models


class CardsCardShareMulti(models.TransientModel):
    _name = 'card.card.share.multi'
    _description = 'Email Marketing Cards Wizard'

    card_campaign_id = fields.Many2one('card.campaign', string='Marketing Card Campaign', ondelete='cascade', required=True)
    domain = fields.Char(default="[]")
    subject = fields.Char()
    message = fields.Html()
    res_model = fields.Selection(related='card_campaign_id.res_model')

    def action_send(self):
        self.ensure_one()
        target_records = self.env[self.res_model].search(literal_eval(self.domain) or [])
        composer = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'model': self.res_model,
            'res_ids': target_records.ids,
            'subject': self.subject,
            'body': Markup("""
                <p>{}</p>
                <a t-att-href="env['card.campaign'].browse(ctx['marketing_card_campaign_id'])._get_preview_url(object.id)" class="o_no_link_popover">{}</a>
            """).format(self.message, _("Your Card"))
        })

        # pre-create empty cards so that they may be used for tracking purposes
        self.card_campaign_id._get_or_create_cards_from_res_ids(target_records.ids)

        # template requires the campaign to be passed in through context
        composer.with_context(marketing_card_campaign_id=self.card_campaign_id.id)._action_send_mail()
        return {'type': 'ir.actions.act_window_close'}
