import { fields, models } from "@web/../tests/web_test_helpers";

export class HelpdeskSlaStatus extends models.Model {
    _name = "helpdesk.sla.status";

    color = fields.Integer({ string: "Color index" });
    name = fields.Char({ string: "Name" });
    status = fields.Selection({
        string: "SLA's",
        selection: [
            ["failed", "Failed"],
            ["reached", "Reached"],
            ["dummy", "Dummy"],
        ],
    });
    ticket_id = fields.Many2one({ relation: "helpdesk.ticket" });

    _records = [
        {
            color: 1,
            name: "SLA Status 1",
            status: "failed",
            ticket_id: 1,
        },
        {
            color: 2,
            name: "SLA Status 2",
            status: "reached",
            ticket_id: 1,
        },
        {
            color: 4,
            name: "SLA Status 2",
            status: "reached",
            ticket_id: 2,
        },
    ];
}
