# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.addons.website.models.website import slug


class Event(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'website.seo.metadata', 'website.published.mixin']

    def _default_hashtag(self):
        return re.sub("[- \\.\\(\\)\\@\\#\\&]+", "", self.env.user.company_id.name).lower()

    twitter_hashtag = fields.Char('Twitter Hashtag', default=_default_hashtag)
    website_published = fields.Boolean(track_visibility='onchange')
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [
            '&', ('model', '=', self._name), ('message_type', '=', 'comment')
        ],
        string='Website Messages',
        help="Website communication history",
    )
    is_participating = fields.Boolean("Is Participating", compute="_compute_is_participating")

    show_menu = fields.Boolean('Dedicated Menu', compute='_get_show_menu', inverse='_set_show_menu',
                               help="Creates menus Introduction, Location and Register on the page "
                                    " of the event on the website.", store=True)
    menu_id = fields.Many2one('website.menu', 'Event Menu')

    def _compute_is_participating(self):
        # we don't allow public user to see participating label
        if self.env.user != self.env.ref('base.public_user'):
            email = self.env.user.partner_id.email
            for event in self:
                domain = ['&', '|', ('email', '=', email), ('partner_id', '=', self.env.user.partner_id.id), ('event_id', '=', event.id)]
                event.is_participating = self.env['event.registration'].search_count(domain)

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Event, self)._compute_website_url()
        for event in self:
            if event.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                event.website_url = '/event/%s' % slug(event)

    @api.multi
    def _get_new_menu_pages(self):
        """ Retuns a list of tuple ('Page name', 'relative page url') for the event """
        self.ensure_one()
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

    @api.multi
    def _set_show_menu(self):
        for event in self:
            if event.menu_id and not event.show_menu:
                event.menu_id.unlink()
            elif event.show_menu and not event.menu_id:
                root_menu = self.env['website.menu'].create({'name': event.name})
                to_create_menus = event._get_new_menu_pages()
                seq = 0
                for name, url in to_create_menus:
                    self.env['website.menu'].create({
                        'name': name,
                        'url': url,
                        'parent_id': root_menu.id,
                        'sequence': seq,
                    })
                    seq += 1
                event.menu_id = root_menu

    @api.multi
    def _get_show_menu(self):
        for event in self:
            event.show_menu = bool(event.menu_id)

    @api.multi
    def google_map_img(self, zoom=8, width=298, height=298):
        self.ensure_one()
        if self.address_id:
            return self.sudo().address_id.google_map_img(zoom=zoom, width=width, height=height)
        return None

    @api.multi
    def google_map_link(self, zoom=8):
        self.ensure_one()
        if self.address_id:
            return self.sudo().address_id.google_map_link(zoom=zoom)
        return None

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'website_published' in init_values and self.website_published:
            return 'website_event.mt_event_published'
        elif 'website_published' in init_values and not self.website_published:
            return 'website_event.mt_event_unpublished'
        return super(Event, self)._track_subtype(init_values)

    @api.multi
    def action_open_badge_editor(self):
        """ open the event badge editor : redirect to the report page of event badge report """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/report/html/%s/%s?enable_editor' % ('event.event_event_report_template_badge', self.id),
        }
