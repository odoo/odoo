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

import datetime as DT
import openerp
import openerp.tools as tools
from operator import itemgetter
from osv import osv
from osv import fields
import tools
from tools.translate import _
from lxml import etree

class ir_ui_menu(osv.osv):
    _inherit = 'ir.ui.menu'
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        context = context or {}
        ids = super(ir_ui_menu, self).search(cr, uid, args, offset=0,
            limit=None, order=order, context=context, count=False)
        if context.get('ir.ui.menu.full_list'):
            return ids

        root_group = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'mail_group_root')
        if not root_group:
            return ids
        root_group = root_group[1]

        print 'Root Group', root_group, ids, args
        for a in args:
            if a[0]=='id':
                return ids
            if a[0]=='parent_id':
                if (a[1] == 'child_of'):
                    if root_group not in ids:
                        return ids
                elif (a[1] == 'in'):
                    if root_group not in a[2]:
                        return ids
                elif (a[1] <> '='):
                    if a[2] <> root_group:
                        return ids

        print 'Got IT'
        subs = self.pool.get('mail.subscription')
        sub_ids = subs.search(cr, uid, [('user_id','=',uid),('res_model','=','mail.group')], context=context)
        result = ids + map(lambda x: 'group-'+str(x.res_id), subs.browse(cr, uid, sub_ids, context=context))
        print 'END SEARCH', result
        return result

    def _read_flat(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        group_ids = filter(lambda x: type(x)==str and x.startswith('group-'), ids)
        nongroup_ids = filter(lambda x: x not in group_ids, ids)
        print 'READ ***', ids, nongroup_ids, group_ids
        result = super(ir_ui_menu, self)._read_flat(cr, uid, nongroup_ids, fields, context, load)

        group_ids = map(lambda x: int(x[6:]), group_ids)
        root_group = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'mail_group_root')
        if not root_group:
            return result
        root_group = root_group[1]

        for group in self.pool.get('mail.group').browse(cr, uid, group_ids, context=context):
            data = {
                'id': 'group-'+str(group.id),
                'name': group.name,
                'child_id': [],
                'parent_id': root_group,
                'complete_name': group.name,
                'needaction_enabled': 1,
                'needaction_counter': 1,  # to compute
                'action': 'ir.actions.client,1'
            }
            for key in fields or []:
                data.setdefault(key, False)
            for key in data.keys():
                if fields and key not in fields:
                    del data[key]
            result.append(data)

        print result
        return result


    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result
    
    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)
    
    def get_member_ids(self, cr, uid, ids, field_names, args, context=None):
        if context is None:
            context = {}
        result = dict.fromkeys(ids)
        for id in ids:
            result[id] = {}
            result[id]['member_ids'] = self.message_get_subscribers(cr, uid, [id], context=context)
            result[id]['member_count'] = len(result[id]['member_ids'])
            result[id]['is_subscriber'] = uid in result[id]['member_ids']
        return result
    
    def search_member_ids(self, cr, uid, obj, name, args, context=None):
        if context is None:
            context = {}
        sub_obj = self.pool.get('mail.subscription')
        sub_ids = sub_obj.search(cr, uid, ['&', ('res_model', '=', obj._name), ('user_id', '=', args[0][2])], context=context)
        subs = sub_obj.read(cr, uid, sub_ids, context=context)
        return [('id', 'in', map(itemgetter('res_id'), subs))]
    
    def get_last_month_msg_nbr(self, cr, uid, ids, name, args, context=None):
        result = {}
        message_obj = self.pool.get('mail.message')
        for id in ids:
            lower_date = (DT.datetime.now() - DT.timedelta(days=30)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
            result[id] = self.message_search(cr, uid, [id], limit=None, domain=[('date', '>=', lower_date)], count=True, context=context)
        return result
    
    def _get_default_image(self, cr, uid, context=None):
        image_path = openerp.modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))
    
    _columns = {
        'name': fields.char('Group Name', size=64, required=True),
        'description': fields.text('Description'),
        'responsible_id': fields.many2one('res.users', string='Responsible',
            ondelete='set null', required=True, select=1,
            help="Responsible of the group that has all rights on the record."),
        'public': fields.selection([('public','Public'),('private','Private'),('employee','Employees Only')], 'Privacy', required=True,
            help='This group is visible by non members. \
            Invisible groups can add members through the invite button.'),
        'group_ids': fields.many2many('res.groups', rel='mail_group_res_group_rel',
            id1='mail_group_id', id2='groups_id', string='Auto Subscription',
            help="Members of those groups will automatically added as followers. "\
                    "Note that they will be able to manage their subscription manually "\
                    "if necessary."),
        'image': fields.binary("Photo",
            help="This field holds the image used as photo for the "\
                 "user. The image is base64 encoded, and PIL-supported. "\
                 "It is limited to a 12024x1024 px image."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized photo", type="binary", multi="_get_image",
            store = {
                'mail.group': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized photo of the group. It is automatically "\
                 "resized as a 180x180px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized photo", type="binary", multi="_get_image",
            store = {
                'mail.group': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the group. It is automatically "\
                 "resized as a 50x50px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'member_ids': fields.function(get_member_ids, fnct_search=search_member_ids,
            type='many2many', relation='res.users', string='Group members', multi='get_member_ids'),
        'member_count': fields.function(get_member_ids, type='integer',
            string='Member count', multi='get_member_ids'),
        'is_subscriber': fields.function(get_member_ids, type='boolean',
            string='Joined', multi='get_member_ids'),
        'last_month_msg_nbr': fields.function(get_last_month_msg_nbr, type='integer',
            string='Messages count for last month'),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="cascade", required=True, 
                                    help="The email address associated with this group. New emails received will automatically "
                                         "create new topics."),
    }

    _defaults = {
        'public': 'employee',
        'responsible_id': (lambda s, cr, uid, ctx: uid),
        'image': _get_default_image,
    }

    def _subscribe_user_with_group_m2m_command(self, cr, uid, ids, group_ids_command, context=None):
        # form: {'group_ids': [(3, 10), (3, 3), (4, 10), (4, 3)]} or {'group_ids': [(6, 0, [ids]}
        user_group_ids = [command[1] for command in group_ids_command if command[0] == 4]
        user_group_ids += [id for command in group_ids_command if command[0] == 6 for id in command[2]]
        # retrieve the user member of those groups
        user_ids = []
        res_groups_obj = self.pool.get('res.groups')
        for group in res_groups_obj.browse(cr, uid, user_group_ids, context=context):
            user_ids += [user.id for user in group.users]
        # subscribe the users
        return self.message_subscribe(cr, uid, ids, user_ids, context=context)

    def create(self, cr, uid, vals, context=None):
        alias_pool = self.pool.get('mail.alias')
        if not vals.get('alias_id'):
            name = vals.get('alias_name') or vals['name']
            alias_id = alias_pool.create_unique_alias(cr, uid, 
                    {'alias_name': "group_"+name}, 
                    model_name=self._name, context=context)
            vals['alias_id'] = alias_id
        mail_group_id = super(mail_group, self).create(cr, uid, vals, context)
        alias_pool.write(cr, uid, [vals['alias_id']], {"alias_force_thread_id": mail_group_id}, context)
       
        if vals.get('group_ids'):
            self._subscribe_user_with_group_m2m_command(cr, uid, [mail_group_id], vals.get('group_ids'), context=context)

        return mail_group_id

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the mail group.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [group.alias_id.id for group in self.browse(cr, uid, ids, context=context) if group.alias_id]
        res = super(mail_group, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('group_ids'):
            self._subscribe_user_with_group_m2m_command(cr, uid, ids, vals.get('group_ids'), context=context)
        return super(mail_group, self).write(cr, uid, ids, vals, context=context)

    def action_group_join(self, cr, uid, ids, context=None):
        return self.message_subscribe(cr, uid, ids, context=context)

    def action_group_leave(self, cr, uid, ids, context=None):
        return self.message_unsubscribe(cr, uid, ids, context=context)
