import { models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    _records = [
        { id: 100, name: "Richard" },
        { id: 200, name: "Alice" },
    ];

    async generate_work_entries(employeeIds, startDate, endDate) {}
}
