import { onRpc } from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";

onRpc(
    "gantt_resource_employees_working_periods",
    function ganttResourceEmployeesWorkingPeriods({ args, model, kwargs }) {
        const start_time = kwargs.context.default_start_datetime;
        const end_time = kwargs.context.default_end_datetime;
        const rows = [];
        for (const row of args[0]) {
            if ("rows" in row) {
                row["rows"] = ganttResourceEmployeesWorkingPeriods({ model, row, kwargs });
                continue;
            }
            const [resource_id] = JSON.parse(row.id)[0].resource_id || [false];
            if (!resource_id) {
                continue;
            }
            const [resource] = this.env["resource.resource"].browse([resource_id]);
            if (!resource.employee_id) {
                continue;
            }
            row.working_periods = new Array();
            rows[resource.employee_id] = row;
        }
        if (rows) {
            const employee_ids = Object.keys(rows).map((a) => parseInt(a, 10));
            const hr_contract_read_group = this.env["hr.contract"].read_group(
                new Domain([
                    "&",
                    ["employee_id", "in", employee_ids],
                    "|",
                    ["state", "not in", ["draft", "cancel"]],
                    "&",
                    ["kanban_state", "=", "done"],
                    ["state", "=", "draft"],
                ]).toList(),
                "",
                ["id", "employee_id", "date_start:day", "date_end:day"],
                "",
                "",
                "",
                false
            );
            hr_contract_read_group.forEach((contract) => {
                rows[contract.employee_id[0]]["working_periods"].push({
                    start: contract["date_start:day"],
                    end: contract["date_end:day"],
                });
            });
            new Set(employee_ids)
                .difference(new Set(hr_contract_read_group.map((a) => a.employee_id[0])))
                .forEach((employee) => {
                    rows[employee]["working_periods"].push({
                        start: start_time,
                        end: end_time,
                    });
                });
        }
        return rows;
    }
);
