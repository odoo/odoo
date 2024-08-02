import base64
from lxml import html
from itertools import count

from odoo import _, api, Command, fields, models
from odoo.tools.misc import hmac

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
        if 'card_element_ids' in fields_list and 'card_element_ids' not in default_vals:
            default_vals.setdefault('card_element_ids', [
                Command.create({'card_element_role': 'background', 'render_type': 'image'}),
                Command.create({'card_element_role': 'header', 'render_type': 'text'}),
                Command.create({'card_element_role': 'subheader', 'render_type': 'text'}),
                Command.create({'card_element_role': 'section_1', 'render_type': 'text'}),
                Command.create({'card_element_role': 'subsection_1', 'render_type': 'text'}),
                Command.create({'card_element_role': 'subsection_2', 'render_type': 'text'}),
                Command.create({'card_element_role': 'button', 'render_type': 'text'}),
                Command.create({'card_element_role': 'image_1', 'render_type': 'image'}),
                Command.create({'card_element_role': 'image_2', 'render_type': 'image'}),
            ])
        return default_vals

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
    card_element_ids = fields.One2many('card.campaign.element', inverse_name='campaign_id', copy=True)
    image_preview = fields.Image(compute='_compute_image_preview', readonly=True, store=True, compute_sudo=False, attachment=False)
    link_tracker_id = fields.Many2one('link.tracker', ondelete="restrict")
    res_model = fields.Selection(string="Model Name", selection=_get_model_selection,
                                 compute="_compute_res_model", copy=True, precompute=True,
                                 readonly=False, required=True, store=True)

    post_suggestion = fields.Text(help="Description below the card and default text when sharing on X")
    preview_record_ref = fields.Reference(string="Preview Record", selection="_selection_preview_record_ref")
    preview_record_url = fields.Char('Preview Record Link', compute="_compute_preview_record_url")
    reward_message = fields.Html(string='Thanks to You Message')
    reward_target_url = fields.Char(string='Reward Link')
    tag_ids = fields.Many2many('card.campaign.tag', string='Tags')
    target_url = fields.Char(string='Shared Link')
    target_url_click_count = fields.Integer(related="link_tracker_id.count")

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, domain="[('share', '=', False)]")

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

    @api.depends('body_html', 'card_element_ids', 'preview_record_ref', 'res_model', 'card_element_ids.card_element_role',
                 'card_element_ids.card_element_image', 'card_element_ids.card_element_text', 'card_element_ids.field_path',
                 'card_element_ids.text_color', 'card_element_ids.render_type', 'card_element_ids.value_type')
    def _compute_image_preview(self):
        rendered_campaigns = self.filtered('card_template_id.body').filtered('card_element_ids')
        (self - rendered_campaigns).image_preview = False

        for campaign in rendered_campaigns:
            if campaign.preview_record_ref and campaign.preview_record_ref.exists():
                image = campaign._get_image_b64(campaign.preview_record_ref)
            else:
                image = campaign._get_generic_image_b64()
            if image is not None:
                campaign.image_preview = image

    @api.depends('preview_record_ref')
    def _compute_preview_record_url(self):
        self.preview_record_url = False
        for campaign in self.filtered('preview_record_ref'):
            if campaign._origin.id:
                campaign.preview_record_url = campaign._get_preview_url_from_res_id(campaign.preview_record_ref.id)

    @api.depends('preview_record_ref')
    def _compute_res_model(self):
        for campaign in self:
            if campaign.preview_record_ref:
                campaign.res_model = campaign.preview_record_ref._name
            elif not campaign.res_model:
                campaign.res_model = 'res.partner'

    @api.onchange('res_model', 'preview_record_ref')
    def _onchange_res_model(self):
        for campaign in self:
            if not campaign._origin.res_model:
                continue
            if campaign._origin.res_model != campaign.res_model:
                campaign.card_element_ids.value_type = 'static'

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

    @api.model
    def _selection_preview_record_ref(self):
        return self._fields['res_model']._description_selection(self.env)

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

        # check this early to get a better error message
        for element in self.card_element_ids:
            if element._origin.field_path != element.field_path:
                element._check_fields()

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

    def _generate_card_hash_token(self, record_id):
        """Generate a token for a specific recipient of this campaign."""
        self.ensure_one()
        return hmac(self.env(su=True), ('marketing_card', self._name, self._origin.id, self.name), record_id)

    def _get_or_create_cards_from_res_ids(self, res_ids):
        """Create missing cards for the given ids."""
        self.ensure_one()
        cards = self.env['card.card'].search_fetch([('campaign_id', '=', self.id), ('res_id', 'in', res_ids)], ['res_id'])
        missing_ids = set(res_ids) - set(cards.mapped('res_id'))
        cards += self.env['card.card'].create([{'campaign_id': self.id, 'res_id': missing_id} for missing_id in missing_ids])

        # order based on input
        res_order = dict(zip(res_ids, count()))
        return cards.sorted(key=lambda card: res_order[card.res_id])

    def _get_preview_url_from_res_id(self, res_id):
        return self._get_card_path(res_id, 'preview')

    def _get_card_path(self, res_id, suffix):
        self.ensure_one()
        return f'{self.get_base_url()}/cards/{self._origin.id}/{res_id}/{self._generate_card_hash_token(res_id)}/{suffix}'

    # ==========================================================================
    # Mail render mixin / Render utils
    # ==========================================================================

    @api.depends('res_model')
    def _compute_render_model(self):
        """ override for mail.render.mixin """
        for campaign in self:
            campaign.render_model = campaign.res_model

    def _get_card_element_values(self, record, preview_values):
        """Helper to get the right value for each element when rendering."""
        self.ensure_one()
        value_from_role = {}
        default_values = {
            'background': self.card_template_id.default_background
        }
        for element in self.card_element_ids:
            value = element._get_render_value(record)
            if not value and element.card_element_role in default_values:
                value = default_values[element.card_element_role]
            if not value and preview_values and element.card_element_role in preview_values and element.value_type == 'static':
                value = preview_values[element.card_element_role]
            if not value and not record:
                value = element._get_placeholder_value()
            value_from_role[element.card_element_role] = value

        # in qweb t-out of "False" effectively removed the element while '' does not
        # we force everything to '' to be consistent
        return {element: val or '' for element, val in value_from_role.items()}
