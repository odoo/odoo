# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

from openerp.tools.translate import _
import re

from openerp.addons.website.models.website import slug


class event(osv.osv):
    _name = 'event.event'
    _inherit = ['event.event','website.seo.metadata']
    _track = {
        'website_published': {
            'website_event.mt_event_published': lambda self, cr, uid, obj, ctx=None: obj.website_published,
            'website_event.mt_event_unpublished': lambda self, cr, uid, obj, ctx=None: not obj.website_published
        },
    }

    def _get_new_menu_pages(self, cr, uid, event, context=None):
        context = context or {}
        todo = [
            (_('Introduction'), 'website_event.template_intro'),
            (_('Location'), 'website_event.template_location')
        ]
        web = self.pool.get('website')
        result = []
        for name,path in todo:
            name2 = name+' '+event.name
            newpath = web.new_page(cr, uid, name2, path, ispage=False, context=context)
            url = "/event/"+slug(event)+"/page/" + newpath
            result.append((name, url))
        return result

    def _set_show_menu(self, cr, uid, ids, name, value, arg, context=None):
        menuobj = self.pool.get('website.menu')
        eventobj = self.pool.get('event.event')
        for event in self.browse(cr, uid, [ids], context=context):
            if event.menu_id and not value:
                menuobj.unlink(cr, uid, [event.menu_id.id], context=context)
            elif value and not event.menu_id:
                root = menuobj.create(cr, uid, {
                    'name': event.name
                }, context=context)
                tocreate = self._get_new_menu_pages(cr, uid, event, context)
                tocreate.append((_('Register'), '/event/%s/register' % slug(event)))
                sequence = 0
                for name,url in tocreate:
                    menuobj.create(cr, uid, {
                        'name': name,
                        'url': url,
                        'parent_id': root,
                        'sequence': sequence
                    }, context=context)
                    sequence += 1
                eventobj.write(cr, uid, [event.id], {'menu_id': root}, context=context)
        return True

    def _get_show_menu(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = bool(event.menu_id)
        return res

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        for event in self.browse(cr, uid, ids, context=context):
            res[event.id] = "/event/" + slug(event)
        return res

    def _default_hashtag(self, cr, uid, context={}):
        name = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.name
        return re.sub("[- \\.\\(\\)\\@\\#\\&]+", "", name).lower()

    _columns = {
        'twitter_hashtag': fields.char('Twitter Hashtag'),
        'website_published': fields.boolean('Visible in Website', copy=False),
        # TDE TODO FIXME: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Website Messages',
            help="Website communication history",
        ),
        'website_url': fields.function(_website_url, string="Website url", type="char"),
        'show_menu': fields.function(_get_show_menu, fnct_inv=_set_show_menu, type='boolean', string='Dedicated Menu',
            help="Creates menus Introduction, Location and Register on the page of the event on the website."),
        'menu_id': fields.many2one('website.menu', 'Event Menu'),
    }
    _defaults = {
        'show_menu': False,
        'twitter_hashtag': _default_hashtag
    }

    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        event = self.browse(cr, uid, ids[0], context=context)
        if event.address_id:
            return self.browse(cr, SUPERUSER_ID, ids[0], context=context).address_id.google_map_img()
        return None

    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        event = self.browse(cr, uid, ids[0], context=context)
        if event.address_id:
            return self.browse(cr, SUPERUSER_ID, ids[0], context=context).address_id.google_map_link()
        return None

