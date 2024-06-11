/** @odoo-module */

export function getDashboardServerData() {
    return {
        models: {
            "spreadsheet.dashboard": {
                fields: {
                    json_data: { type: "char" },
                    spreadsheet_data: { type: "char " },
                    name: { type: "char" },
                    dashboard_group_id: {
                        type: "many2one",
                        relation: "spreadsheet.dashboard.group",
                    },
                },
                records: [
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
                ],
            },
            "spreadsheet.dashboard.group": {
                fields: {
                    name: { type: "char" },
                    dashboard_ids: {
                        type: "one2many",
                        relation: "spreadsheet.dashboard",
                        relation_field: "dashboard_group_id",
                    },
                },
                records: [
                    { id: 1, name: "Container 1", dashboard_ids: [1, 2] },
                    { id: 2, name: "Container 2", dashboard_ids: [3] },
                ],
            },
        },
        views: {},
    };
}
