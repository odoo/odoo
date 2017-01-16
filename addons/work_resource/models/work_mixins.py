# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResourceResourceMixin(models.Model):
    _name = "resource.resource.mixin"
    _description = 'Resource Mixin'

    def get_work_days_count(self, from_datetime, to_datetime):
        return len([dt for dt in self._iter_work_days(from_datetime, to_datetime)])
