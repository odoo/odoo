import {
    SpreadsheetModels,
    defineSpreadsheetModels,
    getBasicData,
} from "@spreadsheet/../tests/helpers/data";
import { fields, models, onRpc } from "@web/../tests/web_test_helpers";
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

export function getServerData(spreadsheetData) {
    const serverData = getDashboardServerData();
    serverData.models = {
        ...serverData.models,
        ...getBasicData(),
    };
    serverData.models["spreadsheet.dashboard.group"].records = [
        {
            published_dashboard_ids: [789],
            id: 1,
            name: "Pivot",
        },
    ];
    serverData.models["spreadsheet.dashboard"].records = [
        {
            id: 789,
            name: "Spreadsheet with Pivot",
            json_data: JSON.stringify(spreadsheetData),
            spreadsheet_data: JSON.stringify(spreadsheetData),
            dashboard_group_id: 1,
        },
    ];
    return serverData;
}

export class SpreadsheetDashboard extends models.Model {
    _name = "spreadsheet.dashboard";

    name = fields.Char({ string: "Name" });
    spreadsheet_data = fields.Char({});
    json_data = fields.Char({});
    is_published = fields.Boolean({ string: "Is published" });
    dashboard_group_id = fields.Many2one({ relation: "spreadsheet.dashboard.group" });
    favorite_user_ids = fields.Many2many({ relation: "res.users", string: "Favorite Users" });
    is_favorite = fields.Boolean({ compute: "_compute_is_favorite", string: "Is Favorite" });

    _compute_is_favorite() {
        for (const record of this) {
            record.is_favorite = record.favorite_user_ids.includes(this.env.uid);
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

export class SpreadsheetDashboardFavoriteFilters extends models.Model {
    _name = "spreadsheet.dashboard.favorite.filters";

    name = fields.Char({ required: true });
    user_ids = fields.Many2many({
        relation: "res.users",
    });
    dashboard_id = fields.Many2one({
        string: "Dashboard",
        relation: "spreadsheet.dashboard",
    });
    is_default = fields.Boolean();
    global_filters = fields.Json();

    get_filters(dashboard) {
        return this.search_read(
            [
                ["dashboard_id", "=", dashboard],
                ["user_ids", "in", [this.env.uid, false]],
            ],
            ["name", "is_default", "global_filters", "user_ids"]
        );
    }
}

function mockDashboardDataController(_request, { res_id }) {
    const [record] = this.env["spreadsheet.dashboard"].search_read([["id", "=", parseInt(res_id)]]);
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

onRpc("/spreadsheet/dashboard/data/<int:res_id>", mockDashboardDataController);

export function defineSpreadsheetDashboardModels() {
    const SpreadsheetDashboardModels = [
        SpreadsheetDashboard,
        SpreadsheetDashboardGroup,
        SpreadsheetDashboardFavoriteFilters,
    ];
    Object.assign(SpreadsheetModels, SpreadsheetDashboardModels);
    defineSpreadsheetModels();
}
