# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, modules


class ResUsers(models.Model, base.ResUsers):

    @api.model
    def _get_activity_groups(self):
        """ Update the systray icon of res.partner activities to use the
        contact application one instead of base icon. """
        activities = super()._get_activity_groups()
        for activity in activities:
            if activity['model'] != 'res.partner':
                continue
            activity['icon'] = modules.module.get_module_icon('contacts')
        return activities
