/** @odoo-module */

import { getBasicData } from "@spreadsheet/../tests/utils/data";


export function getMenuServerData() {
    const serverData = {};
    serverData.menus = {
        root: { id: "root", children: [1, 2], name: "root", appID: "root" },
        1: {
            id: 1,
            children: [],
            name: "menu with xmlid",
            appID: 1,
            xmlid: "test_menu",
            actionID: "action1",
        },
        2: { id: 2, children: [], name: "menu without xmlid", appID: 2 },
    };
    serverData.actions = {
        action1: {
            id: 99,
            xml_id: "action1",
            name: "action1",
            res_model: "ir.ui.menu",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    };
    serverData.views = {};
    serverData.views["ir.ui.menu,false,list"] = `<tree></tree>`;
    serverData.views["ir.ui.menu,false,search"] = `<search></search>`;
    serverData.models = {
        ...getBasicData(),
        "ir.ui.menu": {
            fields: {
                name: { string: "Name", type: "char" },
                action: { string: "Action", type: "char" },
                groups_id: { string: "Groups", type: "many2many", relation: "res.group" },
            },
            records: [
                { id: 1, name: "menu with xmlid", action: "action1", groups_id: [10] },
                { id: 2, name: "menu without xmlid", action: "action2", groups_id: [10] },
            ],
        },
        "res.users": {
            fields: {
                name: { string: "Name", type: "char" },
                groups_id: { string: "Groups", type: "many2many", relation: "res.group" },
            },
            records: [
                { id: 1, name: "Raoul", groups_id: [10] },
                { id: 2, name: "Joseph", groups_id: [] },
            ],
        },
        "res.group": {
            fields: { name: { string: "Name", type: "char" } },
            records: [{ id: 10, name: "test group" }],
        },
    };
    return serverData;
}
