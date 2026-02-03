import { models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    _records = [
        { id: 1, display_name: "Mario" },
        { id: 2, display_name: "Luigi" },
        { id: 3, display_name: "Yoshi" },
        { id: 100, name: "Richard" },
        { id: 200, name: "Alice" },
    ];

    async generate_work_entries(employeeIds, startDate, endDate) {}
}
