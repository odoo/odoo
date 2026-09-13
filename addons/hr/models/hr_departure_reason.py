from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class HrDepartureReason(models.Model):
    _name = "hr.departure.reason"
    _description = "Departure Reason"
    _order = "sequence"

    sequence = fields.Integer(default=10)
    name = fields.Char(
        string="Reason",
        translate=True,
        required=True,
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        default=lambda self: self.env.company.country_id,
    )
    country_code = fields.Char(related="country_id.code")

    @api.model
    def _get_default_departure_reasons(self):
        return {
            self.env.ref(reason_ref)
            for reason_ref in (
                "hr.departure_fired",
                "hr.departure_resigned",
                "hr.departure_retired",
            )
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_departure_reasons(self):
        master_departure_codes = self._get_default_departure_reasons()
        dbg.logic.debug(
            "hr.departure.reason.unlink %s: defaults are %s",
            dbg.rec(self),
            sorted(reason.id for reason in master_departure_codes),
        )
        if any(reason in master_departure_codes for reason in self):
            raise UserError(self.env._("Default departure reasons cannot be deleted."))
