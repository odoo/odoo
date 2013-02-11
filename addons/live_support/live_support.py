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

import openerp
import openerp.addons.web_im.im as im
import json
import random
import jinja2
from osv import osv, fields

env = jinja2.Environment(
    loader=jinja2.PackageLoader('openerp.addons.live_support', "."),
    autoescape=False
)
env.filters["json"] = json.dumps

class ImportController(openerp.addons.web.http.Controller):
    _cp_path = '/live_support'

    @openerp.addons.web.http.httprequest
    def loader(self, req, **kwargs):
        p = json.loads(kwargs["p"])
        db = p["db"]
        channel = p["channel"]
        req.session._db = db
        req.session._uid = None
        req.session._login = "anonymous"
        req.session._password = "anonymous"
        info = req.session.model('live_support.channel').get_info_for_chat_src(channel)
        info["db"] = db
        info["channel"] = channel
        return req.make_response(env.get_template("loader.js").render(info),
             headers=[('Content-Type', "text/javascript")])

    @openerp.addons.web.http.httprequest
    def web_page(self, req, **kwargs):
        p = json.loads(kwargs["p"])
        db = p["db"]
        channel = p["channel"]
        req.session._db = db
        req.session._uid = None
        req.session._login = "anonymous"
        req.session._password = "anonymous"
        script = req.session.model('live_support.channel').read(channel, ["script"])["script"]
        return req.make_response(env.get_template("web_page.html").render({"script": script}),
             headers=[('Content-Type', "text/html")])

    @openerp.addons.web.http.jsonrequest
    def available(self, req, db, channel):
        req.session._db = db
        req.session._uid = None
        req.session._login = "anonymous"
        req.session._password = "anonymous"
        return req.session.model('live_support.channel').get_available_user(channel) > 0

class live_support_channel(osv.osv):
    _name = 'live_support.channel'

    def _are_you_inside(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = False
            for user in record.user_ids:
                if user.user.id == uid:
                    res[record.id] = True
                    break
        return res

    def _script(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = env.get_template("include.html").render({
                "url": self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url'),
                "parameters": {"db":cr.dbname, "channel":record.id},
            })
        return res

    def _web_page(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url') + \
                "/live_support/web_page?p=" + json.dumps({"db":cr.dbname, "channel":record.id})
        return res

    _columns = {
        'name': fields.char(string="Name", size=200, required=True),
        'user_ids': fields.many2many('im.user', 'live_support_channel_im_user', 'channel_id', 'user_id', string="Users"),
        'are_you_inside': fields.function(_are_you_inside, type='boolean', string='Are you inside the matrix?', store=False),
        'script': fields.function(_script, type='text', string='Script', store=False),
        'web_page': fields.function(_web_page, type='url', string='Web Page', store=False, size="200"),
        'button_text': fields.char(string="Button Text", size=200),
        'input_placeholder': fields.char(string="Input Placeholder", size=200),
        'default_message': fields.char(string="Default Message", size=200),
    }

    _defaults = {
        'button_text': "Chat with one of our collaborators",
        'input_placeholder': "How may I help you?",
        'default_message': '',
    }

    def get_available_user(self, cr, uid, channel_id, context=None):
        channel = self.browse(cr, uid, channel_id, context=context)
        users = []
        for user in channel.user_ids:
            if user.im_status:
                users.append(user)
        if len(users) == 0:
            return False
        return random.choice(users).id

    def get_info_for_chat_src(self, cr, uid, channel, context=None):
        url = self.pool.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url')
        chan = self.browse(cr, uid, channel, context=context)
        return {
            "url": url,
            'buttonText': chan.button_text,
            'inputPlaceholder': chan.input_placeholder,
            'defaultMessage': chan.default_message,
        }

    def join(self, cr, uid, ids, context=None):
        my_id = self.pool.get("im.user").get_by_user_id(cr, uid, uid, context)["id"]
        self.write(cr, uid, ids, {'user_ids': [(4, my_id)]})
        return True

    def quit(self, cr, uid, ids, context=None):
        my_id = self.pool.get("im.user").get_by_user_id(cr, uid, uid, context)["id"]
        self.write(cr, uid, ids, {'user_ids': [(3, my_id)]})
        return True


class im_user(osv.osv):
    _inherit = 'im.user'
    _columns = {
        'support_channel_ids': fields.many2many('live_support.channel', 'live_support_channel_im_user', 'user_id', 'channel_id', string="Support Channels"),
    }
