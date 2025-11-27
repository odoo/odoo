import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { Domain } from "@web/core/domain";
import { fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    department_id = fields.Many2one({ relation: "hr.department" });
    name = fields.Char();
    user_id = fields.Many2one({ relation: "res.users" });
    work_email = fields.Char();
    work_phone = fields.Char();
    work_location_type = fields.Char();
    work_location_id = fields.Many2one({ relation: "hr.work.location" });
    job_title = fields.Char();
    company_id = fields.Many2one({ relation: "res.company" });

    _get_store_avatar_card_fields({ add_user = true, ...args } = {}) {
        const res = [
            "company_id",
            mailDataHelpers.Store.one("department_id", ["name"]),
            "hr_icon_display",
            "job_title",
            "name",
            "show_hr_icon_display",
            "work_email",
            mailDataHelpers.Store.one("work_location_id", ["location_type", "name"]),
            "work_phone",
        ];
        if (add_user) {
            res.push(
                mailDataHelpers.Store.one(
                    "user_id",
                    this.env["res.users"]._get_store_avatar_card_fields({
                        ...args,
                        add_employee: false,
                    })
                )
            );
        }
        return res;
    }

    _get_working_periods_by_field(employeeIds, start_time, end_time, field_key) {
        const employeeToFieldId = Object.fromEntries(
            this.env["hr.employee"]
                .browse(employeeIds)
                .map((employee) => [employee.id, employee[field_key]])
        );
        const periodsByFieldId = Object.fromEntries(
            Object.values(employeeToFieldId).map((fieldId) => [fieldId, []])
        );
        const fieldPath = `employee_id.${field_key}`;
        if (employeeIds.size) {
            const contractGroups = this.env["hr.version"].formatted_read_group(
                new Domain([["employee_id", "in", [...employeeIds]]]).toList(),
                ["employee_id", fieldPath, "contract_date_start:day", "contract_date_end:day"],
                [],
                "",
                "",
                ""
            );
            contractGroups.forEach((group) => {
                const fieldId = group[fieldPath][0];
                periodsByFieldId[fieldId].push({
                    start: group["contract_date_start:day"][1],
                    end: group["contract_date_end:day"][1],
                });
            });

            const employeesWithContracts = new Set(contractGroups.map((g) => g.employee_id[0]));

            employeeIds.difference(employeesWithContracts).forEach((employeeId) => {
                periodsByFieldId[employeeToFieldId[employeeId]].push({
                    start: start_time,
                    end: end_time,
                });
            });
        }
        return periodsByFieldId;
    }

    _views = {
        search: `<search><field name="display_name" string="Name" /></search>`,
        list: `<list><field name="display_name"/></list>`,
    };
}
