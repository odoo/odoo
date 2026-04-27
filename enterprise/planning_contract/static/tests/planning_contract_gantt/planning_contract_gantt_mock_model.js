import { fields, models } from "@web/../tests/web_test_helpers";

export class Contract extends models.Model {
    _name = "hr.contract";

    id = fields.Integer();
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
    date_start = fields.Datetime();
    date_end = fields.Datetime();
    resource_id = fields.Many2one({ relation: "resource.resource" });

    _records = [
        {
            id: 1,
            name: "Contract - Pig",
            state: "draft",
            kanban_state: "normal",
            employee_id: 1,
            date_start: "2024-03-28 00:00:00",
            date_end: "2024-03-28 23:50:59",
            resource_id: 1,
        },
    ];
}
