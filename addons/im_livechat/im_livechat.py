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

import json
import random
import jinja2

import openerp
import openerp.addons.im.im as im
from openerp.osv import osv, fields
from openerp import tools
from openerp import http
from openerp.http import request

env = jinja2.Environment(
    loader=jinja2.PackageLoader('openerp.addons.im_livechat', "."),
    autoescape=False
)
env.filters["json"] = json.dumps

class LiveChatController(http.Controller):

    def _auth(self, db):
        reg = openerp.modules.registry.RegistryManager.get(db)
        uid = request.uid
        return reg, uid

    @http.route('/im_livechat/loader', auth="public")
    def loader(self, **kwargs):
        p = json.loads(kwargs["p"])
        db = p["db"]
        channel = p["channel"]
        user_name = p.get("user_name", None)

        reg, uid = self._auth(db)
        with reg.cursor() as cr:
            info = reg.get('im_livechat.channel').get_info_for_chat_src(cr, uid, channel)
            info["db"] = db
            info["channel"] = channel
            info["userName"] = user_name
            return request.make_response(env.get_template("loader.js").render(info),
                 headers=[('Content-Type', "text/javascript")])

    @http.route('/im_livechat/web_page', auth="public")
    def web_page(self, **kwargs):
        p = json.loads(kwargs["p"])
        db = p["db"]
        channel = p["channel"]
        reg, uid = self._auth(db)
        with reg.cursor() as cr:
            script = reg.get('im_livechat.channel').read(cr, uid, channel, ["script"])["script"]
            info = reg.get('im_livechat.channel').get_info_for_chat_src(cr, uid, channel)
            info["script"] = script
            return request.make_response(env.get_template("web_page.html").render(info),
                 headers=[('Content-Type', "text/html")])

    @http.route('/im_livechat/available', type='json', auth="public")
    def available(self, db, channel):
        reg, uid = self._auth(db)
        with reg.cursor() as cr:
            return len(reg.get('im_livechat.channel').get_available_users(cr, uid, channel)) > 0

class im_livechat_channel(osv.osv):
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

    def _script(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = env.get_template("include.html").render({
                "url": self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url'),
                "parameters": {"db":cr.dbname, "channel":record.id},
            })
        return res

    def _web_page(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url') + \
                "/im_livechat/web_page?p=" + json.dumps({"db":cr.dbname, "channel":record.id})
        return res

    _columns = {
        'name': fields.char(string="Channel Name", size=200, required=True),
        'user_ids': fields.many2many('res.users', 'im_livechat_channel_im_user', 'channel_id', 'user_id', string="Users"),
        'are_you_inside': fields.function(_are_you_inside, type='boolean', string='Are you inside the matrix?', store=False),
        'script': fields.function(_script, type='text', string='Script', store=False),
        'web_page': fields.function(_web_page, type='url', string='Web Page', store=False, size="200"),
        'button_text': fields.char(string="Text of the Button", size=200),
        'input_placeholder': fields.char(string="Chat Input Placeholder", size=200),
        'default_message': fields.char(string="Welcome Message", size=200, help="This is an automated 'welcome' message that your visitor will see when they initiate a new chat session."),
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
        channel = self.browse(cr, openerp.SUPERUSER_ID, channel_id, context=context)
        im_user_ids = self.pool.get("im.user").search(cr, uid, [["user_id", "in", [user.id for user in channel.user_ids]]], context=context)
        users = []
        for iuid in im_user_ids:
            imuser = self.pool.get("im.user").browse(cr, uid, iuid, context=context)
            if imuser.im_status:
                users.append(imuser)
        return users

    def get_session(self, cr, uid, channel_id, uuid, context=None):
        self.pool.get("im.user").get_my_id(cr, uid, uuid, context=context)
        users = self.get_available_users(cr, openerp.SUPERUSER_ID, channel_id, context=context)
        if len(users) == 0:
            return False
        user_id = random.choice(users).id
        session = self.pool.get("im.session").session_get(cr, uid, [user_id], uuid, context=context)
        self.pool.get("im.session").write(cr, openerp.SUPERUSER_ID, session.get("id"), {'channel_id': channel_id}, context=context)
        return session.get("id")

    def test_channel(self, cr, uid, channel, context=None):
        if not channel:
            return {}
        return {
            'url': self.browse(cr, uid, channel[0], context=context or {}).web_page,
            'type': 'ir.actions.act_url'
        }

    def get_info_for_chat_src(self, cr, uid, channel, context=None):
        url = self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url')
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

class im_session(osv.osv):
    _inherit = 'im.session'

    _columns = {
        'channel_id': fields.many2one("im_livechat.channel", "Channel"),
    }
