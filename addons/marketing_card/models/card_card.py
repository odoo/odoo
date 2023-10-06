from datetime import datetime, timedelta

from odoo import api, fields, models


class MarketingCard(models.Model):
    """Mapping from a unique ID to a 'sharer' of a campaign. Storing state of sharing and their specific card."""
    _name = 'card.card'
    _description = 'Marketing Card'

    campaign_id = fields.Many2one('card.campaign', required=True, ondelete="cascade")
    res_model = fields.Selection(related='campaign_id.res_model')
    record_ref = fields.Reference(string='Record', selection='_selection_record_ref', compute='_compute_record_ref')
    res_id = fields.Many2oneReference('Record ID', model_field='res_model', required=True)
    image = fields.Image()
    share_status = fields.Selection([
        ('shared', 'Shared on Social Networks'),
        ('visited', 'Share URL Visited'),
    ])

    _sql_constraints = [
        ('campaign_record_unique', 'unique(campaign_id, res_id)',
         'Each record should be unique for a campaign'),
    ]

    @api.depends('res_model', 'res_id')
    def _compute_record_ref(self):
        for card in self:
            card.record_ref = f'{card.res_model},{card.res_id}'

    @api.autovacuum
    def _gc_card_url_images(self):
        """Remove images after a day. Social networks are expected to cache the images on their side."""
        timedelta_days = self.env['ir.config_parameter'].get_param('marketing_card.card_image_cleanup_interval_days', 1)
        if not timedelta_days:
            return
        self.search([('write_date', '<=', datetime.now() - timedelta(days=timedelta_days))]).image = False

    def _get_card_url(self, small=False):
        return self.campaign_id._get_card_path(self.res_id, 'card.jpg' + ('?small=1' if small else ''))

    def _get_redirect_url(self):
        return self.campaign_id._get_card_path(self.res_id, 'redirect')

    def _get_or_generate_image(self):
        # generate if not already stored
        if not self.image:
            self.image = self.campaign_id._get_image_b64(self.env[self.res_model].browse(self.res_id))
        return self.image

    @api.model
    def _selection_record_ref(self):
        return self.env['card.campaign']._fields['res_model']._description_selection(self.env)
