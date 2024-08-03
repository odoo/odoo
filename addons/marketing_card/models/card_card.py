from datetime import datetime, timedelta

from odoo import api, fields, models


class MarketingCard(models.Model):
    """Mapping from a unique ID to a 'sharer' of a campaign. Storing state of sharing and their specific card."""
    _name = 'card.card'
    _description = 'Marketing Card'

    name = fields.Char('Name')
    active = fields.Boolean('Active', default=True)
    campaign_id = fields.Many2one('card.campaign', required=True, ondelete="cascade")
    res_model = fields.Char(related='campaign_id.res_model')
    res_id = fields.Many2oneReference('Record ID', model_field='res_model', required=True)
    image = fields.Image(compute='_get_image', store=True)
    share_status = fields.Selection([
        ('sent', 'Sent'),
        ('visited', 'Visited'),
        ('shared', 'Shared'),
    ], default='sent', required=True)

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

    @api.depends('res_model', 'res_id', 'campaign_id')
    def _get_image(self):
        for card in self:
            if not (card.res_model or card.res_id or card.campaign_id):
                card.image = None
            else:
                record = card.env[card.res_model].browse(card.res_id)
                card.image = card.campaign_id._get_image_b64(record)

    def _get_path(self, suffix):
        self.ensure_one()
        return f'{self.get_base_url()}/cards/{self.id}/{suffix}'
