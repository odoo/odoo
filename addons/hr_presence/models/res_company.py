# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_presence_last_compute_date = fields.Datetime()

    def _get_fields_no_cache_clear(self):
        fields = super()._get_fields_no_cache_clear()
        fields.add('hr_presence_last_compute_date')
        return fields
