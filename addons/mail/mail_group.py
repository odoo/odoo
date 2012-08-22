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
from tools.translate import _

class mail_group(osv.Model):
    """
    A mail_group is a collection of users sharing messages in a discussion
    group. Group users are users that follow the mail group, using the
    subscription/follow mechanism of OpenSocial. A mail group has nothing
    in common with res.users.group.
    """
    _description = 'Discussion group'
    _name = 'mail.group'
    _inherit = ['mail.thread']
    _inherits = {'mail.alias': 'alias_id', 'ir.ui.menu': 'menu_id'}

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _get_default_image(self, cr, uid, context=None):
        image_path = openerp.modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    _columns = {
        'description': fields.text('Description'),
        'menu_id': fields.many2one('ir.ui.menu', string='Related Menu', required=True, ondelete="cascade"),
        'public': fields.selection([('public','Public'),('private','Private'),('groups','Selected Group Only')], 'Privacy', required=True,
            help='This group is visible by non members. \
            Invisible groups can add members through the invite button.'),
        'group_public_id': fields.many2one('res.groups', string='Authorized Group'),
        'group_ids': fields.many2many('res.groups', rel='mail_group_res_group_rel',
            id1='mail_group_id', id2='groups_id', string='Auto Subscription',
            help="Members of those groups will automatically added as followers. "\
                 "Note that they will be able to manage their subscription manually "\
                 "if necessary."),
        'image': fields.binary("Photo",
            help="This field holds the image used as photo for the "\
                 "user. The image is base64 encoded, and PIL-supported. "\
                 "It is limited to a 1024x1024 px image."),
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
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="cascade", required=True,
            help="The email address associated with this group. New emails received will automatically "
                 "create new topics."),
    }

    def _get_default_employee_group(self, cr, uid, context=None):
        ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        return ref and ref[1] or False

    def _get_menu_parent(self, cr, uid, context=None):
        ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'mail_group_root')
        return ref and ref[1] or False

    _defaults = {
        'public': 'groups',
        'group_public_id': _get_default_employee_group,
        'image': _get_default_image,
        'parent_id': _get_menu_parent,
        'alias_domain': False, # always hide alias during creation
    }

    def _subscribe_users(self, cr, uid, ids, context=None):
        for mail_group in self.browse(cr, uid, ids, context=context):
            partner_ids = []
            for group in mail_group.group_ids:
                partner_ids += [user.partner_id.id for user in group.users]
            self.message_subscribe(cr, uid, ids, partner_ids, context=context)

    def create(self, cr, uid, vals, context=None):
        mail_alias = self.pool.get('mail.alias')
        if not vals.get('alias_id'):
            vals.pop('alias_name', None) # prevent errors during copy()
            alias_id = mail_alias.create_unique_alias(cr, uid,
                          # Using '+' allows using subaddressing for those who don't
                          # have a catchall domain setup.
                          {'alias_name': "group+"+vals['name']},
                          model_name=self._name, context=context)
            vals['alias_id'] = alias_id

        mail_group_id = super(mail_group, self).create(cr, uid, vals, context)

        # Create client action for this group and link the menu to it
        ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'action_mail_group_feeds')
        if ref:
            search_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'view_message_search')
            params = {
                'search_view_id': search_ref and search_ref[1] or False,
                'domain': [('model','=','mail.group'),('res_id','=',mail_group_id)],
                'res_model': 'mail.message',
                'thread_level': 2
            }
            cobj = self.pool.get('ir.actions.client')
            newref = cobj.copy(cr, uid, ref[1], default={'params': str(params), 'name': vals['name']}, context=context)
            self.write(cr, uid, [mail_group_id], {'action': 'ir.actions.client,'+str(newref), 'mail_group_id': mail_group_id}, context=context)

        mail_alias.write(cr, uid, [vals['alias_id']], {"alias_force_thread_id": mail_group_id}, context)

        if vals.get('group_ids'):
            self._subscribe_users(cr, uid, [mail_group_id], context=context)
        return mail_group_id

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the mail group.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [group.alias_id.id for group in self.browse(cr, uid, ids, context=context) if group.alias_id]
        res = super(mail_group, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        result = super(mail_group, self).write(cr, uid, ids, vals, context=context)
        if vals.get('group_ids'):
            self._subscribe_users(cr, uid, ids, vals.get('group_ids'), context=context)
        return result

