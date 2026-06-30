# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DepartureReason(models.Model):
    _name = "hr.departure.reason"
    _description = "Departure Reason"
    _order = "sequence"

    sequence = fields.Integer("Sequence", default=10)
    name = fields.Char(string="Reason", required=True, translate=True)
    reason_code = fields.Integer()

    def _get_default_departure_reasons(self):
        return {
            'fired': 342,
            'resigned': 343,
            'retired': 340,
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_departure_reasons(self):
        master_departure_codes = self._get_default_departure_reasons().values()
        if any(reason.reason_code in master_departure_codes for reason in self):
            raise UserError(_('Default departure reasons cannot be deleted.'))
