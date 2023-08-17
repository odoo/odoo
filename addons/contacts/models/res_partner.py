# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner']

    @api.model
    def _sort_activities_by_record(self, activities, module=False):
        """ Override from mail to associate the activities linked to res.partner
            records to the module contacts instead of base.
        """
        return super()._sort_activities_by_record(activities, module or 'contacts')
