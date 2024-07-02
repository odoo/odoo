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
    is_shared = fields.Boolean('Shared on Social Networks')
    is_visited = fields.Boolean('Share URL Visited')

    _sql_constraints = [
        ('campaign_record_unique', 'unique(campaign_id, res_id)',
         'Each record should be unique for a campaign'),
    ]

    @api.depends('res_model', 'res_id')
    def _compute_record_ref(self):
        for card in self:
            card.record_ref = f'{card.res_model},{card.res_id}'

    @api.autovacuum
    def _gc_card_urls(self):
        """Remove stored image after a while."""
        self.search([('write_date', '<=', datetime.now() - timedelta(days=30))]).image = False

    def _get_preview_url(self):
        self.ensure_one()
        hash_token = self.campaign_id._generate_card_hash_token(self.res_id)
        return f'{self.get_base_url()}/cards/{self.campaign_id.id}/{self.res_id}/{hash_token}/preview'

    def _get_card_url(self, small=False):
        self.ensure_one()
        hash_token = self.campaign_id._generate_card_hash_token(self.res_id)
        url = f'{self.get_base_url()}/cards/{self.campaign_id.id}/{self.res_id}/{hash_token}/card.jpg'
        if small:
            url += '?small=1'
        return url

    def _get_redirect_url(self):
        self.ensure_one()
        hash_token = self.campaign_id._generate_card_hash_token(self.res_id)
        return f'{self.get_base_url()}/cards/{self.campaign_id.id}/{self.res_id}/{hash_token}/redirect'

    def _get_or_generate_image(self):
        # compute if not already stored
        if not self.image:
            self.image = self.campaign_id._get_images_b64(records=self.env[self.res_model].browse(self.res_id))[self.res_id]
        return self.image

    @api.model
    def _selection_record_ref(self):
        groups = self.env['card.campaign'].sudo()._read_group(
            domain=[('res_model', '!=', False)],
            groupby=['res_model'],
        )
        model_names = list({model_name for model_name, *_ in groups})
        models = self.env['ir.model'].sudo().search_fetch([('model', 'in', model_names)], ['model', 'name'])
        return [(model.model, model.name) for model in models]
