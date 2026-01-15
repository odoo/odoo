# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrDepartureReason(models.Model):
    _name = 'hr.departure.reason'
    _description = "Departure Reason"
    _order = "sequence"

    sequence = fields.Integer("Sequence", default=10)
    name = fields.Char(string="Reason", required=True, translate=True)
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
    country_code = fields.Char(related='country_id.code')

    @api.model
    def _get_default_departure_reasons(self):
        return {self.env.ref(reason_ref) for reason_ref in (
            'hr.departure_fired',
            'hr.departure_resigned',
            'hr.departure_retired',
        )}

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_departure_reasons(self):
        master_departure_codes = self._get_default_departure_reasons()
        if any(reason in master_departure_codes for reason in self):
            raise UserError(_('Default departure reasons cannot be deleted.'))
