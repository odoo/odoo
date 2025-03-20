from odoo import fields, models


class EventTrackPostWizard(models.TransientModel):
    _inherit = 'event.track.post.wizard'

    card_campaign_id = fields.Many2one('card.campaign', string='Thumbnail Campaign', domain=f"[('res_model', '=', 'event.track'), ('card_dimension_id.ratio', '=', {round(16 / 9, 2)})]")

    def action_post(self):
        self.ensure_one()
        if self.card_campaign_id:
            active_ids = self.env.context.get('active_ids', [])
            if active_ids:
                self.card_campaign_id._update_cards([('id', 'in', active_ids)])
            self.env.cr.commit()
        return super().action_post()

    def _prepare_youtube_post_values(self, track):
        post_values = super()._prepare_youtube_post_values(track)
        if self.card_campaign_id:
            card = self.env['card.card'].search([('res_model', '=', 'event.track'), ('res_id', '=', track.id)], limit=1)
            if card:
                post_values['thumbnail'] = card.image
        return post_values
