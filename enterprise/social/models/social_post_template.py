# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import format_datetime


class SocialPostTemplate(models.Model):
    """
    Models the abstraction of social post content.
    It can generate multiple 'social.post' records to be sent on social medias

    This model contains all information related to the post content (message, images) but
    also some common methods. They can be used to prepare a social post without creating
    one (that can be useful in other application, like `social_event` e.g.).

    'social.post.template' is therefore a template model used to generate `social.post`.
    It is inherited by `social.post` to extract common fields declaration and post
    management methods.
    """
    _name = 'social.post.template'
    _description = 'Social Post Template'
    _rec_names_search = ['display_message']

    @api.model
    def default_get(self, fields):
        result = super(SocialPostTemplate, self).default_get(fields)
        # When entering a text in a reference field, we should take the entered
        # text  and use it to initialize the message. As the reference widget might
        # share different models (and so not always write on "message" but sometimes on
        # "name" or whatever) it will not update the "create_name_field" parameter when
        # the model changes and we need this piece of code to set correctly the message
        if not result.get('message') and self.env.context.get('default_name'):
            result['message'] = self.env.context.get('default_name')
        return result

    # Content
    message = fields.Text("Message")
    image_ids = fields.Many2many(
        'ir.attachment', string='Attach Images',
        help="Will attach images to your posts (if the social media supports it).")
    display_message = fields.Char(string='Display Message', compute='_compute_display_message', search='_search_display_message')
    # JSON array capturing the URLs of the images to make it easy to display them in the kanban view
    image_urls = fields.Text(
        'Images URLs', compute='_compute_image_urls')
    is_split_per_media = fields.Boolean('Split Per Network')
    media_count = fields.Integer('Media Count', compute='_compute_media_count')
    # Account management
    account_ids = fields.Many2many('social.account', string='Social Accounts',
                                   help="The accounts on which this post will be published.",
                                   compute='_compute_account_ids', store=True, readonly=False)
    has_active_accounts = fields.Boolean('Are Accounts Available?', compute='_compute_has_active_accounts')

    @api.constrains('message', 'image_ids')
    def _check_has_message_or_image(self):
        for post in self:
            if not post.message and not post.image_ids and not post.is_split_per_media:
                raise UserError(_("Please specify either a message or upload some images."))

    @api.constrains(lambda self: ['image_ids'] + list(self._images_fields().values()))
    def _check_image_ids_mimetype(self):
        image_fields = ['image_ids'] + list(self._images_fields().values())
        for post in self:
            if any(not image.mimetype.startswith('image') for field in image_fields for image in post[field]):
                raise UserError(_('Uploaded file does not seem to be a valid image.'))

    @api.depends('message', 'is_split_per_media')
    def _compute_message_by_media(self):
        """To be used in sub-modules to compute the media-specific message."""
        message_fields = self._message_fields()
        for post in self:
            for field in message_fields.values():
                if not post[field] or not post.is_split_per_media:
                    post[field] = post.message

    @api.depends('image_ids', 'is_split_per_media')
    def _compute_images_by_media(self):
        """To be used in sub-modules to compute the media-specific images."""
        images_fields = self._images_fields()
        for post in self:
            for field in images_fields.values():
                if not post[field] or not post.is_split_per_media:
                    post[field] = post.image_ids

    @api.depends(lambda self: ['message', 'is_split_per_media'] + list(self._message_fields().values()))
    def _compute_display_message(self):
        message_fields = self._message_fields()
        for post in self:
            if not post.is_split_per_media:
                post.display_message = post.message
            else:
                media_types = post.account_ids.mapped('media_type')
                post.display_message = next((
                    post[message_fields[media_type]]
                    for media_type in media_types
                    if media_type in message_fields
                    and post[message_fields[media_type]]
                ), False)

    def _search_display_message(self, operator, operand):
        return expression.OR([[
            (field, operator, operand)]
            for field in ('message', *self._message_fields().values())
        ])

    @api.depends(lambda self: ['image_ids'] + list(self._images_fields().values()))
    def _compute_image_urls(self):
        """See field 'help' for more information."""
        image_fields = ['image_ids'] + list(self._images_fields().values())
        for post in self:
            all_image_ids = {image_id for field in image_fields for image_id in post[field].ids}
            post.image_urls = json.dumps([f'/web/image/{image_id}' for image_id in all_image_ids if image_id])

    @api.depends('account_ids')
    def _compute_media_count(self):
        for post in self:
            post.media_count = len(set(post.account_ids.mapped('media_type')))

    def _compute_account_ids(self):
        """If there are less than 3 social accounts available, select them all by default."""
        all_account_ids = self.env['social.account'].sudo().search([])

        for post in self:
            accounts = all_account_ids.filtered_domain(post._get_default_accounts_domain())
            post.account_ids = accounts if len(accounts) <= 3 else False

    @api.depends('account_ids')
    def _compute_has_active_accounts(self):
        has_active_accounts = self.env['social.account'].search_count([]) > 0
        for post in self:
            post.has_active_accounts = has_active_accounts

    def _prepare_preview_values(self, media):
        """ Generic function called by media specific _compute_*media*_preview methods. This function returns the
        live_post_link (in the case the compute is used in the context of a social_post) and the published date. """
        self.ensure_one()
        values = {
            'published_date': format_datetime(self.env, fields.Datetime.now(), tz=self.env.user.tz, dt_format="short"),
        }
        return values
    def _set_attachemnt_res_id(self):
        """ Set res_id of created attachements, the many2many_binary widget
        might create them without res_id, and if it's the case,
        only the current user will be able to read the attachments
        (other user will get an access error). """
        for post in self:
            if post.image_ids:
                attachments = self.env['ir.attachment'].sudo().browse(post.image_ids.ids).filtered(
                    lambda a: a.res_model == self._name and not a.res_id and a.create_uid.id == self._uid)
                if attachments:
                    attachments.write({'res_id': post.id})

    @api.model
    def name_create(self, name):
        record = self.create({'message': name})
        return record.id, record.display_name

    @api.model_create_multi
    def create(self, vals_list):
        res = super(SocialPostTemplate, self).create(vals_list)
        res._set_attachemnt_res_id()
        return res

    @api.depends('display_message')
    def _compute_display_name(self):
        for record in self:
            name = record.display_message or ""
            record.display_name = name if len(name) <= 50 else f"{name[:47]}..."

    def action_generate_post(self):
        self.ensure_one()
        action = self.env.ref('social.action_social_post').read()[0]
        action.update({
            'views': [[False, 'form']],
            'context': {
                'default_%s' % key: value
                for key, value in self._prepare_social_post_values().items()
            }
        })
        return action

    def _prepare_social_post_values(self):
        """Return the values to generate a social post from the social post template."""
        self.ensure_one()
        return {
            'message': self.message,
            'image_ids': self.image_ids.ids,
            'account_ids': self.account_ids.ids,
            'company_id': False,
            **{field: self[field] for field in self._message_fields().values()},
            **{field: self[field].ids for field in self._images_fields().values()},
        }

    @api.model
    def _prepare_post_content(self, message, media_type, **kw):
        """ Prepares the post content and can be customized by underlying social implementations.
        e.g: YouTube will automatically include a link at the end of the message.
        kwargs are limited to fields actually used by the underlying implementations
        (e.g: 'youtube_video_id'). """

        if media_type not in [key for (key, val) in self.env['social.media'].fields_get(['media_type'])['media_type']['selection']]:
            raise ValueError("Unknown media_type %s" % media_type)

        return message or ''

    @api.model
    def _message_fields(self):
        """Return the message field per media."""
        return {}

    @api.model
    def _images_fields(self):
        """Return the images field per media."""
        return {}

    @api.model
    def _get_post_message_modifying_fields(self):
        """ Returns additional fields required by the '_prepare_post_content' to compute the value
        of the social.live.post's "message" field. Which is a post-processed version of this model's
        "message" field (i.e shortened links, UTMized, ...).
        For example, social_youtube requires the 'youtube_video_id' field to be able to correctly
        prepare the post content. """
        return []

    @api.model
    def _extract_url_from_message(self, message):
        """ Utility method that extracts an URL (ex: https://www.google.com) from a string message.
        Copied from: https://daringfireball.net/2010/07/improved_regex_for_matching_urls """
        # TDE FIXME: use a tool method instead
        if not message:
            return None
        url_regex = re.compile(r"""((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]+|(([^\s()<>]+)))*)|[^\s`!()[]{};:'".,<>?«»“”‘’]))""", re.DOTALL)
        urls = url_regex.search(message)
        if urls:
            return urls.group(0)
        return None

    def _get_default_accounts_domain(self):
        """ Can be overridden by underlying social.media implementation to remove default accounts.
        It's used to filter the default accounts to tick when creating a new social.post. """
        return []
