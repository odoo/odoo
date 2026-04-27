# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, api, fields, models
from odoo.tools.misc import format_datetime


class SocialPostConvert2Lead(models.TransientModel):
    """ Simple wizard allowing to convert a social.stream.post or a comment/reply to a post into
    a lead.

    This wizard is typically used from the "Feed" social view, when the end user can interact with
    its community through their posts or view other people's posts.
    For more information about the 2 'sources' of conversion ('comment' and 'stream_post'), see
    #action_convert_to_lead.

    Please note that for obvious privacy reasons, the social media platforms will not provide us
    with people's email, phone or address information, we only have the author name and the content
    of their post/comment.
    For that reason, end users will probably often only convert to leads based on existing clients,
    since otherwise they will not have any mean to contact the created lead. """

    _name = "social.post.to.lead"
    _description = "Convert Social Post to Lead"

    action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer')
    ], string='Related Customer', compute='_compute_partner_action_data', readonly=False, store=True)
    conversion_source = fields.Selection([
        ('comment', 'From a comment'),
        ('stream_post', 'From a stream post'),
    ], default='comment', string='Conversion Source')
    partner_id = fields.Many2one('res.partner', string="Customer",
        compute='_compute_partner_action_data', store=True, readonly=False)
    social_stream_post_id = fields.Many2one('social.stream.post', string="Social Stream Post")
    social_account_id = fields.Many2one('social.account', string="Social Account")
    # comment data
    author_name = fields.Char('Post Author Name', compute='_compute_post_data', store=True, readonly=False)
    post_content = fields.Html('Post Content')
    post_datetime = fields.Datetime('Post Datetime', compute='_compute_post_data', store=True, readonly=False)
    post_link = fields.Char('Post Link', compute='_compute_post_data', store=True, readonly=False)
    post_image_urls = fields.Text("Post Images URLs")  # JSON array capturing the URLs of the images
    #UTMs
    utm_source_id = fields.Many2one('utm.source', compute='_compute_utm_data')
    utm_medium_id = fields.Many2one('utm.medium', compute='_compute_utm_data')
    utm_campaign_id = fields.Many2one('utm.campaign', compute='_compute_utm_data')

    @api.depends('author_name')
    def _compute_partner_action_data(self):
        """ The goal is to find a matching partner based on the post or comment author name.
        e.g: the customer 'John Doe' commented on your Facebook post, and is already an existing
        customer with the same name in your Odoo database -> do the matching.
        If there are none or more than one, fallback to 'create' mode. """

        for wizard in self:
            partner = False
            # avoid searching on res.partner if not enough characters
            if wizard.author_name and len(wizard.author_name) > 3:
                partner = self.env['res.partner'].name_search(wizard.author_name)
            if partner and len(partner) == 1:
                wizard.action = 'exist'
                wizard.partner_id = partner[0][0]
            else:
                wizard.action = 'create'
                wizard.partner_id = False

    @api.depends('social_stream_post_id', 'conversion_source')
    def _compute_post_data(self):
        """ When converting from a stream.post, use it to populate post fields.
        Otherwise, the post fields will come from the default values passed on from the frontend. """

        for wizard in self:
            if wizard.conversion_source == 'stream_post' and wizard.social_stream_post_id:
                wizard.author_name = wizard.social_stream_post_id.author_name
                wizard.post_datetime = wizard.social_stream_post_id.published_date
                wizard.post_link = wizard.social_stream_post_id.post_link
            else:
                wizard.author_name = wizard.author_name or False
                wizard.post_datetime = wizard.post_datetime or False
                wizard.post_link = wizard.post_link or False

    @api.depends('social_stream_post_id', 'social_account_id')
    def _compute_utm_data(self):
        """ UTMs computation logic:

        - The medium is always set to the related social.account of the social.stream.post
        - If we find a matching social.post, we use its source and campaign
          Note: there will not always be a matching social.post
          e.g: when you post directly on your Facebook page on Facebook, then we don't have a
          social.post record related to that published content in your Odoo database, but it will
          still appear in the stream view and leads can be created from it
        - Otherwise, we set the source to a common record created in data.
          That way, users can still check some statistics based on posts that don't originate from
          Odoo. """

        utm_source_social_post = self.env.ref('social_crm.utm_source_social_post', raise_if_not_found=False)
        for wizard in self:
            wizard.utm_campaign_id = False
            wizard.utm_medium_id = wizard.social_account_id.utm_medium_id.id
            wizard.utm_source_id = False

            if wizard.social_stream_post_id:
                social_post = wizard.social_stream_post_id.sudo()._fetch_matching_post()
                if social_post:
                    wizard.utm_campaign_id = social_post.utm_campaign_id.id
                    wizard.utm_source_id = social_post.source_id.id
                elif utm_source_social_post:
                    wizard.utm_source_id = utm_source_social_post.id

    def action_convert_to_lead(self):
        """ Creates a crm.lead using the information of the social.stream.post or the comment.
        There are two possible sources:
        - 'stream_post'
          A social.stream.post, in that case all the information are retrieved from it
        - 'comment'
          A comment or a reply to a comment, in that case there is no record stored so we receive
          all the necessary information from the default values. """

        self.ensure_one()
        # create partner if needed
        if self.action == 'create':
            self.partner_id = self.env['res.partner'].create({'name': self.author_name})

        lead_values = {
            'name': _('Request from %s', self.author_name),
            'partner_id': self.partner_id.id,
            'source_id': self.utm_source_id.id,
            'medium_id': self.utm_medium_id.id,
            'campaign_id': self.utm_campaign_id.id,
            'description': self.env['ir.qweb']._render("social_crm.social_post_to_lead_description", {
                'object': self,
                'post_datetime': format_datetime(self.env, self.post_datetime, dt_format='yyyy-MM-dd HH:mm:ss (ZZZZ)'),
                'post_image_urls': json.loads(self.post_image_urls) if self.post_image_urls else False,
            }),
        }

        if self.action == 'nothing':
            # set the contact_name as we don't have a partner
            lead_values['contact_name'] = self.author_name

        lead_sudo = self.env['crm.lead'].with_context(
            mail_create_nosubscribe=True,
            mail_create_nolog=True
        ).sudo().create(lead_values)

        # return to lead (if can see) or simply close wizard (if cannot)
        if not lead_sudo.with_env(self.env).has_access('read'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("The lead has been created successfully."),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        # return the action to go to the form view of the new Ticket
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_all_leads")
        action.update({
            'res_id': lead_sudo.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        })
        return action
