from datetime import datetime, timedelta

from odoo import api, fields, models


class MarketingCard(models.Model):
    """Mapping from a unique ID to a 'sharer' of a campaign. Storing state of sharing and their specific card."""
    _name = 'card.card'
    _description = 'Marketing Card'

    active = fields.Boolean('Active', default=True)
    campaign_id = fields.Many2one('card.campaign', required=True, ondelete="cascade")
    res_model = fields.Selection(related='campaign_id.res_model')
    res_id = fields.Many2oneReference('Record ID', model_field='res_model', required=True)
    image = fields.Image()
    requires_sync = fields.Boolean(help="Whether the image needs to be updated to match the campaign template.", default=True)
    share_status = fields.Selection([
        ('shared', 'Shared'),
        ('visited', 'Visited'),
    ])

    _sql_constraints = [
        ('campaign_record_unique', 'unique(campaign_id, res_id)',
         'Each record should be unique for a campaign'),
    ]

    @api.depends('res_model', 'res_id')
    def _compute_display_name(self):
        for model, cards in self.grouped('res_model').items():
            if not model:
                cards.display_name = ""
                continue
            self.env[model].browse(cards.mapped('res_id')).sudo().fetch(['display_name'])
            for card in cards:
                card.display_name = self.env[model].browse(card.res_id).sudo().display_name

    @api.depends('campaign_id')
    def _compute_res_model(self):
        """Compute the res_model once and never update it again."""
        for campaign, cards in self.grouped('campaign_id').items():
            cards.res_model = campaign.res_model

    @api.autovacuum
    def _gc_card(self):
        """Remove cards. Social networks are expected to cache the images on their side."""
        timedelta_days = self.env['ir.config_parameter'].get_param('marketing_card.card_image_cleanup_interval_days', 60)
        if not timedelta_days:
            return
        self.with_context({"active_test": False}).search([('write_date', '<=', datetime.now() - timedelta(days=timedelta_days))]).unlink()

    def _get_card_url(self):
        return self._get_path('card.jpg')

    def _get_redirect_url(self):
        return self._get_path('redirect')

    def _get_path(self, suffix):
        self.ensure_one()
        card_slug = self.env['ir.http']._slug(self)
        return f'{self.get_base_url()}/cards/{card_slug}/{suffix}'
