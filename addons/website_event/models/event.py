# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

# from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.models import NewId

# from openerp.tools.translate import _
import re

from openerp.addons.website.models.website import slug


class event(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'website.seo.metadata']
    _track = {
        'website_published': {
            'website_event.mt_event_published': lambda self, cr, uid, obj, ctx=None: obj.website_published,
            'website_event.mt_event_unpublished': lambda self, cr, uid, obj, ctx=None: not obj.website_published
        },
    }

    twitter_hashtag = fields.Char('Twitter Hashtag', default=lambda self: self._default_hashtag())
    website_published = fields.Boolean('Visible in Website', copy=False)
    # TDE TODO FIXME: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [
            '&', ('model', '=', self._name), ('type', '=', 'comment')
        ],
        string='Website Messages',
        help="Website communication history",
    )
    website_url = fields.Char('Website url', compute='_website_url')

    @api.one
    @api.depends('name')
    def _website_url(self):
        if isinstance(self.id, NewId):
            self.website_url = ''
        else:
            self.website_url = "/event/" + slug(self)

    def _default_hashtag(self):
        return re.sub("[- \\.\\(\\)\\@\\#\\&]+", "", self.env.user.company_id.name).lower()

    show_menu = fields.Boolean('Has Dedicated Menu', compute='_get_show_menu', inverse='_set_show_menu')
    menu_id = fields.Many2one('website.menu', 'Event Menu')

    @api.one
    def _get_new_menu_pages(self):
        todo = [
            (_('Introduction'), 'website_event.template_intro'),
            (_('Location'), 'website_event.template_location')
        ]
        result = []
        for name, path in todo:
            complete_name = name + ' ' + self.name
            newpath = self.env['website'].new_page(complete_name, path, ispage=False)
            url = "/event/" + slug(self) + "/page/" + newpath
            result.append((name, url))
        result.append((_('Register'), '/event/%s/register' % slug(self)))
        return result

    @api.one
    def _set_show_menu(self):
        if self.menu_id and not self.show_menu:
            self.menu_id.unlink()
        elif self.show_menu and not self.menu_id:
            root_menu = self.env['website.menu'].create({'name': self.name})
            to_create_menus = self._get_new_menu_pages()[0]  # TDE CHECK api.one -> returns a list with one item ?
            seq = 0
            for name, url in to_create_menus:
                self.env['website.menu'].create({
                    'name': name,
                    'url': url,
                    'parent_id': root_menu.id,
                    'sequence': seq,
                })
                seq += 1
            self.menu_id = root_menu

    @api.one
    def _get_show_menu(self):
        self.show_menu = bool(self.menu_id)

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
