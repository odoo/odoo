import { fields, models, defineModels } from "@web/../tests/web_test_helpers";
import { Domain } from "@web/core/domain";
import { hrModels } from "@hr/../tests/hr_test_helpers";

export class HrContract extends models.Model {
    _name = "hr.contract";

    name = fields.Char();
    state = fields.Selection({
        selection: [
            ["draft", "New"],
            ["open", "Running"],
            ["close", "Expired"],
            ["cancel", "Cancelled"],
        ],
    });
    kanban_state = fields.Selection({
        selection: [
            ["normal", "Grey"],
            ["done", "Green"],
            ["blocked", "Red"],
        ],
    });
    employee_id = fields.Many2one({ relation: "hr.employee" });
    date_start = fields.Date();
    date_end = fields.Date();

    _records = [
        {
            id: 1,
            name: "Contract - Pig",
            employee_id: 1,
            kanban_state: false,
            state: false,
        },
    ];

    get_employee_working_periods(employees, start, stop) {
        const rows = {};

        for (const val of employees) {
            rows[val] = { working_periods: [] };
        }
        const employees_with_contract = this.env["hr.contract"].read_group(
            new Domain([
                "&",
                ["employee_id", "in", employees],
                "|",
                ["state", "not in", ["draft", "cancel", false]],
                "&",
                ["kanban_state", "=", "done"],
                ["state", "=", "draft"],
            ]).toList(),
            "",
            ["id", "employee_id"],
            "",
            "",
            "",
            false
        );

        const contracts = this.env["hr.employee"]._get_contracts(
            employees,
            start,
            stop,
            ["draft", "open", "close"]
        );

        const employees_with_contract_in_current_scale = new Set();

        for (const contract of contracts) {
            if (contract.state == "draft" && contract.kanban_state != "done") {
                continue;
            }

            const employee = contract.employee_id;
            employees_with_contract_in_current_scale.add(employee);
            rows[employee]["working_periods"].push({
                start: contract.date_start,
                end: contract.date_end,
            });
        }

        for (const employee of new Set(employees).difference(
            employees_with_contract_in_current_scale
        )) {
            if (employees_with_contract.some((contract) => contract.employee_id[0] == employee)) {
                continue;
            }
            rows[employee]["working_periods"].push({
                start: start,
                end: stop,
            });
        }
        return rows;
    }
}

export class HrEmployeeContract extends hrModels.HrEmployee {

    _records = [
        {
            name: "Pig-2",
            id: 1,
            user_id: 1,
        },
    ];

    _get_contracts(ids, date_from, date_to, states = ["open"], kanban_state = false) {
        let state_domain = new Domain([["state", "in", states]]);

        if (kanban_state) {
            state_domain = Domain.and([
                state_domain,
                new Domain([["kanban_state", "in", kanban_state]]),
            ]);
        }

        return this.env["hr.contract"]._filter(
            Domain.and([
                new Domain([["employee_id", "in", ids]]),
                state_domain,
                new Domain([
                    ["date_start", "<=", date_to],
                    "|",
                    ["date_end", "=", false],
                    ["date_end", ">=", date_from],
                ]),
            ]).toList()
        );
    }
}

hrModels.HrEmployee = HrEmployeeContract;

export const hrContractModels = {
    ...hrModels,
    HrContract,
}

export function defineHrContractModels() {
    defineModels(hrContractModels);
}
