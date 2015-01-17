# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import random
import openerp
import json
import openerp.addons.im_chat.im_chat

from openerp.osv import osv, fields
from openerp import tools
from openerp import http
from openerp.http import request

class im_livechat_channel(osv.Model):
    _name = 'im_livechat.channel'

    def _get_default_image(self, cr, uid, context=None):
        image_path = openerp.modules.get_module_resource('im_livechat', 'static/src/img', 'default.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))
    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image)
        return result
    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    def _are_you_inside(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = False
            for user in record.user_ids:
                if user.id == uid:
                    res[record.id] = True
                    break
        return res

    def _script_external(self, cr, uid, ids, name, arg, context=None):
        values = {
            "url": self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url'),
            "dbname":cr.dbname
        }
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            values["channel"] = record.id
            res[record.id] = self.pool['ir.ui.view'].render(cr, uid, 'im_livechat.external_loader', values, context=context)
        return res

    def _script_internal(self, cr, uid, ids, name, arg, context=None):
        values = {
            "url": self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url'),
            "dbname":cr.dbname
        }
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            values["channel"] = record.id
            res[record.id] = self.pool['ir.ui.view'].render(cr, uid, 'im_livechat.internal_loader', values, context=context)
        return res

    def _web_page(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url') + \
                "/im_livechat/support/%s/%i" % (cr.dbname, record.id)
        return res

    _columns = {
        'name': fields.char(string="Channel Name", size=200, required=True),
        'user_ids': fields.many2many('res.users', 'im_livechat_channel_im_user', 'channel_id', 'user_id', string="Users"),
        'are_you_inside': fields.function(_are_you_inside, type='boolean', string='Are you inside the matrix?', store=False),
        'script_internal': fields.function(_script_internal, type='text', string='Script (internal)', store=False),
        'script_external': fields.function(_script_external, type='text', string='Script (external)', store=False),
        'web_page': fields.function(_web_page, type='char', string='Web Page', store=False),
        'button_text': fields.char(string="Text of the Button"),
        'input_placeholder': fields.char(string="Chat Input Placeholder"),
        'default_message': fields.char(string="Welcome Message", help="This is an automated 'welcome' message that your visitor will see when they initiate a new chat session."),
        # image: all image fields are base64 encoded and PIL-supported
        'image': fields.binary("Photo",
            help="This field holds the image used as photo for the group, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized photo", type="binary", multi="_get_image",
            store={
                'im_livechat.channel': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized photo of the group. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved. "\
                 "Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized photo", type="binary", multi="_get_image",
            store={
                'im_livechat.channel': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized photo of the group. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
    }

    def _default_user_ids(self, cr, uid, context=None):
        return [(6, 0, [uid])]

    _defaults = {
        'button_text': "Have a Question? Chat with us.",
        'input_placeholder': "How may I help you?",
        'default_message': '',
        'user_ids': _default_user_ids,
        'image': _get_default_image,
    }

    def get_available_users(self, cr, uid, channel_id, context=None):
        """ get available user of a given channel """
        channel = self.browse(cr, uid, channel_id, context=context)
        users = []
        for user_id in channel.user_ids:
            if (user_id.im_status == 'online'):
                users.append(user_id)
        return users

    def get_channel_session(self, cr, uid, channel_id, anonymous_name, context=None):
        """ return a session given a channel : create on with a registered user, or return false otherwise """
        # get the avalable user of the channel
        users = self.get_available_users(cr, uid, channel_id, context=context)
        if len(users) == 0:
            return False
        user_id = random.choice(users).id
        # create the session, and add the link with the given channel
        Session = self.pool["im_chat.session"]
        newid = Session.create(cr, uid, {'user_ids': [(4, user_id)], 'channel_id': channel_id, 'anonymous_name' : anonymous_name}, context=context)
        return Session.session_info(cr, uid, [newid], context=context)

    def test_channel(self, cr, uid, channel, context=None):
        if not channel:
            return {}
        return {
            'url': self.browse(cr, uid, channel[0], context=context or {}).web_page,
            'type': 'ir.actions.act_url'
        }

    def get_info_for_chat_src(self, cr, uid, channel, context=None):
        url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        chan = self.browse(cr, uid, channel, context=context)
        return {
            "url": url,
            'buttonText': chan.button_text,
            'inputPlaceholder': chan.input_placeholder,
            'defaultMessage': chan.default_message,
            "channelName": chan.name,
        }

    def join(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'user_ids': [(4, uid)]})
        return True

    def quit(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'user_ids': [(3, uid)]})
        return True

class im_chat_session(osv.Model):
    _inherit = 'im_chat.session'

    def _get_fullname(self, cr, uid, ids, fields, arg, context=None):
        """ built the complete name of the session """
        result = {}
        sessions = self.browse(cr, uid, ids, context=context)
        for session in sessions:
            names = []
            for user in session.user_ids:
                names.append(user.name)
            if session.anonymous_name:
                names.append(session.anonymous_name)
            result[session.id] = ', '.join(names)
        return result

    _columns = {
        'anonymous_name' : fields.char('Anonymous Name'),
        'channel_id': fields.many2one("im_livechat.channel", "Channel"),
        'fullname' : fields.function(_get_fullname, type="char", string="Complete name"),
    }

    def is_in_session(self, cr, uid, uuid, user_id, context=None):
        """ return if the given user_id is in the session """
        sids = self.search(cr, uid, [('uuid', '=', uuid)], context=context, limit=1)
        for session in self.browse(cr, uid, sids, context=context):
            if session.anonymous_name and user_id == openerp.SUPERUSER_ID:
                return True
            else:
                return super(im_chat_session, self).is_in_session(cr, uid, uuid, user_id, context=context)
        return False

    def users_infos(self, cr, uid, ids, context=None):
        """ add the anonymous user in the user of the session """
        for session in self.browse(cr, uid, ids, context=context):
            users_infos = super(im_chat_session, self).users_infos(cr, uid, ids, context=context)
            if session.anonymous_name:
                users_infos.append({'id' : False, 'name' : session.anonymous_name, 'im_status' : 'online'})
            return users_infos


class LiveChatController(http.Controller):

    @http.route('/im_livechat/support/<string:dbname>/<int:channel_id>', type='http', auth='none')
    def support_page(self, dbname, channel_id, **kwargs):
        registry, cr, uid, context = openerp.modules.registry.RegistryManager.get(dbname), request.cr, openerp.SUPERUSER_ID, request.context
        info = registry.get('im_livechat.channel').get_info_for_chat_src(cr, uid, channel_id)
        info["dbname"] = dbname
        info["channel"] = channel_id
        info["channel_name"] = registry.get('im_livechat.channel').read(cr, uid, channel_id, ['name'], context=context)["name"]
        return request.render('im_livechat.support_page', info)

    @http.route('/im_livechat/loader/<string:dbname>/<int:channel_id>', type='http', auth='none')
    def loader(self, dbname, channel_id, **kwargs):
        registry, cr, uid, context = openerp.modules.registry.RegistryManager.get(dbname), request.cr, openerp.SUPERUSER_ID, request.context
        info = registry.get('im_livechat.channel').get_info_for_chat_src(cr, uid, channel_id)
        info["dbname"] = dbname
        info["channel"] = channel_id
        info["username"] = kwargs.get("username", "Visitor")
        return request.render('im_livechat.loader', info)

    @http.route('/im_livechat/get_session', type="json", auth="none")
    def get_session(self, channel_id, anonymous_name, **kwargs):
        cr, uid, context, db = request.cr, request.uid or openerp.SUPERUSER_ID, request.context, request.db
        reg = openerp.modules.registry.RegistryManager.get(db)
        # if geoip, add the country name to the anonymous name
        if hasattr(request, 'geoip'):
            anonymous_name = anonymous_name + " ("+request.geoip.get('country_name', "")+")"
        return reg.get("im_livechat.channel").get_channel_session(cr, uid, channel_id, anonymous_name, context=context)

    @http.route('/im_livechat/available', type='json', auth="none")
    def available(self, db, channel):
        cr, uid, context, db = request.cr, request.uid or openerp.SUPERUSER_ID, request.context, request.db
        reg = openerp.modules.registry.RegistryManager.get(db)
        with reg.cursor() as cr:
            return len(reg.get('im_livechat.channel').get_available_users(cr, uid, channel)) > 0

