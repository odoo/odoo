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
import io
import openerp
import openerp.tools as tools
from operator import itemgetter
from osv import osv
from osv import fields
from PIL import Image
import StringIO
import tools
from tools.translate import _

class mail_group(osv.osv):
    """
    A mail_group is a collection of users sharing messages in a discussion
    group. Group users are users that follow the mail group, using the
    subscription/follow mechanism of OpenSocial. A mail group has nothing
    in common wih res.users.group.
    Additional information on fields:
        - ``member_ids``: user member of the groups are calculated with
          ``message_get_subscribers`` method from mail.thread
        - ``member_count``: calculated with member_ids
        - ``is_subscriber``: calculated with member_ids
        
    """
    
    _description = 'Discussion group'
    _name = 'mail.group'
    _inherit = ['mail.thread']

    def onchange_photo(self, cr, uid, ids, value, context=None):
        if not value:
            return {'value': {'avatar_big': value, 'avatar': value} }
        return {'value': {'photo_big': value, 'photo': self._photo_resize(cr, uid, value) } }
    
    def _set_photo(self, cr, uid, id, name, value, args, context=None):
        if value:
            return self.write(cr, uid, [id], {'photo_big': value}, context=context)
        else:
            return self.write(cr, uid, [id], {'photo_big': value}, context=context)
    
    def _photo_resize(self, cr, uid, photo, width=128, height=128, context=None):
        image_stream = io.BytesIO(photo.decode('base64'))
        img = Image.open(image_stream)
        img.thumbnail((width, height), Image.ANTIALIAS)
        img_stream = StringIO.StringIO()
        img.save(img_stream, "JPEG")
        return img_stream.getvalue().encode('base64')
        
    def _get_photo(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for group in self.browse(cr, uid, ids, context=context):
            if group.photo_big:
                result[group.id] = self._photo_resize(cr, uid, group.photo_big, context=context)
        return result
    
    def get_member_ids(self, cr, uid, ids, field_names, args, context=None):
        if context is None:
            context = {}
        result = dict.fromkeys(ids)
        for id in ids:
            result[id] = {}
            result[id]['member_ids'] = self.message_get_subscribers(cr, uid, [id], True, context=context)
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
            result[id] = self.message_load(cr, uid, [id], limit=None, domain=[('date', '>=', lower_date)], count=True, context=context)
        return result
    
    def _get_default_photo(self, cr, uid, context=None):
        avatar_path = openerp.modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return self._photo_resize(cr, uid, open(avatar_path, 'rb').read().encode('base64'), context=context)
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'description': fields.text('Description'),
        'responsible_id': fields.many2one('res.users', string='Responsible',
                            ondelete='set null', required=True, select=1,
                            help="Responsible of the group that has all rights on the record."),
        'public': fields.boolean('Public', help='This group is visible by non members. \
                            Invisible groups can add members through the invite button.'),
        'models': fields.many2many('ir.model', rel='mail_group_ir_model_rel',
                            id1='mail_group_id', id2='model_id',
                            string='Linked models', help='Linked models'),
        'groups': fields.many2many('res.groups', rel='mail_group_res_group_rel',
                            id1='mail_group_id', id2='groups_id',
                            string='Linked groups', help='Linked groups'),
        'push_to_groups': fields.boolean('Push to groups', 
                            help="When posting a comment on this mail_group, \
                            the message is pushed to the users beloging to \
                            the linked user groups."),
        'photo_big': fields.binary('Full-size photo', help='Field holding \
                            the full-sized PIL-supported and base64 encoded \
                            version of the group image. The photo field is \
                            used as an interface for this field.'),
        'photo': fields.function(_get_photo, fnct_inv=_set_photo, string='Photo', type="binary",
            store = {
                'mail.group': (lambda self, cr, uid, ids, c={}: ids, ['photo_big'], 10),
            }, help='Field holding the automatically resized (128x128) PIL-supported and base64 encoded version of the group image.'),
        'member_ids': fields.function(get_member_ids, fnct_search=search_member_ids,
                            type='many2many', relation='res.users',
                            string='Group members', multi='get_member_ids'),
        'member_count': fields.function(get_member_ids, type='integer',
                            string='Member count', multi='get_member_ids'),
        'is_subscriber': fields.function(get_member_ids, type='boolean',
                            string='Joined', multi='get_member_ids'),
        'last_month_msg_nbr': fields.function(get_last_month_msg_nbr, type='integer',
                            string='Messages count for last month'),
    }

    _defaults = {
        'public': True,
        'responsible_id': (lambda s, cr, uid, ctx: uid),
        'photo': _get_default_photo,
    }
    
    def message_create_get_notification_user_ids(self, cr, uid, thread_ids, new_msg_vals, context=None):
        """ Overrider OpenChatter message_create_get_notification_user_ids
            method. The purpose is to add to the subscribers users that 
            belong to the res.groups linked to the mail.group through the 
            groups field. The fields push_to_groups allows to control this 
            feature.
        """
        notif_user_ids = super(mail_group, self).message_create_get_notification_user_ids(cr, uid, thread_ids, new_msg_vals, context=context)
        for thread in self.browse(cr, uid, thread_ids, context=context):
            if not thread.push_to_groups or not thread.groups:
                continue
            for group in thread.groups:
                for user in group.users:
                    notif_user_ids.append(user.id)
        return list(set(notif_user_ids))
        
    def message_load(self, cr, uid, ids, fetch_ancestors=False, ancestor_ids=None, 
                        limit=100, offset=0, domain=None, count=False, context=None):
        """ Override OpenChatter message_load method.
            if models attribute is set: search all messages from that model
            else: as usual
        """
        all_msg_ids = []
        message_obj = self.pool.get('mail.message')
        for group in self.browse(cr, uid, ids, context=context):
            # call super to have default message ids
            group_msg_ids = super(mail_group, self).message_load(cr, uid, ids, fetch_ancestors, ancestor_ids, limit, offset, domain, False, True, context)
            group_domain = ['&', ('model', '=', self._name), ('id', 'in', group_msg_ids)]
            # if no linked domain: go on
            if not group.models:
                search_domain = group_domain
            # add message ids linked to group models
            else:
                model_list = []
                for model in group.models:
                    model_list.append(model.model)
                search_domain = [('|')] + group_domain
                search_domain += [('model', 'in', model_list)]
            # perform the search
            msg_ids = message_obj.search(cr, uid, search_domain, limit=limit, offset=offset, context=context)
            if (fetch_ancestors): msg_ids = self._message_load_add_ancestor_ids(cr, uid, ids, msg_ids, ancestor_ids, context=context)
            all_msg_ids += msg_ids
        if count:
            return len(all_msg_ids)
        else:
            return message_obj.read(cr, uid, all_msg_ids, context=context)
    
    def action_group_join(self, cr, uid, ids, context=None):
        return self.message_subscribe(cr, uid, ids, context=context)
    
    def action_group_leave(self, cr, uid, ids, context=None):
        return self.message_unsubscribe(cr, uid, ids, context=context)
    
