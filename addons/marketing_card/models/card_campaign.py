import base64
from lxml import html

from odoo import _, api, fields, models, exceptions

from .card_template import TEMPLATE_DIMENSIONS


class CardCampaign(models.Model):
    _name = 'card.campaign'
    _description = 'Marketing Card Campaign'
    _inherit = ['mail.activity.mixin', 'mail.render.mixin', 'mail.thread']
    _order = 'id DESC'

    def _default_card_template_id(self):
        return self.env['card.template'].search([], limit=1)

    def _get_model_selection(self):
        """Hardcoded list of models, checked against actually-present models."""
        allowed_models = ['res.partner', 'event.track', 'event.booth', 'event.registration']
        models = self.env['ir.model'].sudo().search_fetch([('model', 'in', allowed_models)], ['model', 'name'])
        return [(model.model, model.name) for model in models]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    body_html = fields.Html(related='card_template_id.body', render_engine="qweb")

    card_count = fields.Integer(compute='_compute_card_stats')
    card_click_count = fields.Integer(compute='_compute_card_stats')
    card_share_count = fields.Integer(compute='_compute_card_stats')

    card_template_id = fields.Many2one('card.template', string="Design", default=_default_card_template_id, required=True)
    image_preview = fields.Image(compute='_compute_image_preview', readonly=True, store=True, attachment=False)
    link_tracker_id = fields.Many2one('link.tracker', ondelete="restrict")
    res_model = fields.Char(string="Model Name", compute="_compute_res_model", store=True)

    post_suggestion = fields.Text(help="Description below the card and default text when sharing on X")
    preview_record_ref = fields.Reference(string="Preview On", selection="_get_model_selection", required=True)
    tag_ids = fields.Many2many('card.campaign.tag', string='Tags')
    target_url = fields.Char(string='Post Link')
    target_url_click_count = fields.Integer(related="link_tracker_id.count")

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, domain="[('share', '=', False)]")

    reward_message = fields.Html(string='Thanks to You Message')
    reward_target_url = fields.Char(string='Reward Link')
    request_title = fields.Char('Request', default=_('Help us share the news'))
    request_description = fields.Text('Request Description')

    # Static Content fields
    content_background = fields.Image('Background')
    content_image1 = fields.Char('Dynamic Image 1')
    content_image2 = fields.Char('Dynamic Image 2')
    content_button = fields.Char('Button')

    # Dynamic Content fields
    content_header = fields.Char('Header')
    content_header_dyn = fields.Boolean('Is Dynamic Header')
    content_header_path = fields.Char('Header Path')
    content_header_color = fields.Char('Header Color')

    content_sub_header = fields.Char('Sub-Header')
    content_sub_header_dyn = fields.Boolean('Is Dynamic Sub-Header')
    content_sub_header_path = fields.Char('Sub-Header Path')
    content_sub_header_color = fields.Char('Sub Header Color')

    content_section = fields.Char('Section')
    content_section_dyn = fields.Boolean('Is Dynamic Section')
    content_section_path = fields.Char('Section Path')

    content_sub_section1 = fields.Char('Sub-Section 1')
    content_sub_section1_dyn = fields.Boolean('Is Dynamic Sub-Section 1')
    content_sub_section1_path = fields.Char('Sub-Section 1 Path')

    content_sub_section2 = fields.Char('Sub-Section 2')
    content_sub_section2_dyn = fields.Boolean('Is Dynamic Sub-Section 2')
    content_sub_section2_path = fields.Char('Sub-Section 2 Path')

    def _compute_card_stats(self):
        cards_by_status_count = self.env['card.card']._read_group(
            domain=[('campaign_id', 'in', self.ids)],
            groupby=['campaign_id', 'share_status'],
            aggregates=['__count'],
            order='campaign_id ASC',
        )
        self.update({
            'card_count': 0,
            'card_click_count': 0,
            'card_share_count': 0,
        })
        for campaign, status, card_count in cards_by_status_count:
            # shared cards are implicitly visited
            if status == 'shared':
                campaign.card_share_count += card_count
            if status:
                campaign.card_click_count += card_count
            campaign.card_count += card_count

    @api.depends('preview_record_ref', 'body_html', 'content_background', 'content_image1', 'content_image2', 'content_button', 'content_header',
        'content_header_dyn', 'content_header_path', 'content_header_color', 'content_sub_header',
        'content_sub_header_dyn', 'content_sub_header_path', 'content_section', 'content_section_dyn',
        'content_section_path', 'content_sub_section1', 'content_sub_section1_dyn', 'content_sub_header_color',
        'content_sub_section1_path', 'content_sub_section2', 'content_sub_section2_dyn', 'content_sub_section2_path')
    def _compute_image_preview(self):
        for campaign in self:
            if campaign.preview_record_ref and campaign.preview_record_ref.exists():
                image = campaign._get_image_b64(campaign.preview_record_ref)
            else:
                image = campaign._get_generic_image_b64()
            campaign.image_preview = image

    @api.depends('preview_record_ref')
    def _compute_res_model(self):
        for campaign in self:
            if campaign.preview_record_ref:
                campaign.res_model = campaign.preview_record_ref._name
            else:
                campaign.res_model = 'res.partner'

    @api.model_create_multi
    def create(self, create_vals):
        utm_source = self.env.ref('marketing_card.utm_source_marketing_card', raise_if_not_found=False)
        link_trackers = self.env['link.tracker'].sudo().create([
            {
                'url': vals.get('target_url') or self.env['card.campaign'].get_base_url(),
                'title': vals['name'],  # not having this will trigger a request in the create
                'source_id': utm_source.id if utm_source else None,
                'label': f"marketing_card_campaign_{vals.get('name', '')}_{fields.Datetime.now()}",
            }
            for vals in create_vals
        ])
        return super().create([{
            **vals,
            'link_tracker_id': link_tracker_id,
        } for vals, link_tracker_id in zip(create_vals, link_trackers.ids)])

    def write(self, vals):
        link_tracker_vals = {}
        if 'target_url' in vals:
            link_tracker_vals['url'] = vals['target_url'] or self.env['card.campaign'].get_base_url()
        if link_tracker_vals:
            self.link_tracker_id.sudo().write(link_tracker_vals)
        return super().write(vals)

    def action_view_cards(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("marketing_card.cards_card_action") | {
            'context': {},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_view_cards_clicked(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("marketing_card.cards_card_action") | {
            'context': {'search_default_filter_visited': True},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_view_cards_shared(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("marketing_card.cards_card_action") | {
            'context': {'search_default_filter_shared': True},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_preview(self):
        self.ensure_one()
        if not self.preview_record_ref.id:
            raise exceptions.UserError(_('Please set a preview record'))
        card = self.env['card.card'].create({
            'campaign_id': self.id,
            'res_id': self.preview_record_ref.id,
            'name': self.preview_record_ref.display_name,
            'active': False})
        return {'type': 'ir.actions.act_url', 'url': card._get_path('preview'), 'target': 'new'}

    def action_share(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Cards'),
            'res_model': 'card.card.share',
            'context': {'default_card_campaign_id': self.id, 'default_subject': self.name},
            'views': [[False, 'form']],
            'target': 'new',
        }

    # ==========================================================================
    # Image generation
    # ==========================================================================

    def _get_image_b64(self, record):
        if not self.card_template_id.body:
            return ''

        image_bytes = self.env['ir.actions.report']._run_wkhtmltoimage(
            [self._render_field('body_html', record.ids, add_context={'card_campaign': self})[record.id]],
            *TEMPLATE_DIMENSIONS
        )[0]
        return image_bytes and base64.b64encode(image_bytes)

    def _get_generic_image_b64(self):
        """Render a single preview image with no record."""
        rendered_body = self.env['ir.qweb']._render(
            html.fromstring(self.body_html),
            self._render_eval_context() | {
                'card_campaign': self,
                'preview_values': {
                    'header': _('Title'),
                    'subheader': _('Subtitle'),
                }
            },
            raise_on_code=False,
        )
        image_bytes = self.env['ir.actions.report']._run_wkhtmltoimage(
            [rendered_body],
            *TEMPLATE_DIMENSIONS
        )[0]
        return image_bytes and base64.b64encode(image_bytes)

    # ==========================================================================
    # Card creation
    # ==========================================================================

    def _get_or_create_cards_from_res_ids(self, res_ids):
        """Create missing cards for the given ids."""
        self.ensure_one()
        card_obj = self.env['card.card']
        cards = card_obj.search_fetch([('campaign_id', '=', self.id), ('res_id', 'in', res_ids)], ['res_id'])
        records = self.env[self.res_model].browse(set(res_ids) - set(cards.mapped('res_id')))
        return cards + card_obj.create([{'campaign_id': self.id, 'res_id': record.id, 'name': record.display_name} for record in records])

    # ==========================================================================
    # Mail render mixin / Render utils
    # ==========================================================================

    @api.depends('res_model')
    def _compute_render_model(self):
        """ override for mail.render.mixin """
        for campaign in self:
            campaign.render_model = campaign.res_model

    def _get_card_element_values(self, record, preview_values):
        """Helper to get the right value for dynamic fields."""
        self.ensure_one()
        result = {
            'image1': self.content_image1 and record.mapped(self.content_image1)[0] or False,
            'image2': self.content_image2 and record.mapped(self.content_image2)[0] or False
        }
        for el in ('header', 'sub_header', 'section', 'sub_section1', 'sub_section2'):
            if not self['content_' + el + '_dyn']:
                result[el] = self['content_' + el]
            else:
                try:
                    m = record.mapped(self['content_' + el + '_path'])
                    result[el] = m and m[0] or False
                except AttributeError:
                    # for generic image, or if field incorrect, return name of field
                    result[el] = self['content_' + el + '_path']
        return result

    def _get_url_from_res_id(self, res_id, suffix='preview'):
        card = self.env['card.card'].search([('campaign_id', '=', self.id), ('res_id', '=', res_id)])
        return card and card._get_path(suffix) or self.target_url
