# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Event(models.Model):
    _name = 'event.event'
    _inherit = 'event.event'

    def _get_menu_entries(self):
        """ Force tracking on Introduction and Location template-pages """
        res = super(Event, self)._get_menu_entries()
        return [
            (item[0], item[1], item[2], True)
            for item in res
        ]
