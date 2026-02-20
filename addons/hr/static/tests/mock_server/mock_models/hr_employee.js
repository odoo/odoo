import { Domain } from "@web/core/domain";
import { fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    department_id = fields.Many2one({ relation: "hr.department" });
    work_email = fields.Char();
    work_phone = fields.Char();
    work_location_type = fields.Char();
    work_location_id = fields.Many2one({ relation: "hr.work.location" });
    job_title = fields.Char();

    _get_store_avatar_card_fields() {
        return this.env["hr.employee.public"]._get_store_avatar_card_fields();
    }

    _get_employee_working_periods(employeeIds, start_time, end_time) {
        const working_periods = Object.fromEntries([...employeeIds].map((id) => [id, []]));
        if (employeeIds.size) {
            const hr_contract_read_group = this.env["hr.version"].formatted_read_group(
                new Domain([["employee_id", "in", [...employeeIds]]]).toList(),
                ["employee_id", "contract_date_start:day", "contract_date_end:day"],
                [],
                "",
                "",
                ""
            );
            hr_contract_read_group.forEach((contract) => {
                const employee_id = contract.employee_id[0];
                working_periods[employee_id].push({
                    start: contract["contract_date_start:day"][1],
                    end: contract["contract_date_end:day"][1],
                });
            });
            employeeIds
                .difference(new Set(hr_contract_read_group.map((a) => a.employee_id[0])))
                .forEach((employee_id) => {
                    working_periods[employee_id].push({
                        start: start_time,
                        end: end_time,
                    });
                });
        }

        return working_periods;
    }

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
