# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import format_date


class ReceptionReport(models.AbstractModel):
    _inherit = 'report.stock.report_reception'

    def _get_formatted_scheduled_date(self, source):
        if source._name == 'mrp.production':
            return format_date(self.env, source.date_planned_start)
        return super()._get_formatted_scheduled_date(source)
