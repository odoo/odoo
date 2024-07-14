/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { InsertViewSpreadsheet } from "../insert_action_link_menu/insert_action_link_menu";
import { InsertListSpreadsheetMenu } from "../list_view/insert_list_spreadsheet_menu_owl";

import { Component } from "@odoo/owl";
const cogMenuRegistry = registry.category("cogMenu");

export class SpreadsheetCogMenu extends Component {
    static template = "spreadsheet_edition.SpreadsheetCogMenu";
    static components = { Dropdown, InsertViewSpreadsheet, InsertListSpreadsheetMenu };
}

cogMenuRegistry.add(
    "spreadsheet-cog-menu",
    {
        Component: SpreadsheetCogMenu,
        groupNumber: 30,
        isDisplayed: ({ config, isSmall }) =>
            !isSmall && config.actionType === "ir.actions.act_window" && config.viewType !== "form",
    },
    { sequence: 1 }
);
