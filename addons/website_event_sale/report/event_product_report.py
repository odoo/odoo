# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventProductReport(models.Model):
    _inherit = 'event.product.report'

    is_published = fields.Boolean('Published Events', readonly=True)

    def _event_sale_select_clause(self, *select):
        return super()._event_sale_select_clause('event_event.is_published as is_published', *select)
