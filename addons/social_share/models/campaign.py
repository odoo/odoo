# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict
from markupsafe import Markup

from odoo import _, api, Command, exceptions, fields, models
from ..controllers.main import SocialShareController
from .render.renderer_text import FieldTextRenderer, UserTextRenderer
from .render.renderer_image import ColorShapeRenderer, ImageFieldShapeRenderer, ImageStaticShapeRenderer

TEXT_VALUE_TYPES = [('static', 'Text'), ('field', 'Field')]
IMAGE_VALUE_TYPES = [('static', 'Text'), ('field', 'Field')]
TEMPLATE_TYPE_CAMPAIGN_TYPE_MAP = {'shape': 'image'}
TEMPLATE_RENDERER_CAMPAIGN_RENDERER_MAP = {ColorShapeRenderer: ImageStaticShapeRenderer}

# roles that are linked to campaign fields and what type of values they should be
SUPPORTED_ROLES = OrderedDict({
    'background': {'render_type': ['image', 'shape'], 'value_type': ['static']},
    'header': {'render_type': ['text'], 'value_type': [t[0] for t in TEXT_VALUE_TYPES]},
    'subheader': {'render_type': ['text'], 'value_type': [t[0] for t in TEXT_VALUE_TYPES]},
    'section-1': {'render_type': ['text'], 'value_type': [t[0] for t in TEXT_VALUE_TYPES]},
    'subsection-1': {'render_type': ['text'], 'value_type': [t[0] for t in TEXT_VALUE_TYPES]},
    'subsection-2': {'render_type': ['text'], 'value_type': [t[0] for t in TEXT_VALUE_TYPES]},
    'button': {'render_type': ['text'], 'value_type': ['static']},
    'image-1': {'render_type': ['image', 'shape'], 'value_type': IMAGE_VALUE_TYPES},
    'image-2': {'render_type': ['image', 'shape'], 'value_type': ['static']},
})


class CampaignElement(models.Model):
    _name = 'social.share.campaign.render.element'
    _inherit = 'social.share.image.render.element'
    _description = 'Social Share Campaign Element'
    _sql_constraints = [('role_uniq', "unique(campaign_id, role)", "Each campaign should only have one element for each role.")]

    model = fields.Char(related='campaign_id.model')
    campaign_id = fields.Many2one('social.share.campaign', ondelete='cascade')
    role = fields.Selection(required=True)
    # for static data, we can cache the result of the compute as an image to avoid expensive computes
    # TODO maybe remove if not necessary
    cached_image = fields.Image(compute="_compute_cached_image", store=True)

    @api.depends('value_type', 'render_type', 'text')
    def _compute_cached_image(self):
        self.cached_image = False
        #for element in self:
        #    if element.value_type != 'static' or element.render_type != 'text' or not element.text:
        #        element.cached_image = False
        #    else:
        #        matching_template_element = element.campaign_id.share_template_variant_id.layers.filtered(lambda layer: layer.role == element.role)
        #        if matching_template_element:
        #            renderer_class = element._get_renderer_class()
        #            template_values = matching_template_element._get_renderer_constructor_values(renderer_class)
        #            local_values = element._get_renderer_constructor_values(renderer_class)
        #            image_bytes = BytesIO()
        #            renderer_class(**(template_values | local_values)).render_image().save(image_bytes, "PNG")
        #            element.cached_image = image_bytes.getvalue()
        #        else:
        #            element.cached_image = False

    @api.onchange('model')
    def _onchange_model(self):
        self.filtered(lambda element: element.value_type == 'field').field_path = False

    def _get_renderer_constructor_values(self, renderer_class):
        """Return a dict containing kwargs to construct a renderer object."""
        if renderer_class == ImageStaticShapeRenderer:
            return {
                'shape': self.shape,
                'image': self.image,
            }
        if renderer_class == ImageFieldShapeRenderer:
            return {
                'shape': self.shape,
                'field_path': self.field_path,
            }
        if renderer_class == UserTextRenderer:
            values = {
                'text': self.text,
                'text_color': self.text_color,
            }
            return values
        if renderer_class == FieldTextRenderer:
            values = {
                'field_path': self.field_path,
                'model': self.model,
                'text_color': self.text_color,
            }
            return values
        return super()._get_renderer_constructor_values()

    def _sync_from_template_element(self, template_element):
        template_renderer_class = template_element._get_renderer_class()
        template_renderer_class = TEMPLATE_RENDERER_CAMPAIGN_RENDERER_MAP.get(template_renderer_class, template_renderer_class)
        fields = self._get_renderer_constructor_values(template_element._get_renderer_class()).keys()
        self.write({
            field: template_element[field]
            for field in fields
        } | {
            'render_type': TEMPLATE_TYPE_CAMPAIGN_TYPE_MAP.get(template_element.render_type, template_element.render_type),
            'value_type': template_element.value_type,
            'text_color': template_element.text_color or 'ffffff',
        })

