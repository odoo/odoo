# -*- coding: utf-8 -*-

from openerp import _, api, fields, models, modules, tools
from openerp.exceptions import UserError


class MailGroup(models.Model):
    """ A mail.channel is a collection of users sharing messages in a discussion
        group. The group mechanics are based on the followers. """
    _description = 'Discussion group'
    _name = 'mail.channel'
    _mail_flat_thread = False
    _mail_post_access = 'read'
    _inherit = ['mail.thread']
    _inherits = {'mail.alias': 'alias_id'}

    def _get_default_image(self):
        image_path = modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    name = fields.Char('Name', required=True, translate=True)
    description = fields.Text('Description')
    menu_id = fields.Many2one('ir.ui.menu', string='Related Menu', required=True, ondelete="cascade")
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
        # get parent menu
        menu_parent = self.env.ref('mail.mail_channel_menu_root')

        # Create menu id
        menu = self.env['ir.ui.menu'].sudo().create({'name': vals['name'], 'parent_id': menu_parent.id})
        vals['menu_id'] = menu.id

        # Create group and alias
        group = super(MailGroup, self.with_context(
            alias_model_name=self._name, alias_parent_model_name=self._name, mail_create_nolog=True)
        ).create(vals)
        group.alias_id.write({"alias_force_thread_id": group.id, 'alias_parent_thread_id': group.id})

        # Create action window for this group and link the menu to it
        inbox_ref = self.env.ref('mail.mail_channel_action_timeline')
        search_ref = self.env.ref('mail.view_message_search')
        act_domain = [('model', '=', 'mail.channel'), ('res_id', '=', group.id)]
        act_context = {'default_model': 'mail.channel',
                       'default_res_id': group.id,
                       'options': {'view_mailbox': False,
                                   'view_inbox': True,
                                   'read_action': 'read',
                                   'compose_placeholder': 'Send a message to the group'},
                        'params': {'header_description': group._get_header(),
                                   'name': vals['name'],}
                      }
        act_res_model = 'mail.message'
        act_search_view_id = search_ref.id 

        new_action = inbox_ref.sudo().copy(default={'domain': act_domain, 
                                                    'context': act_context,
                                                    'res_model': act_res_model,
                                                    'search_view_id': act_search_view_id,
                                                    'name': vals['name']})
        menu.write({'action': 'ir.actions.act_window,%d' % new_action.id, 'mail_channel_id': group.id})

        if vals.get('group_ids'):
            group._subscribe_users()
        return group

    @api.multi
    def unlink(self):
        aliases = self.mapped('alias_id')
        menus = self.mapped('menu_id')

        # Delete mail.channel
        try:
            all_emp_group = self.env.ref('mail.channel_all_employees')
        except ValueError:
            all_emp_group = None
        if all_emp_group and all_emp_group in self:
            raise UserError(_('You cannot delete those groups, as the Whole Company group is required by other modules.'))
        res = super(MailGroup, self).unlink()
        # Cascade-delete mail aliases as well, as they should not exist without the mail.channel.
        aliases.sudo().unlink()
        # Cascade-delete menu entries as well
        menus.sudo().unlink()
        return res

    @api.multi
    def write(self, vals):
        result = super(MailGroup, self).write(vals)
        if vals.get('group_ids'):
            self._subscribe_users()
        # if description, name or alias is changed: update action window
        if vals.get('description') or vals.get('name') or vals.get('alias_id') or vals.get('alias_name'):
            for group in self:
                if (vals.get('name')):
                    group.menu_id.action.sudo().write({'name': vals.get('name')})
        # if name is changed: update menu
        if vals.get('name'):
            self.sudo().mapped('menu_id').write({'name': vals.get('name')})
        return result

    def _get_header(self):
        self.ensure_one()
        header = '%(description)s%(gateway)s' % {
            'description': '%s<br />' % self.description if self.description else '',
            'gateway': _('Group email gateway: %s@%s') % (self.alias_name, self.alias_domain) if self.alias_name and self.alias_domain else ''
        }
        return header
    # compat
    _generate_header_description = _get_header

    def _subscribe_users(self):
        for mail_channel in self:
            partner_ids = mail_channel.mapped('group_ids').mapped('users').mapped('partner_id')
            mail_channel.message_subscribe(partner_ids.ids)

    @api.multi
    def action_follow(self):
        """ Wrapper because message_subscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_subscribe_users()

    @api.multi
    def action_unfollow(self):
        """ Wrapper because message_unsubscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_unsubscribe_users()

    @api.multi
    def message_get_email_values(self, notif_mail=None):
        self.ensure_one()
        res = super(MailGroup, self).message_get_email_values(notif_mail=notif_mail)
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
