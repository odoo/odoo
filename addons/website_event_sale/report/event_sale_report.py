# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import event_sale


class EventSaleReport(event_sale.EventSaleReport):

    is_published = fields.Boolean('Published Events', readonly=True)

    def _select_clause(self, *select):
        return super()._select_clause('event_event.is_published as is_published', *select)
