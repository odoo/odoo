# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models


class Post(models.Model):
    """
    This is used to send customized share links to event participants
    outlining their involvment in the event.
    """
    _name = 'social.share.post'
    _description = 'Social Share Campaign'

    def _get_text_types_selection(self):
        lambda self: self.env['social.share.post.template.element']._get_text_types()

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one('ir.model', domain=lambda self: [('model', 'in', self.env['social.share.post.template']._get_valid_target_models())])
    model = fields.Char(related='model_id.model', string="Model Name")
    reference_share_template_id = fields.Many2one(
        'social.share.post.template', 'Reference Template',
        domain="[('post_id', '=', False), ('parent_variant_id', '=', False),"
        "'|', ('model_id', '=', False), ('model_id', '=', model_id)]"
    )
    share_template_variant_id = fields.Many2one(
        'social.share.post.template', domain="['|', ('id', '=', reference_share_template_id),"
        "('parent_variant_id', '=', reference_share_template_id)]"
    )
    share_template_id = fields.Many2one('social.share.post.template', string="Related Template", store=True, readonly=False)

    post_suggestion = fields.Text()
    tag_ids = fields.Many2many('social.share.tag', string="Tags")
    target_url = fields.Char(string="Target URL", required=True)
    thanks_message = fields.Html(string="Thank-You Message")
    thanks_redirection = fields.Char(string="Redirection URL")
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user)

    background = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    header = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    subheader = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    section_1 = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    subsection_1 = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    subsection_2 = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    button = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    image_1 = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')
    image_2 = fields.Many2one('social.share.post.template.element', compute='_compute_custom_elements', search='_search_template_element')

    header_type = fields.Selection(selection=_get_text_types_selection, related='header.type', readonly=False)
    subheader_type = fields.Selection(selection=_get_text_types_selection, related='subheader.type', readonly=False)
    section_1_type = fields.Selection(selection=_get_text_types_selection, related='section_1.type', readonly=False)
    subsection_1_type = fields.Selection(selection=_get_text_types_selection, related='subsection_1.type', readonly=False)
    subsection_2_type = fields.Selection(selection=_get_text_types_selection, related='subsection_2.type', readonly=False)

    header_val = fields.Text(related='header.text_val', readonly=False)
    subheader_val = fields.Text(related='subheader.text_val', readonly=False)
    section_1_val = fields.Text(related='section_1.text_val', readonly=False)
    subsection_1_val = fields.Text(related='subsection_1.text_val', readonly=False)
    subsection_2_val = fields.Text(related='subsection_2.text_val', readonly=False)

    background_val = fields.Image(related='background.image', readonly=False)
    button_val = fields.Text(related='button.text_val', readonly=False)
    image_1_val = fields.Image(related='image_1.image', readonly=False)
    image_2_val = fields.Image(related='image_2.image', readonly=False)

    def _search_template_element(self, operator, value):
        return [('share_template_id.layers', operator, value)]

    image = fields.Image(related='share_template_id.image')

    def action_open_url_share(self):
        """Open url dialog."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Url Share'),
            'res_model': 'social.share.url.share',
            'views': [[False, 'form']],
            'context': {
                'default_campaign_id': self.id,
                'dialog_size': 'medium',
            },
            'target': 'new',
        }

    def _get_template_custom_elements(self):
        def _get_role(role_field_name, post_template_layers):
            role_name = role_field_name.replace('_', '-')
            layers = post_template_layers.filtered(lambda layer: layer.role == role_name)
            return layers[-1] if layers else False
        self.ensure_one()
        post_layers = self.share_template_id.layers
        roles = ('background', 'header', 'subheader',
                 'section_1', 'subsection_1', 'subsection_2',
                 'button', 'image_1', 'image_2')
        return {
            role: _get_role(role, post_layers) for role in roles
        }

    @api.depends('share_template_id', 'share_template_variant_id')
    def _compute_custom_elements(self):
        for post in self:
            for key, value in post._get_template_custom_elements().items():
                setattr(post, key, value)

    def _inverse_custom_elements(self):
        pass

    @api.onchange('share_template_variant_id')
    def _update_share_template_id(self):
        """Update, create or recreate the 'template' associated with this post."""
        for post in self.filtered('share_template_variant_id'):
            if not post.share_template_id:
                post.share_template_id = post.share_template_variant_id.copy({'name': self.name})
            else:
                post.share_template_id._update_from_variant(post.share_template_variant_id)

    @api.depends('share_template_id')
    def _compute_body(self):
        for campaign in self:
            campaign.body = campaign.share_template_id.content

    def action_send(self):
        pass
    def action_schedule(self):
        pass
    def action_test(self):
        pass
