import hashlib

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = ["hr.employee", "mixin.pos.load"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        return config._employee_domain(config.current_user_id.id)

    @api.model
    def _load_pos_data_fields(self, config):
        return ["name", "user_id", "partner_id"]

    def _add_server_date_to_domain(self, domain):
        return domain

    @api.model
    def _load_pos_data_read(self, records, config):
        # NOTE:
        fields = self._load_pos_data_fields(config)
        read_records = records.read(fields, load=False)
        manager_ids = records.filtered(
            lambda emp: config.group_pos_manager_id.id in emp.user_id.all_group_ids.ids
        ).ids

        employees_barcode_pin = records.get_barcodes_and_pin_hashed()
        bp_per_employee_id = {bp_e["id"]: bp_e for bp_e in employees_barcode_pin}

        _debug.perf.count(
            "pos_employees_loaded",
            config=config,
            employees=len(read_records),
            managers=len(manager_ids),
            with_credentials=len(bp_per_employee_id),
        )
        for employee in read_records:
            if employee["id"] in manager_ids:
                role = "manager"
                employee["_user_role"] = "admin"
            elif employee["id"] in config.advanced_employee_ids.ids:
                role = "manager"
            elif employee["id"] in config.minimal_employee_ids.ids:
                role = "minimal"
            else:
                role = "cashier"
            _debug.logic(
                "pos_employee_role",
                config=config,
                employee_id=employee["id"],
                role=role,
                by="pos_manager_group"
                if employee["id"] in manager_ids
                else "advanced_list"
                if employee["id"] in config.advanced_employee_ids.ids
                else "minimal_list"
                if employee["id"] in config.minimal_employee_ids.ids
                else "default",
            )

            employee_barcode_pin = bp_per_employee_id.get(employee["id"], {})
            employee["_role"] = role
            employee["_barcode"] = employee_barcode_pin.get("barcode", False)
            employee["_pin"] = employee_barcode_pin.get("pin", False)

        return read_records

    def _is_pos_manager(self) -> bool:
        self.check_singleton()
        # an employee with no user has no group
        return bool(self.user_id) and self.user_id._has_group(
            "point_of_sale.group_pos_manager"
        )

    def get_barcodes_and_pin_hashed(self):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            _debug.logic(
                "pos_credentials_denied",
                reason="not_a_pos_user",
                user=self.env.user,
                employees=self,
            )
            return []
        # Apply visibility filters (record rules)
        visible_emp_ids = self.search([("id", "in", self.ids)])
        employees_data = self.sudo().search_read(
            [("id", "in", visible_emp_ids.ids)], ["barcode", "pin"]
        )

        _debug.logic(
            "pos_credentials_read",
            user=self.env.user,
            requested=self,
            visible=visible_emp_ids,
        )
        for e in employees_data:
            e["barcode"] = (
                hashlib.sha1(e["barcode"].encode("utf8")).hexdigest()
                if e["barcode"]
                else False
            )
            e["pin"] = (
                hashlib.sha1(e["pin"].encode("utf8")).hexdigest() if e["pin"] else False
            )
        return employees_data

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_pos_session(self):
        configs_with_employees = (
            self.env["pos.config"]
            .sudo()
            .search([("module_pos_hr", "=", True)])
            .filtered(lambda c: c.current_session_id)
        )
        configs_with_all_employees = configs_with_employees.filtered(
            lambda c: (
                not c.basic_employee_ids
                and not c.advanced_employee_ids
                and not c.minimal_employee_ids
            )
        )
        configs_with_specific_employees = configs_with_employees.filtered(
            lambda c: (
                (
                    c.basic_employee_ids
                    or c.advanced_employee_ids
                    or c.minimal_employee_ids
                )
                & self
            )
        )
        _debug.logic(
            "pos_employee_unlink_checked",
            employees=self,
            open_configs=configs_with_employees,
            configs_open_to_all=configs_with_all_employees,
            configs_naming_these=configs_with_specific_employees,
        )
        if configs_with_all_employees or configs_with_specific_employees:
            error_msg = _(
                "You cannot delete an employee that may be used in an active PoS session, close the session(s) first: \n"
            )
            for employee in self:
                config_ids = (
                    configs_with_all_employees
                    | configs_with_specific_employees.filtered(
                        lambda c, employee=employee: (
                            employee in c.basic_employee_ids
                            or employee in c.advanced_employee_ids
                            or employee in c.minimal_employee_ids
                        )
                    )
                )
                if config_ids:
                    error_msg += _(
                        "Employee: %(employee)s - PoS Config(s): %(config_list)s \n",
                        employee=employee.name,
                        config_list=config_ids.mapped("name"),
                    )

            raise UserError(error_msg)
