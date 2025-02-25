import { getBasicData } from "@spreadsheet/../tests/helpers/data";
import { serverState } from "@web/../tests/web_test_helpers";

export function getMenuServerData() {
    const serverData = {};
    serverData.menus = {
        1: {
            id: 1,
            name: "App_1",
            appID: 1,
            xmlid: "app_1",
            children: [
                {
                    id: 11,
                    name: "menu with xmlid",
                    appID: 1,
                    xmlid: "test_menu",
                    actionID: "spreadsheet.action1",
                },
                {
                    id: 12,
                    name: "menu without xmlid",
                    actionID: "spreadsheet.action1",
                    appID: 1,
                },
            ],
        },
    };
    serverData.actions = {
        action1: {
            id: 99,
            xml_id: "spreadsheet.action1",
            name: "action1",
            res_model: "ir.ui.menu",
            type: "ir.actions.act_window",
            views: [
                [1, "list"],
                [2, "form"],
            ],
        },
        action2: {
            id: 199,
            xml_id: "spreadsheet.action2",
            name: "action1",
            res_model: "ir.ui.menu",
            type: "ir.actions.act_window",
            views: [
                [false, "graph"],
                [false, "pivot"],
            ],
        },
    };
    serverData.models = {
        ...getBasicData(),
        "ir.ui.menu": {
            fields: {
                name: { string: "Name", type: "char" },
                action: { string: "Action", type: "char" },
                groups_id: { string: "Groups", type: "many2many", relation: "res.group" },
            },
            records: [
                { id: 11, name: "menu with xmlid", action: "action1", groups_id: [10] },
                { id: 12, name: "menu without xmlid", action: "action1", groups_id: [10] },
            ],
        },
        "res.users": {
            fields: {
                name: { string: "Name", type: "char" },
                groups_id: { string: "Groups", type: "many2many", relation: "res.group" },
            },
            records: [
                {
                    id: 1,
                    name: "Raoul",
                    active: true,
                    partner_id: serverState.partnerId,
                    groups_id: [10],
                },
                { id: 2, name: "Joseph", groups_id: [] },
            ],
        },
        "res.group": {
            fields: { name: { string: "Name", type: "char" } },
            records: [{ id: 10, name: "test group" }],
        },
    };
    serverState.userId = 1;
    return serverData;
}
