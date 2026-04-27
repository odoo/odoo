import { fields, models } from "@web/../tests/web_test_helpers";

export class HelpdeskTicket extends models.Model {
    _name = "helpdesk.ticket";

    name = fields.Char({ string: "Name" });
    sla_status_ids = fields.One2many({ string: "SLA's", relation: "helpdesk.sla.status" });
    sla_deadline = fields.Date({
        string: "SLA Deadline",
        store: true,
        sortable: true,
        groupable: true,
    });
    team_id = fields.Many2one({ relation: "helpdesk.team" });
    stage_id = fields.Many2one({ relation: "helpdesk.stage" });

    _records = [
        {
            name: "Ticket 1",
            team_id: 1,
            stage_id: 1,
            sla_status_ids: [1, 2, 3],
        },
        {
            name: "Ticket 2",
            team_id: 1,
            stage_id: 2,
            sla_status_ids: [1, 2],
        },
        {
            name: "Ticket 3",
            team_id: 2,
            stage_id: 2,
            sla_status_ids: [1, 2, 3],
        },
    ];
}
