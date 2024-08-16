from ast import literal_eval
from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools import plaintext2html


class CardsCardShare(models.TransientModel):
    _name = 'card.card.share'
    _description = 'Email Marketing Cards Wizard'

    def _default_message(self):
        return plaintext2html(_(
            "Hello everyone\n\n"
            """Here's the link to advertise your participation.
            Your help with this promotion would be greatly appreciated!\n\n"""
            "Many thanks"
        ))

    card_campaign_id = fields.Many2one('card.campaign', string='Marketing Card Campaign', ondelete='cascade', required=True)
    domain = fields.Char(default="[]")
    subject = fields.Char()
    message = fields.Html(default=_default_message)
    res_model = fields.Selection(related='card_campaign_id.res_model')

    def action_send(self):
        self.ensure_one()
        target_records = self.env[self.res_model].search(literal_eval(self.domain) or [])
        composer = self.env['mail.compose.message'].create({
            'composition_mode': 'mass_mail',
            'model': self.res_model,
            'res_ids': target_records.ids,
            'subject': self.subject,
            'body': Markup(
                "<div>{}</div>\n"
                """<a t-att-href="env['card.campaign'].browse(ctx['marketing_card_campaign_id'])._get_preview_url_from_res_id(object.id)" class="o_no_link_popover">{}</a>"""
            ).format(self.message or '', _("Your Card"))
        })

        # pre-create empty cards so that they may be used for tracking purposes
        self.card_campaign_id.sudo()._get_or_create_cards_from_res_ids(target_records.ids)

        # template requires the campaign to be passed in through context
        composer.with_context(marketing_card_campaign_id=self.card_campaign_id.id)._action_send_mail()
        return {'type': 'ir.actions.act_window_close'}
