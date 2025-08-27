from datetime import datetime, timedelta

from odoo import api, fields, models


class CardCard(models.Model):
    """Mapping from a unique ID to a 'sharer' of a campaign. Storing state of sharing and their specific card."""
    _name = 'card.card'
    _description = 'Marketing Card'

    active = fields.Boolean('Active', default=True)
    campaign_id = fields.Many2one('card.campaign', required=True, index=True, ondelete="cascade")
    res_model = fields.Selection(related='campaign_id.res_model')
    res_id = fields.Many2oneReference('Record ID', model_field='res_model', required=True)
    image = fields.Image()
    requires_sync = fields.Boolean(help="Whether the image needs to be updated to match the campaign template.", default=True)
    share_status = fields.Selection([
        ('shared', 'Shared'),
        ('visited', 'Visited'),
    ])

    link_tracker_id = fields.Many2one('link.tracker', ondelete="restrict")
    target_url = fields.Char(string='Post Link', compute='_compute_target_url', store=True)
    target_url_click_count = fields.Integer(related="link_tracker_id.count")

    _campaign_record_unique = models.Constraint(
        'unique(campaign_id, res_id)',
        'Each record should be unique for a campaign',
    )

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

    @api.depends('res_model', 'res_id')
    def _compute_target_url(self):
        for model, cards in self.grouped('res_model').items():
            if not model:
                cards.target_url = False
                continue
            if any(cards.campaign_id.mapped('show_target_url_dyn')):
                self.env[model].browse(cards.mapped('res_id')).sudo().fetch(['website_url'])
            for card in cards:
                target_url_dyn = self.env[model].browse(card.res_id).sudo().website_url if card.campaign_id.show_target_url_dyn else False
                card.target_url = target_url_dyn or self.campaign_id.target_url or self.env['card.campaign'].get_base_url()
                card.link_tracker_id.url = card.target_url
                card.link_tracker_id.title = f"{card.campaign_id.name} - {card.display_name}"

    @api.model_create_multi
    def create(self, vals_list):
        utm_source = self.env.ref('marketing_card.utm_source_marketing_card', raise_if_not_found=False)
        campaign_ids = {c.id: c for c in self.env['card.campaign'].browse([v['campaign_id'] for v in vals_list])}
        link_trackers = self.env['link.tracker'].sudo().create([
            {
                'url': campaign_ids[vals['campaign_id']].target_url or self.env['card.campaign'].get_base_url(),  # Use campaign target url by default
                'title': f"{campaign_ids[vals['campaign_id']].name} - ({campaign_ids[vals['campaign_id']].res_model},{vals['res_id']})",  # not having this will trigger a request in the create
                'source_id': utm_source.id if utm_source else None,
                'label': f"marketing_card_campaign_{campaign_ids[vals['campaign_id']]}_{campaign_ids[vals['campaign_id']].res_model}_{vals['res_id']}_{fields.Datetime.now()}",
            }
            for vals in vals_list
        ])
        return super().create([{
            **vals,
            'link_tracker_id': link_tracker_id,
        } for vals, link_tracker_id in zip(vals_list, link_trackers.ids)])

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
