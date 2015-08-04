# -*- coding: utf-8 -*-

import uuid

from openerp import _, api, fields, models, modules, tools
from openerp.exceptions import UserError


class ChannelPartner(models.Model):
    _name = 'mail.channel.partner'
    _description = 'Last Seen Many2many'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Recipient')
    channel_id = fields.Many2one('mail.channel', string='Channel')
    seen_datetime = fields.Datetime('Last Seen Datetime')


class Channel(models.Model):
    """ A mail.channel is a discussion group that may behave like a listener
    on documents. """
    _description = 'Discussion channel'
    _name = 'mail.channel'
    _mail_flat_thread = False
    _mail_post_access = 'read'
    _inherit = ['mail.thread']
    _inherits = {'mail.alias': 'alias_id'}

    def _get_default_image(self):
        image_path = modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    name = fields.Char('Name', required=True, translate=True)
    channel_type = fields.Selection([
        ('chat', 'Chat Discussion'),
        ('channel', 'Channel')],
        'Channel Type', default='channel')
    description = fields.Text('Description')
    uuid = fields.Char('UUID', size=50, select=True, default=lambda self: '%s' % uuid.uuid4())
    email_send = fields.Boolean('Email Sent', default=True)  # True for mail.channel
    # multi users channel
    channel_last_seen_partner_ids = fields.One2many('mail.channel.partner', 'channel_id', string='Last Seen')
    channel_partner_ids = fields.Many2many('res.partner', 'mail_channel_partner', 'channel_id', 'partner_id', string='Listeners')
    channel_message_ids = fields.Many2many('mail.message', 'mail_message_mail_channel_rel')
    # access
    public = fields.Selection([
        ('public', 'Everyone'),
        ('private', 'Invited people only'),
        ('groups', 'Selected group of users')],
        'Privacy', required=True, default='groups',
        help='This group is visible by non members. Invisible groups can add members through the invite button.')
    group_public_id = fields.Many2one('res.groups', string='Authorized Group',
                                      default=lambda self: self.env.ref('base.group_user'))
    group_ids = fields.Many2many(
        'res.groups', rel='mail_channel_res_group_rel',
        id1='mail_channel_id', id2='groups_id', string='Auto Subscription',
        help="Members of those groups will automatically added as followers. "
             "Note that they will be able to manage their subscription manually "
             "if necessary.")
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary("Photo", default=_get_default_image,
                          help="This field holds the image used as photo for the group, limited to 1024x1024px.")
    image_medium = fields.Binary('Medium-sized photo', compute='_get_image', inverse='_set_image', store=True,
                                 help="Medium-sized photo of the group. It is automatically "
                                      "resized as a 128x128px image, with aspect ratio preserved. "
                                      "Use this field in form views or some kanban views.")
    image_small = fields.Binary('Small-sized photo', compute='_get_image', inverse='_set_image', store=True,
                                help="Small-sized photo of the group. It is automatically "
                                     "resized as a 64x64px image, with aspect ratio preserved. "
                                     "Use this field anywhere a small image is required.")
    alias_id = fields.Many2one(
        'mail.alias', 'Alias', ondelete="restrict", required=True,
        help="The email address associated with this group. New emails received will automatically "
             "create new topics.")

    @api.one
    @api.depends('image')
    def _get_image(self):
        res = tools.image_get_resized_images(self.image)
        self.image_medium = res['image_medium']
        self.image_small = res['image_small']

    def _set_image(self):
        self.image = tools.image_resize_image_big(self.image)

    @api.model
    def create(self, vals):
        # Create channel and alias
        channel = super(Channel, self.with_context(
            alias_model_name=self._name, alias_parent_model_name=self._name, mail_create_nolog=True)
        ).create(vals)
        channel.alias_id.write({"alias_force_thread_id": channel.id, 'alias_parent_thread_id': channel.id})

        if vals.get('group_ids'):
            channel._subscribe_users()

        # make channel listen itself: posting on a channel notifies the channel
        if not self._context.get('mail_channel_noautofollow'):
            channel.message_subscribe(channel_ids=[channel.id])

        return channel

    @api.multi
    def unlink(self):
        aliases = self.mapped('alias_id')

        # Delete mail.channel
        try:
            all_emp_group = self.env.ref('mail.channel_all_employees')
        except ValueError:
            all_emp_group = None
        if all_emp_group and all_emp_group in self:
            raise UserError(_('You cannot delete those groups, as the Whole Company group is required by other modules.'))
        res = super(Channel, self).unlink()
        # Cascade-delete mail aliases as well, as they should not exist without the mail.channel.
        aliases.sudo().unlink()
        return res

    @api.multi
    def write(self, vals):
        result = super(Channel, self).write(vals)
        if vals.get('group_ids'):
            self._subscribe_users()
        return result

    def _subscribe_users(self):
        for mail_channel in self:
            mail_channel.write({'channel_partner_ids': [(4, pid) for pid in mail_channel.mapped('group_ids').mapped('users').mapped('partner_id').ids]})

    @api.multi
    def action_follow(self):
        return self.write({'channel_partner_ids': [(4, self.env.user.partner_id.id)]})

    @api.multi
    def action_unfollow(self):
        return self.write({'channel_partner_ids': [(3, self.env.user.partner_id.id)]})

    @api.multi
    def message_get_email_values(self, notif_mail=None):
        self.ensure_one()
        res = super(Channel, self).message_get_email_values(notif_mail=notif_mail)
        headers = {}
        if res.get('headers'):
            try:
                headers.update(eval(res['headers']))
            except Exception:
                pass
        headers['Precedence'] = 'list'
        # avoid out-of-office replies from MS Exchange
        # http://blogs.technet.com/b/exchange/archive/2006/10/06/3395024.aspx
        headers['X-Auto-Response-Suppress'] = 'OOF'
        if self.alias_domain and self.alias_name:
            headers['List-Id'] = '%s.%s' % (self.alias_name, self.alias_domain)
            headers['List-Post'] = '<mailto:%s@%s>' % (self.alias_name, self.alias_domain)
            # Avoid users thinking it was a personal message
            # X-Forge-To: will replace To: after SMTP envelope is determined by ir.mail.server
            list_to = '"%s" <%s@%s>' % (self.name, self.alias_name, self.alias_domain)
            headers['X-Forge-To'] = list_to
        res['headers'] = repr(headers)
        return res
