import {
    defineSpreadsheetModels,
    SpreadsheetModels,
} from "@spreadsheet/../tests/helpers/data";
import { fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { RPCError } from "@web/core/network";

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
    favorite_user_ids = fields.Many2many({
        relation: "res.users",
        string: "Favorite Users",
    });
    is_user_favorite = fields.Boolean({
        compute: "_compute_is_user_favorite",
        string: "Is Favorite",
    });
    // Present on the deployed model whenever spreadsheet_dashboard_edition is
    // installed (which adds it and unconditionally patches the dashboard loader
    // to read it into the groups fetch spec). The unit-test bundle always loads
    // that patch, so the community mock must expose the field or web_read of the
    // groups spec fails ("no field is_from_data"). Overridden by the enterprise
    // mock (test_data.js) with the same definition.
    is_from_data = fields.Boolean({ string: "Is from Data", default: false });

    _compute_is_user_favorite() {
        for (const record of this) {
            record.is_user_favorite = record.favorite_user_ids.includes(this.env.uid);
        }
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

function mockDashboardDataController(_request, { res_id }) {
    const [record] = this.env["spreadsheet.dashboard"].search_read([
        ["id", "=", parseInt(res_id)],
    ]);
    if (!record) {
        const error = new RPCError(`Dashboard ${res_id} does not exist`);
        error.data = {};
        throw error;
    }
    return {
        snapshot: JSON.parse(record.spreadsheet_data),
        revisions: [],
    };
}

export function defineSpreadsheetDashboardDataRoute() {
    onRpc("/spreadsheet/dashboard/data/<int:res_id>", mockDashboardDataController);
}

export function defineSpreadsheetDashboardModels() {
    defineSpreadsheetDashboardDataRoute();
    const SpreadsheetDashboardModels = [
        SpreadsheetDashboard,
        SpreadsheetDashboardGroup,
    ];
    Object.assign(SpreadsheetModels, SpreadsheetDashboardModels);
    defineSpreadsheetModels();
}
