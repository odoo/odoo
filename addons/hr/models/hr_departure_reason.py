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

    def _get_default_departure_reasons(self):
        return {
            'fired': self.env.ref('hr.departure_fired', False),
            'resigned': self.env.ref('hr.departure_resigned', False),
            'retired': self.env.ref('hr.departure_retired', False),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_departure_reasons(self):
        ids = set(map(lambda a: a.id, self._get_default_departure_reasons().values()))
        if set(self.ids) & ids:
            raise UserError(_('Default departure reasons cannot be deleted.'))
