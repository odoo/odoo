# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventMenu(models.Model):
    _name = "website.event.menu"
    _description = "Website Event Menu"
    _rec_name = "menu_id"

    menu_id = fields.Many2one('website.menu', string='Menu', ondelete='cascade')
    event_id = fields.Many2one('event.event', string='Event', ondelete='cascade')
    view_id = fields.Many2one('ir.ui.view', string='View', ondelete='cascade', help='Used when not being an url based menu')
    menu_type = fields.Selection(
        [('community', 'Community Menu'),
         ('introduction', 'Introduction'),
         ('location', 'Location'),
         ('register', 'Register'),
        ], string="Menu Type", required=True)

    def unlink(self):
        self.view_id.sudo().unlink()
        return super(EventMenu, self).unlink()
