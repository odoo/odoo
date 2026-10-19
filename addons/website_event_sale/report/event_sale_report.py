# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class EventSaleReport(models.Model):
    _inherit = 'event.sale.report'

    is_published = fields.Boolean('Published Events', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['is_published'] = SQL('event_event.is_published')
        return res
