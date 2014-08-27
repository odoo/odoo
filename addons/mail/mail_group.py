# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import openerp
import openerp.tools as tools
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.safe_eval import safe_eval as eval
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

class mail_group(osv.Model):
    """ A mail_group is a collection of users sharing messages in a discussion
        group. The group mechanics are based on the followers. """
    _description = 'Discussion group'
    _name = 'mail.group'
    _mail_flat_thread = False
    _inherit = ['mail.thread']
    _inherits = {'mail.alias': 'alias_id'}

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'description': fields.text('Description'),
        'menu_id': fields.many2one('ir.ui.menu', string='Related Menu', required=True, ondelete="cascade"),
        'public': fields.selection([('public', 'Public'), ('private', 'Private'), ('groups', 'Selected Group Only')], 'Privacy', required=True,
            help='This group is visible by non members. \
            Invisible groups can add members through the invite button.'),
        'group_public_id': fields.many2one('res.groups', string='Authorized Group'),
        'group_ids': fields.many2many('res.groups', rel='mail_group_res_group_rel',
            id1='mail_group_id', id2='groups_id', string='Auto Subscription',
            help="Members of those groups will automatically added as followers. "\
                 "Note that they will be able to manage their subscription manually "\
                 "if necessary."),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Photo",
            help="This field holds the image used as photo for the group, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized photo", type="binary", multi="_get_image",
            store={
                'mail.group': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized photo of the group. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized photo", type="binary", multi="_get_image",
            store={
                'mail.group': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the group. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
            help="The email address associated with this group. New emails received will automatically "
                 "create new topics."),
    }

    def _get_default_employee_group(self, cr, uid, context=None):
        ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        return ref and ref[1] or False

    def _get_default_image(self, cr, uid, context=None):
        image_path = openerp.modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    _defaults = {
        'public': 'groups',
        'group_public_id': _get_default_employee_group,
        'image': _get_default_image,
    }

    def _generate_header_description(self, cr, uid, group, context=None):
        header = ''
        if group.description:
            header = '%s' % group.description
        if group.alias_id and group.alias_name and group.alias_domain:
            if header:
                header = '%s<br/>' % header
            return '%sGroup email gateway: %s@%s' % (header, group.alias_name, group.alias_domain)
        return header

    def _subscribe_users(self, cr, uid, ids, context=None):
        for mail_group in self.browse(cr, uid, ids, context=context):
            partner_ids = []
            for group in mail_group.group_ids:
                partner_ids += [user.partner_id.id for user in group.users]
            self.message_subscribe(cr, uid, ids, partner_ids, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}

        # get parent menu
        menu_parent = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'mail_group_root')
        menu_parent = menu_parent and menu_parent[1] or False

        # Create menu id
        mobj = self.pool.get('ir.ui.menu')
        menu_id = mobj.create(cr, SUPERUSER_ID, {'name': vals['name'], 'parent_id': menu_parent}, context=context)
        vals['menu_id'] = menu_id

        # Create group and alias
        create_context = dict(context, alias_model_name=self._name, alias_parent_model_name=self._name, mail_create_nolog=True)
        mail_group_id = super(mail_group, self).create(cr, uid, vals, context=create_context)
        group = self.browse(cr, uid, mail_group_id, context=context)
        self.pool.get('mail.alias').write(cr, uid, [group.alias_id.id], {"alias_force_thread_id": mail_group_id, 'alias_parent_thread_id': mail_group_id}, context)
        group = self.browse(cr, uid, mail_group_id, context=context)

        # Create client action for this group and link the menu to it
        ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'action_mail_group_feeds')
        if ref:
            search_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'view_message_search')
            params = {
                'search_view_id': search_ref and search_ref[1] or False,
                'domain': [
                    ('model', '=', 'mail.group'),
                    ('res_id', '=', mail_group_id),
                ],
                'context': {
                    'default_model': 'mail.group',
                    'default_res_id': mail_group_id,
                },
                'res_model': 'mail.message',
                'thread_level': 1,
                'header_description': self._generate_header_description(cr, uid, group, context=context),
                'view_mailbox': True,
                'compose_placeholder': 'Send a message to the group',
            }
            cobj = self.pool.get('ir.actions.client')
            newref = cobj.copy(cr, SUPERUSER_ID, ref[1], default={'params': str(params), 'name': vals['name']}, context=context)
            mobj.write(cr, SUPERUSER_ID, menu_id, {'action': 'ir.actions.client,' + str(newref), 'mail_group_id': mail_group_id}, context=context)

        if vals.get('group_ids'):
            self._subscribe_users(cr, uid, [mail_group_id], context=context)
        return mail_group_id

    def unlink(self, cr, uid, ids, context=None):
        groups = self.browse(cr, uid, ids, context=context)
        alias_ids = [group.alias_id.id for group in groups if group.alias_id]
        menu_ids = [group.menu_id.id for group in groups if group.menu_id]
        # Delete mail_group
        try:
            all_emp_group = self.pool['ir.model.data'].get_object_reference(cr, uid, 'mail', 'group_all_employees')[1]
        except ValueError:
            all_emp_group = None
        if all_emp_group and all_emp_group in ids:
            raise osv.except_osv(_('Warning!'), _('You cannot delete those groups, as the Whole Company group is required by other modules.'))
        res = super(mail_group, self).unlink(cr, uid, ids, context=context)
        # Cascade-delete mail aliases as well, as they should not exist without the mail group.
        self.pool.get('mail.alias').unlink(cr, SUPERUSER_ID, alias_ids, context=context)
        # Cascade-delete menu entries as well
        self.pool.get('ir.ui.menu').unlink(cr, SUPERUSER_ID, menu_ids, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        result = super(mail_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('group_ids'):
            self._subscribe_users(cr, uid, ids, context=context)
        # if description, name or alias is changed: update client action
        if vals.get('description') or vals.get('name') or vals.get('alias_id') or vals.get('alias_name'):
            cobj = self.pool.get('ir.actions.client')
            for action in [group.menu_id.action for group in self.browse(cr, uid, ids, context=context)]:
                new_params = action.params
                new_params['header_description'] = self._generate_header_description(cr, uid, group, context=context)
                cobj.write(cr, SUPERUSER_ID, [action.id], {'params': str(new_params)}, context=context)
        # if name is changed: update menu
        if vals.get('name'):
            mobj = self.pool.get('ir.ui.menu')
            mobj.write(cr, SUPERUSER_ID,
                [group.menu_id.id for group in self.browse(cr, uid, ids, context=context)],
                {'name': vals.get('name')}, context=context)

        return result

    def action_follow(self, cr, uid, ids, context=None):
        """ Wrapper because message_subscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_subscribe_users(cr, uid, ids, context=context)

    def action_unfollow(self, cr, uid, ids, context=None):
        """ Wrapper because message_unsubscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_unsubscribe_users(cr, uid, ids, context=context)

    def get_suggested_thread(self, cr, uid, removed_suggested_threads=None, context=None):
        """Show the suggestion of groups if display_groups_suggestions if the
        user perference allows it."""
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if not user.display_groups_suggestions:
            return []
        else:
            return super(mail_group, self).get_suggested_thread(cr, uid, removed_suggested_threads, context)

    def message_get_email_values(self, cr, uid, id, notif_mail=None, context=None):
        res = super(mail_group, self).message_get_email_values(cr, uid, id, notif_mail=notif_mail, context=context)
        group = self.browse(cr, uid, id, context=context)
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
        if group.alias_domain and group.alias_name:
            headers['List-Id'] = '%s.%s' % (group.alias_name, group.alias_domain)
            headers['List-Post'] = '<mailto:%s@%s>' % (group.alias_name, group.alias_domain)
            # Avoid users thinking it was a personal message
            # X-Forge-To: will replace To: after SMTP envelope is determined by ir.mail.server
            list_to = '"%s" <%s@%s>' % (group.name, group.alias_name, group.alias_domain)
            headers['X-Forge-To'] = list_to
        res['headers'] = repr(headers)
        return res
