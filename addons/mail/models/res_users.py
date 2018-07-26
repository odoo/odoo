# -*- coding: utf-8 -*-

from openerp import _, api, fields, models
import openerp


class Users(models.Model):
    """ Update of res.users class
        - add a preference about sending emails about notifications
        - make a new user follow itself
        - add a welcome message
        - add suggestion preference
        - if adding groups to an user, check mail.channels linked to this user
          group, and the user. This is done by overriding the write method.
    """
    _name = 'res.users'
    _inherit = ['res.users']
    _inherits = {'mail.alias': 'alias_id'}

    alias_id = fields.Many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
            help="Email address internally associated with this user. Incoming "\
                 "emails will appear in the user's notifications.", copy=False, auto_join=True)
    chatter_needaction_auto = fields.Boolean('Automatically set needaction as Read')

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on notification_email_send
            and alias fields. Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(Users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.extend(['notify_email'])
        # duplicate list to avoid modifying the original reference
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.extend(['notify_email', 'alias_domain', 'alias_name'])
        return init_res

    def _auto_init(self, cr, context=None):
        """ Installation hook: aliases """
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(Users, self)._auto_init, self._name, self._columns['alias_id'], 'login', alias_force_key='id', context=context)

    @api.model
    def create(self, values):
        if not values.get('login', False):
            action = self.env.ref('base.action_res_users')
            msg = _("You cannot create a new user from here.\n To create new user please go to configuration panel.")
            raise openerp.exceptions.RedirectWarning(msg, action.id, _('Go to the configuration panel'))

        user = super(Users, self.with_context(
            alias_model_name=self._name,
            alias_parent_model_name=self._name
        )).create(values)
        user.alias_id.sudo().write({"alias_force_thread_id": user.id, "alias_parent_thread_id": user.id})

        # create a welcome message
        user._create_welcome_message()
        return user

    @api.multi
    def write(self, vals):
        write_res = super(Users, self).write(vals)
        if vals.get('groups_id'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_group_ids = [command[1] for command in vals['groups_id'] if command[0] == 4]
            user_group_ids += [id for command in vals['groups_id'] if command[0] == 6 for id in command[2]]
            self.env['mail.channel'].search([('group_ids', 'in', user_group_ids)])._subscribe_users()
        return write_res

    def copy_data(self, *args, **kwargs):
        data = super(Users, self).copy_data(*args, **kwargs)
        if data and data.get('alias_name'):
            data['alias_name'] = data['login']
        return data

    def _create_welcome_message(self):
        self.ensure_one()
        if not self.has_group('base.group_user'):
            return False
        company_name = self.company_id.name if self.company_id else ''
        body = _('%s has joined the %s network.') % (self.name, company_name)
        # TODO change SUPERUSER_ID into user.id but catch errors
        return self.partner_id.sudo().message_post(body=body)

    @api.multi
    def unlink(self):
        # Cascade-delete mail aliases as well, as they should not exist without the user.
        aliases = self.mapped('alias_id')
        res = super(Users, self).unlink()
        aliases.unlink()
        return res

    def _message_post_get_pid(self):
        self.ensure_one()
        if 'thread_model' in self.env.context:
            self = self.with_context(thread_model='res.users')
        return self.partner_id.id

    @api.multi
    def message_post(self, **kwargs):
        """ Redirect the posting of message on res.users as a private discussion.
            This is done because when giving the context of Chatter on the
            various mailboxes, we do not have access to the current partner_id. """
        current_pids = []
        partner_ids = kwargs.get('partner_ids', [])
        user_pid = self._message_post_get_pid()
        for partner_id in partner_ids:
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                current_pids.append(partner_id[1])
            elif isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                current_pids.append(partner_id[2])
            elif isinstance(partner_id, (int, long)):
                current_pids.append(partner_id)
        if user_pid not in current_pids:
            partner_ids.append(user_pid)
        kwargs['partner_ids'] = partner_ids
        # ??
        # if context and context.get('thread_model') == 'res.partner':
        #   return self.pool['res.partner'].message_post(cr, uid, user_pid, **kwargs)
        return self.env['mail.thread'].message_post(**kwargs)  # ??

    def message_update(self, msg_dict, update_vals=None):
        return True

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None, force=True):
        return True

    @api.cr_uid_context
    def message_get_partner_info_from_emails(self, cr, uid, emails, link_mail=False, context=None):
        return self.pool.get('mail.thread').message_get_partner_info_from_emails(cr, uid, emails, link_mail=link_mail, context=context)

    @api.multi
    def message_get_suggested_recipients(self):
        return dict((res_id, list()) for res_id in self._ids)


class res_groups_mail_channel(models.Model):
    """ Update of res.groups class
        - if adding users from a group, check mail.channels linked to this user
          group and subscribe them. This is done by overriding the write method.
    """
    _name = 'res.groups'
    _inherit = 'res.groups'

    @api.multi
    def write(self, vals, context=None):
        write_res = super(res_groups_mail_channel, self).write(vals)
        if vals.get('users'):
            # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
            user_ids = [command[1] for command in vals['users'] if command[0] == 4]
            user_ids += [id for command in vals['users'] if command[0] == 6 for id in command[2]]
            self.env['mail.channel'].search([('group_ids', 'in', self._ids)])._subscribe_users()
        return write_res
