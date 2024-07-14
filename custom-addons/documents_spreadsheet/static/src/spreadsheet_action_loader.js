/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadSpreadsheetAction } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

const actionRegistry = registry.category("actions");

const loadActionSpreadsheet = async (env, context) => {
    await loadSpreadsheetAction(env, "action_open_spreadsheet", loadActionSpreadsheet);

    return {
        ...context,
        target: "current",
        tag: "action_open_spreadsheet",
        type: "ir.actions.client",
    };
};

const loadActionSpreadsheetTemplate = async (env, context) => {
    await loadSpreadsheetAction(env, "action_open_template", loadActionSpreadsheetTemplate);

    return {
        ...context,
        target: "current",
        tag: "action_open_template",
        type: "ir.actions.client",
    };
};

actionRegistry.add("action_open_spreadsheet", loadActionSpreadsheet);
actionRegistry.add("action_open_template", loadActionSpreadsheetTemplate);
