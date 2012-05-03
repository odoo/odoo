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
        'models': fields.many2many('ir.model', rel='mail_group_models_rel',
                            id1='mail_group_id', id2='model_id',
                            string='Linked models', help='Linked models'),
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
    
    def message_load(self, cr, uid, ids, limit=100, offset=0, domain=[], ascent=False, root_ids=[], context=None):
        """ Override OpenChatter method.
            if models attribute is set: search all messages from that model
            else: as usual
            :param domain: domain to add to the search; especially child_of
                           is interesting when dealing with threaded display
            :param ascent: performs an ascended search; will add to fetched msgs
                           all their parents until root_ids
            :param root_ids: for ascent search
            :param root_ids: root_ids when performing an ascended search
        """
        search_domain = []
        for group in self.browse(cr, uid, ids, context=context):
            # call super to have default message ids
            message_obj = self.pool.get('mail.message')
            group_msgs = super(mail_group, self).message_load(cr, uid, ids, limit, offset, domain, ascent, root_ids, context)
            msg_ids = map(itemgetter('id'), group_msgs)
            search_domain = ['|', '&', ('model', '=', self._name), ('id', 'in', ids)]
            # add message ids linked to group models
            model_list = []
            for model in group.models:
                model_list.append(model.model)
            search_domain.append(('model', 'in', model_list))
            msg_ids += message_obj.search(cr, uid, search_domain, limit=limit, offset=offset, context=context)
        return message_obj.read(cr, uid, msg_ids, context=context)
    
    def action_group_join(self, cr, uid, ids, context=None):
        return self.message_subscribe(cr, uid, ids, context=context)
    
    def action_group_leave(self, cr, uid, ids, context=None):
        return self.message_unsubscribe(cr, uid, ids, context=context)
    
