import { SpreadsheetModels, defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { fields, models } from "@web/../tests/web_test_helpers";
import { RPCError } from "@web/core/network/rpc";

export function getDashboardServerData() {
    return {
        models: {
            "spreadsheet.dashboard": {},
            "spreadsheet.dashboard.group": {},
        },
        views: {},
    };
}

export class SpreadsheetDashboard extends models.Model {
    _name = "spreadsheet.dashboard";

    name = fields.Char({ string: "Name" });
    spreadsheet_data = fields.Char({});
    json_data = fields.Char({});
    is_published = fields.Boolean({ string: "Is published" });
    dashboard_group_id = fields.Many2one({ relation: "spreadsheet.dashboard.group" });

    get_readonly_dashboard(id) {
        const dashboard = this.env["spreadsheet.dashboard"].search_read([["id", "=", id]])[0];
        if (!dashboard) {
            const error = new RPCError();
            error.data = {};
            throw error;
        }
        return {
            snapshot: JSON.parse(dashboard.spreadsheet_data),
            revisions: [],
        };
    }

    _records = [
        {
            id: 1,
            spreadsheet_data: "{}",
            json_data: "{}",
            name: "Dashboard CRM 1",
            dashboard_group_id: 1,
        },
        {
            id: 2,
            spreadsheet_data: "{}",
            json_data: "{}",
            name: "Dashboard CRM 2",
            dashboard_group_id: 1,
        },
        {
            id: 3,
            spreadsheet_data: "{}",
            json_data: "{}",
            name: "Dashboard Accounting 1",
            dashboard_group_id: 2,
        },
    ];
}

export class SpreadsheetDashboardGroup extends models.Model {
    _name = "spreadsheet.dashboard.group";

    name = fields.Char({ string: "Name" });
    published_dashboard_ids = fields.One2many({
        relation: "spreadsheet.dashboard",
        relation_field: "dashboard_group_id",
    });

    _records = [
        { id: 1, name: "Container 1", published_dashboard_ids: [1, 2] },
        { id: 2, name: "Container 2", published_dashboard_ids: [3] },
    ];
}

export function defineSpreadsheetDashboardModels() {
    const SpreadsheetDashboardModels = [SpreadsheetDashboard, SpreadsheetDashboardGroup];
    Object.assign(SpreadsheetModels, SpreadsheetDashboardModels);
    defineSpreadsheetModels();
}
