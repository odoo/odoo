import base64
import pytz
from datetime import date, datetime

from odoo import _, api, exceptions, fields, models, modules

from .card_template import TEMPLATE_DIMENSIONS


class CardCampaign(models.Model):
    _name = 'card.campaign'
    _description = 'Marketing Card Campaign'
    _inherit = ['mail.activity.mixin', 'mail.render.mixin', 'mail.thread']
    _order = 'id DESC'
    _unrestricted_rendering = True

    def _default_card_template_id(self):
        return self.env['card.template'].search([], limit=1)

    def _get_model_selection(self):
        """Hardcoded list of models, checked against actually-present models."""
        allowed_models = ['res.partner', 'event.track', 'event.booth', 'event.registration']
        models = self.env['ir.model'].sudo().search_fetch([('model', 'in', allowed_models)], ['model', 'name'])
        return [(model.model, model.name) for model in models]

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    body_html = fields.Html(related='card_template_id.body', render_engine="qweb", readonly=False)

    card_count = fields.Integer(compute='_compute_card_stats')
    card_click_count = fields.Integer(compute='_compute_card_stats')
    card_share_count = fields.Integer(compute='_compute_card_stats')

    mailing_ids = fields.One2many('mailing.mailing', 'card_campaign_id')
    mailing_count = fields.Integer(compute='_compute_mailing_count')

    card_ids = fields.One2many('card.card', inverse_name='campaign_id')
    card_template_id = fields.Many2one('card.template', string="Design", default=_default_card_template_id, required=True)
    image_preview = fields.Image(compute='_compute_image_preview', compute_sudo=False, readonly=True, store=True, attachment=False)
    link_tracker_id = fields.Many2one('link.tracker', ondelete="restrict")
    res_model = fields.Selection(
        string="Model Name", compute='_compute_res_model', selection='_get_model_selection',
        precompute=True, readonly=True, required=True, store=True,
    )

    post_suggestion = fields.Text(help="Description below the card and default text when sharing on X")
    preview_record_ref = fields.Reference(string="Preview On", selection="_get_model_selection", required=True)
    tag_ids = fields.Many2many('card.campaign.tag', string='Tags')
    target_url = fields.Char(string='Post Link')
    target_url_click_count = fields.Integer(related="link_tracker_id.count")

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, domain="[('share', '=', False)]")

    reward_message = fields.Html(string='Thank You Message')
    reward_target_url = fields.Char(string='Reward Link')
    request_title = fields.Char('Request', default=lambda self: _('Help us share the news'))
    request_description = fields.Text('Request Description')

    # Static Content fields
    content_background = fields.Image('Background')
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

    # images are always dynamic
    content_image1_path = fields.Char('Dynamic Image 1')
    content_image2_path = fields.Char('Dynamic Image 2')

    @api.depends('card_ids')
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
            if status in ('shared', 'visited'):
                campaign.card_click_count += card_count
            campaign.card_count += card_count

    @api.model
    def _get_render_fields(self):
        return [
            'body_html', 'content_background', 'content_image1_path', 'content_image2_path', 'content_button', 'content_header',
            'content_header_dyn', 'content_header_path', 'content_header_color', 'content_sub_header',
            'content_sub_header_dyn', 'content_sub_header_path', 'content_section', 'content_section_dyn',
            'content_section_path', 'content_sub_section1', 'content_sub_section1_dyn', 'content_sub_header_color',
            'content_sub_section1_path', 'content_sub_section2', 'content_sub_section2_dyn', 'content_sub_section2_path',
            'card_template_id',
        ]

    def _check_access_right_dynamic_template(self):
        """ `_unrestricted_rendering` being True means we trust the value on model
        when rendering. This means once created, rendering is done without restriction.
        But this attribute triggers a check at create / write / translation update that
        current user is an admin or has full edition rights (group_mail_template_editor).

         However here a Marketing Card Manager must be able to edit the fields other
         than the rendering fields. The qweb rendered field `body_html` cannot be
         modified by users other than the `base.group_system` users, as
        - it's a related field to `card.template.body`,
        - store=False
        - the model `card.template` can only be altered by `base.group_system`

        Hence the security is delegated to the 'card.template' model, hence the
        check done by `_check_access_right_dynamic_template` can be bypassed.
        """
        return

    @api.depends(lambda self: self._get_render_fields() + ['preview_record_ref'])
    def _compute_image_preview(self):
        for campaign in self:
            if campaign.preview_record_ref and campaign.preview_record_ref.exists():
                image = campaign._get_image_b64(campaign.preview_record_ref)
            else:
                image = False
            campaign.image_preview = image

    @api.depends('mailing_ids')
    def _compute_mailing_count(self):
        self.mailing_count = 0
        mailing_counts = self.env['mailing.mailing']._read_group(
            [('card_campaign_id', 'in', self.ids)], ['card_campaign_id'], ['__count']
        )
        for campaign, mailing_count in mailing_counts:
            campaign.mailing_count = mailing_count

    @api.depends('preview_record_ref')
    def _compute_res_model(self):
        for campaign in self:
            preview_model = campaign.preview_record_ref and campaign.preview_record_ref._name
            campaign.res_model = preview_model or campaign.res_model or 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        utm_source = self.env.ref('marketing_card.utm_source_marketing_card', raise_if_not_found=False)
        link_trackers = self.env['link.tracker'].sudo().create([
            {
                'url': vals.get('target_url') or self.env['card.campaign'].get_base_url(),
                'title': vals['name'],  # not having this will trigger a request in the create
                'source_id': utm_source.id if utm_source else None,
                'label': f"marketing_card_campaign_{vals.get('name', '')}_{fields.Datetime.now()}",
            }
            for vals in vals_list
        ])
        return super().create([{
            **vals,
            'link_tracker_id': link_tracker_id,
        } for vals, link_tracker_id in zip(vals_list, link_trackers.ids)])

    def write(self, vals):
        link_tracker_vals = {}
        if vals.keys() & set(self._get_render_fields()):
            self.env['card.card'].with_context(active_test=False).search([('campaign_id', 'in', self.ids)]).requires_sync = True
        if 'target_url' in vals:
            link_tracker_vals['url'] = vals['target_url'] or self.env['card.campaign'].get_base_url()
        if link_tracker_vals:
            self.link_tracker_id.sudo().write(link_tracker_vals)

        # write and detect model changes on actively-used campaigns
        original_models = self.mapped('res_model')

        write_res = super().write(vals)

        updated_model_campaigns = self.env['card.campaign'].browse([
            campaign.id for campaign, new_model, old_model
            in zip(self, self.mapped('res_model'), original_models)
            if new_model != old_model
        ])
        for campaign in updated_model_campaigns:
            if campaign.card_count:
                raise exceptions.ValidationError(_(
                    "Model of campaign %(campaign)s may not be changed as it already has cards",
                    campaign=campaign.display_name,
                ))
        return write_res

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

    def action_view_mailings(self):
        self.ensure_one()
        return {
            'name': _('%(card_campaign_name)s Mailings', card_campaign_name=self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'mailing.mailing',
            'domain': [('card_campaign_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_preview(self):
        self.ensure_one()
        card = self._fetch_or_create_preview_card()
        return {'type': 'ir.actions.act_url', 'url': card._get_path('preview'), 'target': 'new'}

    def action_share(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Cards'),
            'res_model': 'mailing.mailing',
            'context': {
                'create': False,
                'default_subject': self.name,
                'default_card_campaign_id': self.id,
                'default_mailing_model_id': self.env['ir.model']._get_id(self.res_model),
                'default_body_arch': self._action_share_get_default_body(),
            },
            'views': [[False, 'form']],
            'target': 'current',
        }

    def _fetch_or_create_preview_card(self):
        """Fetch the card corresponding to the preview record, or create one if none exists.

        The image also gets the preview render if it has none. It is also archived to ensure
        it is rerendered later if sent.
        """
        self.ensure_one()
        card = self.env['card.card'].with_context(active_test=False).search([
            ('campaign_id', '=', self.id),
            ('res_id', '=', self.preview_record_ref.id),
        ])
        image = self.image_preview
        if card:
            card.write({
                'image': image,
                'active': False,
            })
        else:
            card = self.env['card.card'].create({
                'campaign_id': self.id,
                'res_id': self.preview_record_ref.id,
                'image': image,
                'active': False,
            })
        return card

    def _action_share_get_default_body(self):
        # try to pick a relevant card if users try to visit during preview/test mailings
        preview_card = self._fetch_or_create_preview_card() if self else self.env['card.card']
        return f"""
<div class="o_layout oe_unremovable oe_unmovable o_empty_theme" data-name="Mailing">
<style id="design-element"></style>
<div class="container o_mail_wrapper o_mail_regular oe_unremovable">
<div class="row">
<div class="col o_mail_no_options o_mail_wrapper_td bg-white oe_structure o_editable theme_selection_done">

<div class="s_text_block o_mail_snippet_general pt24 pb24" style="padding-left: 15px; padding-right: 15px;" data-snippet="s_text_block" data-name="Text">
    <div class="container s_allow_columns">
        <p">{_("Hello everyone")}</p>
        <p>{_("Here's the link to advertise your participation.")}
        <br>{_("Your help with this promotion would be greatly appreciated!")}</p>
        <p>{_("Many thanks")}</p>
    </div>
</div>

<div class="s_call_to_share_card o_mail_snippet_general" style="padding-top: 10px; padding-bottom: 10px;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0">
        <tbody>
            <tr>
                <td align="center">
                    <a href="/cards/{preview_card.id or 0}/preview" style="padding-left: 3px !important; padding-right: 3px !important">
                        <img src="/web/image/card.campaign/{self.id or 0}/image_preview" alt="{_("Card Preview")}" class="img-fluid" style="width: 540px;"
                            data-original-src="/web/image/card.campaign/{self.id or 0}/image_preview"/>
                    </a>
                </td>
            </tr>
        </tbody>
    </table>
</div>

</div></div></div></div>
"""

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

        # None means there was a logged error at image rendering time.
        # Tests also do not render by default, in that case ignore.
        if image_bytes is None and not modules.module.current_test:
            raise exceptions.UserError(_(
                'An error occured while rendering a card for %(record_name)s. '
                'Try again or check the server logs for more details.',
                record_name=record.display_name
            ))
        return image_bytes and base64.b64encode(image_bytes)

    # ==========================================================================
    # Card creation
    # ==========================================================================

    def _update_cards(self, domain, auto_commit=False):
        """Create missing cards and update cards if necessary based for the domain."""
        self.ensure_one()
        TargetModel = self.env[self.res_model]
        res_ids = TargetModel.search(domain).ids
        cards = self.env['card.card'].with_context(active_test=False).search_fetch([
            ('campaign_id', '=', self.id),
            ('res_id', 'in', res_ids),
        ], ['res_id', 'requires_sync'])
        # update active and res_model for preview cards
        cards.active = True
        self.env['card.card'].create([
            {'campaign_id': self.id, 'res_id': res_id}
            for res_id in set(res_ids) - set(cards.mapped('res_id'))
        ])

        # render by batch of 100 to avoid losing progress in case of time out
        updated_cards = self.env['card.card']
        while cards := self.env['card.card'].search_fetch([
            ('requires_sync', '=', True),
            ('campaign_id', '=', self.id),
            ('res_id', 'in', res_ids),
        ], ['res_id'], limit=100):
            # no need to autocommit if it can be done in one batch
            if auto_commit and updated_cards:
                self.env.cr.commit()
                # avoid keeping hundreds of jpegs in memory
                self.env['card.card'].invalidate_model(['image'])
            TargetModelPrefetch = TargetModel.with_prefetch(cards.mapped('res_id'))
            for card in cards.filtered('requires_sync'):
                card.write({
                    'image': self._get_image_b64(TargetModelPrefetch.browse(card.res_id)),
                    'requires_sync': False,
                    'active': True,
                })
            cards.flush_recordset()
            updated_cards += cards
        return updated_cards

    def _get_url_from_res_id(self, res_id, suffix='preview'):
        card = self.env['card.card'].search([('campaign_id', '=', self.id), ('res_id', '=', res_id)])
        return card and card._get_path(suffix) or self.target_url

    # ==========================================================================
    # Mail render mixin / Render utils
    # ==========================================================================

    @api.depends('res_model')
    def _compute_render_model(self):
        """ override for mail.render.mixin """
        for campaign in self:
            campaign.render_model = campaign.res_model

    def _get_card_element_values(self, record):
        """Helper to get the right value for dynamic fields."""
        self.ensure_one()
        result = {
            'image1': images[0] if (images := self.content_image1_path and self.content_image1_path in record and record.mapped(self.content_image1_path)) else False,
            'image2': images[0] if (images := self.content_image2_path and self.content_image2_path in record and record.mapped(self.content_image2_path)) else False,
        }
        campaign_text_element_fields = (
            ('header', 'content_header', 'content_header_dyn', 'content_header_path'),
            ('sub_header', 'content_sub_header', 'content_sub_header_dyn', 'content_sub_header_path'),
            ('section', 'content_section', 'content_section_dyn', 'content_section_path'),
            ('sub_section1', 'content_sub_section1', 'content_sub_section1_dyn', 'content_sub_section1_path'),
            ('sub_section2', 'content_sub_section2', 'content_sub_section2_dyn', 'content_sub_section2_path'),
        )
        for el, text_field, dyn_field, path_field in campaign_text_element_fields:
            if not self[dyn_field]:
                result[el] = self[text_field]
            elif not (field_path := self[path_field]):
                result[el] = record
            else:
                fnames = field_path.split('.')
                try:
                    value = record
                    while fnames and (fname := fnames.pop(0)):
                        value.fetch([fname])
                        value = value[fname]
                    m = record.mapped(field_path)
                    result[el] = m and m[0] or False
                except (AttributeError, ValueError):
                    # for generic image, or if field incorrect, return name of field
                    result[el] = field_path
                # force dates to their relevant timezone as that's what is usually wanted
                if (
                    isinstance(result[el], (date, datetime))
                    and (tz := record._mail_get_timezone())
                ):
                    result[el] = pytz.utc.localize(result[el]).astimezone(pytz.timezone(tz)).replace(tzinfo=None)
        return result
