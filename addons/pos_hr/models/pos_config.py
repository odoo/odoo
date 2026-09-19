from odoo import Command, api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class PosConfig(models.Model):
    _name = "pos.config"
    _inherit = ["mixin.hr", "pos.config"]

    minimal_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="pos_hr_minimal_employee_hr_employee",
        string="Employees with minimal access",
        help="If left empty, all employees can log in to PoS",
    )
    basic_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="pos_hr_basic_employee_hr_employee",
        string="Employees with basic access",
        help="If left empty, all employees can log in to PoS",
    )
    advanced_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        relation="pos_hr_advanced_employee_hr_employee",
        string="Employees with manager access",
        help="Employees linked to users with the PoS Manager role are automatically added to this list",
    )

    def write(self, vals):
        if "advanced_employee_ids" not in vals:
            vals["advanced_employee_ids"] = []
        vals["advanced_employee_ids"] += [
            Command.link(emp_id)
            for emp_id in self._default_group_pos_manager_id().user_ids.employee_id.ids
        ]

        # write employees in sudo, because we have no access to these corecords
        sudo_vals = {
            field_name: vals.pop(field_name)
            for field_name in (
                "minimal_employee_ids",
                "basic_employee_ids",
                "advanced_employee_ids",
            )
            if not self.env.su
            if isinstance(vals.get(field_name), list)
            if all(isinstance(cmd, (list, tuple)) for cmd in vals[field_name])
        }

        _debug.pipeline(
            "pos_config_employee_lists_written",
            configs=self,
            escalated_fields=len(sudo_vals),
            # the key is `pop`ped into `sudo_vals` on the non-superuser path,
            # so it is read from wherever it ended up
            advanced_commands=len(
                vals.get("advanced_employee_ids")
                or sudo_vals.get("advanced_employee_ids")
                or ()
            ),
        )
        res = super().write(vals)
        if sudo_vals:
            super(PosConfig, self.sudo()).write(sudo_vals)
        return res

    @api.onchange("minimal_employee_ids")
    def _onchange_minimal_employee_ids(self):
        for employee in self.minimal_employee_ids:
            if employee._is_pos_manager():
                self.minimal_employee_ids -= employee
            elif employee in self.basic_employee_ids:
                self.basic_employee_ids -= employee
            elif employee in self.advanced_employee_ids:
                self.advanced_employee_ids -= employee

    @api.onchange("basic_employee_ids")
    def _onchange_basic_employee_ids(self):
        for employee in self.basic_employee_ids:
            if employee._is_pos_manager():
                self.basic_employee_ids -= employee
            elif employee in self.advanced_employee_ids:
                self.advanced_employee_ids -= employee
            elif employee in self.minimal_employee_ids:
                self.minimal_employee_ids -= employee

    @api.onchange("advanced_employee_ids")
    def _onchange_advanced_employee_ids(self):
        for employee in self.advanced_employee_ids:
            if employee in self.basic_employee_ids:
                self.basic_employee_ids -= employee
            if employee in self.minimal_employee_ids:
                self.minimal_employee_ids -= employee

    def _employee_domain(self, user_id):
        domain = self._check_company_domain(self.company_id)
        _debug.logic(
            "pos_employee_domain",
            config=self,
            user_id=user_id,
            restricted=len(self.basic_employee_ids) > 0,
            basic=self.basic_employee_ids,
            advanced=self.advanced_employee_ids,
            minimal=self.minimal_employee_ids,
        )
        if len(self.basic_employee_ids) > 0:
            domain = Domain.AND(
                [
                    domain,
                    [
                        "|",
                        ("user_id", "=", user_id),
                        (
                            "id",
                            "in",
                            self.basic_employee_ids.ids
                            + self.advanced_employee_ids.ids
                            + self.minimal_employee_ids.ids,
                        ),
                    ],
                ]
            )
        return domain