class Campaign(models.Model):
    _name = 'social.share.campaign'
    _description = 'Social Share Campaign'
    _inherit = ['utm.source.mixin', 'mail.thread']

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one('ir.model', domain=lambda self: [('model', 'in', self.env['social.share.campaign.template']._get_valid_target_models())])
    model = fields.Char(related='model_id.model', string="Model Name")
    reference_share_template_id = fields.Many2one(
        'social.share.campaign.template', 'Reference Template',
        domain="[('parent_variant_id', '=', False),"
        "'|', ('model_id', '=', False), ('model_id', '=', model_id)]"
    )
    share_template_variant_id = fields.Many2one(
        'social.share.campaign.template', domain="['|', ('id', '=', reference_share_template_id),"
        "('parent_variant_id', '=', reference_share_template_id)]"
    )

    post_suggestion = fields.Text()
    tag_ids = fields.Many2many('social.share.campaign.tag', string='Tags')
    target_url = fields.Char(string='Shared Link', required=True)
    target_url_redirected = fields.Char(compute='_compute_target_url_redirected')
    thanks_message = fields.Html(string='Thank-You Message')
    thanks_redirection = fields.Char(string='Redirection URL')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, domain="[('share', '=', False)]")

    render_element_ids = fields.One2many('social.share.campaign.render.element', inverse_name='campaign_id')

    image = fields.Image(compute='_compute_image', store=True)  # for some reason, is computed twice on change if not stored

    link_tracker_id = fields.Many2one('link.tracker', ondelete="restrict")

    target_url_click_count = fields.Integer(compute='_compute_target_url_click_count')
    share_url_ids = fields.One2many('social.share.url', inverse_name='campaign_id')
    share_url_click_count = fields.Integer(compute='_compute_share_url_click_count')
    share_url_share_count = fields.Integer(compute='_compute_share_url_share_count')

    mail_template_id = fields.Many2one('mail.template')

    @api.model_create_multi
    def create(self, create_vals):
        campaign_ids = super().create(create_vals)
        link_tracker_ids = self.env['link.tracker'].create([
            {
                'url': campaign.target_url,
                'title': campaign.name,  # not having this will trigger a request in the create
                'source_id': campaign.source_id.id,
            } for campaign in campaign_ids
        ])

        mail_template_ids = self.env['mail.template'].create([{
            'name': f'social_share {campaign.name} template',
            'model_id': campaign.model_id.id if campaign.model_id else False,
            'body_html': Markup(
                '<div id="message"></div>'
                f"""<a t-att-href="object.env['social.share.campaign'].browse({campaign.id})._get_url(object.id)" class="o_no_link_popover">{_("Your Card")}</a>"""
            ),
        } for campaign in campaign_ids])

        for campaign, tracker, template in zip(campaign_ids, link_tracker_ids, mail_template_ids):
            campaign.write({'link_tracker_id': tracker.id, 'mail_template_id': template.id})
        return campaign_ids

    def unlink(self):
        self.mail_template_id.unlink()
        return super().unlink()

    def write(self, vals):
        write_ret = super().write(vals)
        for campaign in self:
            link_tracker_vals = {}
            if 'source_id' in vals:
                link_tracker_vals['source_id'] = campaign.source_id
            if 'target_url' in vals:
                link_tracker_vals['url'] = campaign.target_url
            if 'model_id' in vals:
                campaign.mail_template_id.model_id = campaign.model_id
            if link_tracker_vals.keys():
                campaign.link_tracker_id.write(link_tracker_vals)
        return write_ret

    @api.depends('link_tracker_id.count')
    def _compute_target_url_click_count(self):
        for campaign in self:
            campaign.target_url_click_count = self.link_tracker_id.count

    @api.depends('share_url_ids.visited')
    def _compute_share_url_click_count(self):
        for campaign in self:
            campaign.share_url_click_count = len(campaign.share_url_ids.filtered('visited'))

    @api.depends('share_url_ids.shared')
    def _compute_share_url_share_count(self):
        for campaign in self:
            campaign.share_url_share_count = len(campaign.share_url_ids.filtered('shared'))

    @api.depends('link_tracker_id.short_url')
    def _compute_target_url_redirected(self):
        for campaign in self:
            campaign.target_url_redirected = campaign.link_tracker_id.short_url or campaign.target_url

    @api.constrains('share_template_variant_id.layers.render_type', 'share_template_variant_id.layers.value_type')
    def _check_share_template_variant_id(self):
        for campaign in self:
            for layer in campaign.reference_share_template_id.layers.filtered('role'):
                if not self._check_layer_is_compatible(layer):
                    raise exceptions.ValidationError(_('%(layer_role)s is used in %(social_campaign_name)s but has incompatible values.'))

    @staticmethod
    def _check_layer_is_compatible(layer):
        expected_values = SUPPORTED_ROLES.get(layer.role, dict())
        for field, valid_values in expected_values.items():
            if layer[field] not in valid_values:
                return False
        return True

    @api.depends('share_template_variant_id', 'render_element_ids')
    def _compute_image(self):
        for campaign in self:
            record = self.env[campaign.model] if campaign.model else None
            campaign.image = campaign._generate_image_b64(record=record)

    def action_open_url_share(self):
        """Open url dialog."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Share Link'),
            'res_model': 'social.share.url.share',
            'views': [[False, 'form']],
            'context': {
                'default_campaign_id': self.id,
                'dialog_size': 'medium',
            },
            'target': 'new',
        }

    def _generate_image_b64(self, record=None):
        return base64.encodebytes(self._generate_image_bytes(record=record))

    def _generate_image_bytes(self, record=None):
        return self.share_template_variant_id._generate_image_bytes(
            record=record,
            replacement_renderers=self._get_replacement_renderers()
        )

    def _get_replacement_renderers(self):
        """Combine the original values of the template with the custom values of the campaign.

        Get a mapping from layer role to an instance of a renderer.
        """
        template_layers = self.share_template_variant_id.layers.filtered('role').grouped('role')
        local_layers = self.render_element_ids.grouped('role')
        renderer_vals = dict()
        for role in template_layers.keys() & local_layers.keys():
            renderer_class = local_layers[role]._get_renderer_class()
            template_values = template_layers[role]._get_renderer_constructor_values(renderer_class)
            local_values = local_layers[role]._get_renderer_constructor_values(renderer_class)
            renderer_vals[role] = renderer_class(**(template_values | local_values))
        return renderer_vals

    def action_show_clicked_urls(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("social_share.action_social_share_url") | {
            'context': {'search_default_filter_visited': True},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_show_shared_urls(self):
        self.ensure_one()
        return self.env["ir.actions.actions"]._for_xml_id("social_share.action_social_share_url") | {
            'context': {'search_default_filter_shared': True},
            'domain': [('campaign_id', '=', self.id)],
        }

    def action_share_multi(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Share URLS'),
            'res_model': 'social.share.url.share.multi',
            'context': {'default_share_campaign_id': self.id},
            'views': [[False, 'form']],
            'target': 'new',
        }

    def _get_url(self, record_id):
        self.ensure_one()
        uuid = False
        if self.model_id:
            existing_url = self.share_url_ids.filtered(lambda rec: rec.res_id == record_id)
            if existing_url:
                uuid = existing_url.uuid
            else:
                uuid = self.env['social.share.url'].create({'campaign_id': self.id, 'res_id': record_id}).uuid
        return SocialShareController._get_campaign_url(
            self.id, uuid
        )

    @api.onchange('reference_share_template_id')
    def _onchange_reference_share_template_id(self):
        for campaign in self:
            # sync roles
            template_layers = campaign.reference_share_template_id.layers.filtered('role').grouped('role')
            local_layers = campaign.render_element_ids.grouped('role')
            template_roles = set(template_layers.keys())
            local_roles = set(local_layers.keys())
            # re-create everything to preserve a consistent ordering in UI
            if local_roles != template_roles:
                create_values = []
                for role in SUPPORTED_ROLES:
                    if role not in template_roles:
                        continue
                    if role in local_roles:
                        create_values.append(Command.create(local_layers[role].copy_data()[0]))
                    else:
                        create_values.append(Command.create({'role': role}))
                campaign.write({'render_element_ids': [Command.clear()] + create_values})
            local_layers = campaign.render_element_ids.grouped('role')
            for role in template_roles:
                local_layers[role]._sync_from_template_element(template_layers[role])
            # pick default variant
            self.share_template_variant_id = self.reference_share_template_id
