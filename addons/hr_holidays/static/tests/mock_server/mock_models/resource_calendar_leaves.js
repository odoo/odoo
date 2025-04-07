import { fields, models } from "@web/../tests/web_test_helpers";
import { parseRequestParams, registerRoute } from "@mail/../tests/mock_server/mail_mock_server";

export class ResourceCalendarLeaves extends models.Model {
    _name = "resource.calendar.leaves";

    id = fields.Integer();
    name = fields.Char();
    company_id = fields.Many2one({
        relation: "res.company",
    });
    date_from = fields.Datetime();
    date_to = fields.Datetime();
    resource_id = fields.Many2one({
        relation: "resource.resource",
    });
    state = fields.Char();
    description = fields.Char();
    // Add any additional fields specific to resource.calendar.leaves
}

// registerRoute
registerRoute("/holidays/is_public_holiday", get_public_holiday);
async function get_public_holiday(request) {
    const { userId } = await parseRequestParams(request);
    const today = new Date().toISOString().split("T")[0]; // Get today's date in 'YYYY-MM-DD' format
    const ResourceCalendarLeaves = this.env["resource.calendar.leaves"];
    const ResUsers = this.env["res.users"];
    const [user] = ResUsers.search_read([["id", "=", userId]]);
    const [holidays] = ResourceCalendarLeaves.search_read([
        ["resource_id", "=", false],
        ["company_id", "=", user.company_id[0]], // Assuming a single company for simplicity
        ["date_from", "<=", today],
        ["date_to", ">=", today],
    ]);

    // Return the name of the holiday if found, otherwise false
    return holidays ? holidays.name : false;
}
