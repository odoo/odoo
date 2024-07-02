from lxml import html
import base64
import hashlib

from odoo import _, api, Command, fields, models

from ..utils.image_utils import scale_image_b64
from .card_template import TEMPLATE_DIMENSIONS

class CardCampaign(models.Model):
    _name = 'card.campaign'
    _description = 'Marketing Card Campaign'
    _inherit = ['mail.activity.mixin', 'mail.render.mixin', 'mail.thread']
    _order = 'id DESC'

    def _default_card_template_id(self):
        return self.env['card.template'].search([], limit=1)

    def default_get(self, fields_list):
        default_vals = super().default_get(fields_list)
        if 'element_ids' in fields_list and 'element_ids' not in default_vals:
            default_vals.setdefault('element_ids', [
                Command.create({'role': 'background', 'render_type': 'image'}),
                Command.create({'role': 'header', 'render_type': 'text'}),
                Command.create({'role': 'subheader', 'render_type': 'text'}),
                Command.create({'role': 'section_1', 'render_type': 'text'}),
                Command.create({'role': 'subsection_1', 'render_type': 'text'}),
                Command.create({'role': 'subsection_2', 'render_type': 'text'}),
                Command.create({'role': 'button', 'render_type': 'text'}),
                Command.create({'role': 'image_1', 'render_type': 'image'}),
                Command.create({'role': 'image_2', 'render_type': 'image'}),
            ])
        return default_vals

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    body_html = fields.Html(related='card_template_id.body', render_engine="qweb")

    card_ids = fields.One2many('card.card', inverse_name='campaign_id')
    card_count = fields.Integer(compute='_compute_card_count')
    card_click_count = fields.Integer(compute='_compute_card_click_count')
    card_share_count = fields.Integer(compute='_compute_card_share_count')

    card_template_id = fields.Many2one('card.template', string="Design", default=_default_card_template_id)
    element_ids = fields.One2many('card.campaign.element', inverse_name='campaign_id', copy=True)
    image = fields.Image(compute='_compute_image', readonly=True, store=True, attachment=False)
    link_tracker_id = fields.Many2one('link.tracker', ondelete="restrict")
    res_model = fields.Selection(string="Model Name", selection=[('res.partner', 'Contact')], required=True, default="res.partner")

    post_suggestion = fields.Text(help="Default text when sharing on X")
    tag_ids = fields.Many2many('card.campaign.tag', string='Tags')
    target_url = fields.Char(string='Shared Link')
    target_url_click_count = fields.Integer(related="link_tracker_id.count")
    target_url_redirected = fields.Char(compute='_compute_target_url_redirected')
    thanks_message = fields.Html(string='Thanks to You Message')
    thanks_redirection = fields.Char(string='Redirect Address')

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, domain="[('share', '=', False)]")
    utm_campaign_id = fields.Many2one('utm.campaign', string='UTM Campaign', ondelete='set null')

    @api.depends('card_ids')
    def _compute_card_count(self):
        for campaign in self:
            campaign.card_count = len(campaign.card_ids)

    @api.depends('card_ids.is_visited')
    def _compute_card_click_count(self):
        visited_count_from_campaign = self.env['card.card']._read_group(
            domain=[('campaign_id', 'in', self.ids), ('is_visited', '=', True)],
            groupby=['campaign_id'],
            aggregates=['__count']
        )
        self.card_click_count = 0
        for campaign, count in visited_count_from_campaign:
            campaign.card_click_count = count

    @api.depends('card_ids.is_shared')
    def _compute_card_share_count(self):
        shared_count_from_campaign = self.env['card.card']._read_group(
            domain=[('campaign_id', 'in', self.ids), ('is_shared', '=', True)],
            groupby=['campaign_id'],
            aggregates=['__count']
        )
        self.card_share_count = 0
        for campaign, count in shared_count_from_campaign:
            campaign.card_share_count = count

    @api.depends('body_html', 'card_template_id.body', 'element_ids')
    def _compute_image(self):
        for campaign in self.filtered('card_template_id.body').filtered('element_ids'):
            rendered_body = self.env['ir.qweb']._render(
                html.fromstring(campaign.body_html),
                campaign._campaign_render_eval_context() | {
                    'preview_values': {
                        'header': _('Title'),
                        'subheader': _('Subtitle'),
                    }
                },
                raise_on_code=False,
            )
            image = self.env['ir.actions.report']._run_wkhtmltoimage(
                [rendered_body],
                *TEMPLATE_DIMENSIONS
            )[0]
            # scaled image for reduced network load
            campaign.image = scale_image_b64(base64.b64encode(image), 0.5)

    def _compute_render_model(self):
        for campaign in self:
            campaign.render_model = campaign.res_model

    @api.depends('link_tracker_id.short_url')
    def _compute_target_url_redirected(self):
        for campaign in self:
            campaign.target_url_redirected = campaign.link_tracker_id.short_url or campaign.target_url or campaign.get_base_url()

    @api.model_create_multi
    def create(self, create_vals):
        utm_source = self.env.ref('marketing_card.utm_source_marketing_card', raise_if_not_found=False)
        utm_campaigns = self.env['utm.campaign'].create([{
            'title': vals['name'],
            'user_id': vals.get('user_id'),
        } for vals in create_vals])
        link_trackers = self.env['link.tracker'].create([
            {
                'url': vals.get('target_url') or self.get_base_url(),
                'title': vals['name'],  # not having this will trigger a request in the create
                'source_id': utm_source.id if utm_source else None,
                'campaign_id': utm_campaign.id,
            }
            for vals, utm_campaign in zip(create_vals, utm_campaigns)
        ])
        return super().create([{
            **vals,
            'link_tracker_id': link_tracker_id,
            'utm_campaign_id': utm_campaign_id,
        } for vals, link_tracker_id, utm_campaign_id in zip(
            create_vals, link_trackers.ids, utm_campaigns.ids
        )])

    def write(self, vals):
        link_tracker_vals = {}
        utm_campaign_vals = {}
        if 'utm_campaign_id' in vals:
            link_tracker_vals['campaign_id'] = self.utm_campaign_id.id
        if 'target_url' in vals:
            link_tracker_vals['url'] = self.target_url or self.get_base_url()
        if 'name' in vals:
            utm_campaign_vals['title'] = self.name
        if 'user_id' in vals:
            utm_campaign_vals['user_id'] = self.user_id.id
        if link_tracker_vals:
            self.link_tracker_id.write(link_tracker_vals)
        if utm_campaign_vals:
            self.utm_campaign_id.write(utm_campaign_vals)
        return super().write(vals)

    def action_open_card_share(self):
        """Open card share dialog."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Share Link'),
            'res_model': 'card.card.share',
            'views': [[False, 'form']],
            'context': {
                'default_campaign_id': self.id,
                'dialog_size': 'medium',
            },
            'target': 'new',
        }

    def action_show_cards(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("marketing_card.cards_card_action") | {
            'context': {},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_show_clicked_cards(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("marketing_card.cards_card_action") | {
            'context': {'search_default_filter_visited': True},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_show_shared_cards(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("marketing_card.cards_card_action") | {
            'context': {'search_default_filter_shared': True},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_share_multi(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Cards'),
            'res_model': 'card.card.share.multi',
            'context': {'default_card_campaign_id': self.id, 'default_subject': self.name},
            'views': [[False, 'form']],
            'target': 'new',
        }

    def _generate_card_hash_token(self, record_id):
        """Generate a token for a specific recipient of this campaign."""
        self.ensure_one()
        token = (self.id, self.create_date, record_id)
        return hashlib.sha1(repr(token).encode('utf-8')).hexdigest()

    def _get_bodies(self, records=None):
        if not self.card_template_id.body:
            return {record.id: '' for record in records}
        return self._render_field('body_html', records.ids)

    def _get_images_b64(self, records=None):
        bodies = self._get_bodies(records=records)
        return {record_id: base64.b64encode(self.env['ir.actions.report']._run_wkhtmltoimage(
            [body],
            *TEMPLATE_DIMENSIONS
        )[0]) if body else '' for record_id, body in bodies.items()}

    def _get_or_create_card_from_res_id(self, record_id):
        """Create find the card associated with the record_id, or creates it.

        :raise MissingError: if checking tokens and the token doesn't match the record id.
        """
        self.ensure_one()
        card = self.env['card.card'].search([('campaign_id', '=', self.id), ('res_id', '=', record_id)])
        if not card:
            card = self.env['card.card'].create({'campaign_id': self.id, 'res_id': record_id})
        return card

    def _get_or_create_cards_from_res_ids(self, res_ids):
        """Create missing cards for the given ids.

        :return: all associated cards in no particular order
        """
        self.ensure_one()
        cards = self.env['card.card'].search_fetch([('campaign_id', '=', self.id), ('res_id', 'in', res_ids)], ['res_id'])
        missing_ids = set(res_ids) - set(cards.mapped('res_id'))
        cards += self.env['card.card'].create([{'campaign_id': self.id, 'res_id': missing_id} for missing_id in missing_ids])

        card_by_res_id = cards.grouped('res_id')
        return self.env['card.card'].browse([card_by_res_id[res_id].id for res_id in res_ids])

    def _get_preview_url(self, res_id):
        self.ensure_one()
        return f'{self.get_base_url()}/cards/{self.id}/{res_id}/{self._generate_card_hash_token(res_id)}/preview'

    # MAIL RENDER MIXIN

    @api.model
    def _campaign_render_eval_context(self):
        return {
            'default_values': {
                'background': self.card_template_id.default_background
            },
            'elements': self.element_ids.grouped('role'),
            '_get_role_value': self._get_role_value,
            '_get_role_values': self._get_role_values,
        }

    @api.model
    def _render_eval_context(self):
        return super()._render_eval_context() | self._campaign_render_eval_context()

    @staticmethod
    def _get_role_value(element, record, default_values, preview_values):
        value = element._get_value(record)
        if not value and default_values and element.role in default_values:
            value = default_values[element.role]
        if not value and preview_values and element.role in preview_values and element.value_type == 'static':
            value = preview_values[element.role]
        if not value and not record:
            value = element._get_placeholder()
        return value

    @staticmethod
    def _get_role_values(elements, record, default_values, preview_values):
        return {role: CardCampaign._get_role_value(element, record, default_values, preview_values) for role, element in elements.items()}
