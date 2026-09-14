from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

_CONTROLS = ("hr_presence_control_ip", "hr_presence_control_email")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    @api.model_create_multi
    def create(self, vals_list):
        """Sweep at once when a control is switched on, so the list is not wrong
        until the next hour.

        The snapshot has to be taken before `super()`: a related field that is
        not readonly is written through to the company by `create` itself, so
        anything comparing the setting to the company afterwards -- here or in
        `set_values`, which runs later still -- reads them equal whatever the
        user changed.
        """
        companies = self.env["res.company"].browse(
            {vals.get("company_id") or self.env.company.id for vals in vals_list}
        )
        before = {
            company.id: tuple(company[name] for name in _CONTROLS)
            for company in companies.sudo()
        }
        configs = super().create(vals_list)
        companies.invalidate_recordset(_CONTROLS)
        turned_on = companies.sudo().filtered(
            lambda company: (
                tuple(company[name] for name in _CONTROLS) != before[company.id]
                and any(company[name] for name in _CONTROLS)
            )
        )
        if turned_on:
            _debug.lifecycle("presence_control_changed", companies=turned_on)
            self.env["hr.employee"]._check_presence()
        return configs
