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

    def action_group_join(self, cr, uid, ids, context={}):
        return self.message_subscribe(cr, uid, ids, context=context);
    
    def action_group_leave(self, cr, uid, ids, context={}):
        return self.message_unsubscribe(cr, uid, ids, context=context);

    def _get_image_resized(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for mail_group in self.browse(cr, uid, ids, context=context):
            result[mail_group.id] = {'image_medium': False, 'image_small': False}
            if mail_group.image:
                result[mail_group.id]['image_medium'] = tools.resize_image_medium(mail_group.image)
                result[mail_group.id]['image_small'] = tools.resize_image_small(mail_group.image)
        return result
    
    def _set_image_resized(self, cr, uid, id, name, value, args, context=None):
        if not value:
            vals = {'image': value}
        else:
            vals = {'image': tools.resize_image_big(value)}
        return self.write(cr, uid, [id], vals, context=context)
    
    def onchange_image(self, cr, uid, ids, value, context=None):
        if not value:
            return {'value': {
                    'image': value,
                    'image_medium': value,
                    'image_small': value,
                    }}
        return {'value': {
                    'image': tools.resize_image_big(value),
                    'image_medium': tools.resize_image_medium(value),
                    'image_small': tools.resize_image_small(value),
                    }}
    
    def get_member_ids(self, cr, uid, ids, field_names, args, context=None):
        if context is None:
            context = {}
        result = dict.fromkeys(ids)
        for id in ids:
            result[id] = {}
            result[id]['member_ids'] = self.message_get_subscribers_ids(cr, uid, [id], context=context)
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
            result[id] = message_obj.search(cr, uid, ['&', '&', ('model', '=', self._name), ('res_id', 'in', ids), ('date', '>=', lower_date)], count=True, context=context)
        return result
    
    def _get_photo(self, cr, uid, context=None):
        image_path = openerp.modules.get_module_resource('mail', 'static/src/img', 'groupdefault.png')
        return tools.resize_image_big(open(image_path, 'rb').read().encode('base64'))
    
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'description': fields.text('Description'),
        'responsible_id': fields.many2one('res.users', string='Responsible',
                            ondelete='set null', required=True, select=1,
                            help="Responsible of the group that has all rights on the record."),
        'public': fields.boolean('Public', help='This group is visible by non members. Invisible groups can add members through the invite button.'),
        'image': fields.binary("Photo",
            help="This field holds the photo used as image for the "\
                 "group. The avatar field is used as an interface to "\
                 "access this field. The image is base64 encoded, "\
                 "and PIL-supported. It is stored as a 540x450 px "\
                 "image, in case a bigger image must be used."),
        'image_medium': fields.function(_get_image_resized, fnct_inv=_set_image_resized,
            string="Medium-sized photo", type="binary", multi="_get_image_resized",
            store = {
                'mail.group': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized photo of the group. It is automatically "\
                 "resized as a 180x180px image, with aspect ratio keps. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image_resized, fnct_inv=_set_image_resized,
            string="Smal-sized photo", type="binary", multi="_get_image_resized",
            store = {
                'mail.group': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the group. It is automatically "\
                 "resized as a 50x50px image, with aspect ratio keps. "\
                 "Use this field in form views or some kanban views."),
        'member_ids': fields.function(get_member_ids, fnct_search=search_member_ids, type='many2many',
                        relation='res.users', string='Group members', multi='get_member_ids'),
        'member_count': fields.function(get_member_ids, type='integer', string='Member count', multi='get_member_ids'),
        'is_subscriber': fields.function(get_member_ids, type='boolean', string='Joined', multi='get_member_ids'),
        'last_month_msg_nbr': fields.function(get_last_month_msg_nbr, type='integer', string='Messages count for last month'),
    }

    _defaults = {
        'public': True,
        'responsible_id': (lambda s, cr, uid, ctx: uid),
        'image_medium': _get_photo,
    }
