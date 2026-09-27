# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models


class WebsiteEventMenu(models.Model):
    _name = 'website.event.menu'
    _inherit = 'website.seo.metadata'
    _description = "Website Event Menu"
    _rec_name = "menu_id"

    menu_id = fields.Many2one('website.menu', string='Menu', ondelete='cascade')
    event_id = fields.Many2one('event.event', string='Event', index='btree_not_null', ondelete='cascade')
    view_id = fields.Many2one('ir.ui.view', string='View', ondelete='cascade', help='Used when not being an url based menu')
    menu_type = fields.Selection(
        [('community', 'Community Menu'),
         ('introduction', 'Home'),
         ('register', 'Practical'),
         ('other', 'Other'),
        ], string="Menu Type", required=True)

    def copy(self, default=None):
        new_menus = super().copy(default=default)
        for new_menu, old_menu in zip(new_menus, self):
            if not old_menu.view_id:
                continue
            # Get the last view modified based on the key and the website of the event
            # as multiple views with the same key can exist with different website.
            view = self.env['ir.ui.view'].sudo().search([
                ('key', '=', old_menu.view_id.key),
                ('website_id', '=?', old_menu.event_id.website_id.id)
            ], order='write_date DESC', limit=1)
            # The "-t{timestamp}" at the end of the key is needed when _is_active() is called on the menu.
            # Without it, the unslug url can think of the copied view key as a record and keep only the number
            # which can lead to issue where we get multiple menus active at the same time. Also that way, we ensure
            # that the key is unique.
            new_menu.view_id = view.copy({
                'key': f"{old_menu.view_id.key}-t{int(datetime.now().timestamp())}",
                'website_id': view.website_id.id,
            })
            self._copy_children_views(new_menu.view_id, view.inherit_children_ids, old_menu.event_id.website_id.id)
            new_url = f"/event/{self.env['ir.http']._slug(new_menu.event_id)}/page/{new_menu.view_id.key.split('.')[-1]}"
            new_menu_defaults = {
                'url': new_url
            }

            if old_menu.menu_id.page_id:
                new_page = old_menu.menu_id.page_id.copy({
                    'url': new_url
                })
                new_menu_defaults['page_id'] = new_page.id

            new_menu.menu_id = old_menu.menu_id.copy(new_menu_defaults)
        return new_menus

    @api.model
    def _copy_children_views(self, new_view, children_views, website_id):
        """ Duplicate the children associated in the new view """
        new_view.ensure_one()
        for child_view in children_views:
            view_info = child_view.key.split('.')
            # Get the last view modified based on the key and the website of the event
            view = self.env['ir.ui.view'].sudo().search([
                ('key', '=', child_view.key),
                ('website_id', '=?', website_id)
            ], order='write_date DESC', limit=1)
            new_child_view = view.copy({
                'key': self.env['website'].get_unique_key(view_info[-1], view_info[0]),
                'inherit_id': new_view.id,
                'website_id': view.website_id.id,
            })
            self._copy_children_views(new_child_view, view.inherit_children_ids, website_id)

    def unlink(self):
        self.view_id.sudo().unlink()
        return super().unlink()
