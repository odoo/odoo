/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadSpreadsheetAction } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

const actionRegistry = registry.category("actions");

const loadActionSpreadsheetHistory = async (env, context) => {
    await loadSpreadsheetAction(
        env,
        "action_open_spreadsheet_history",
        loadActionSpreadsheetHistory
    );

    return {
        ...context,
        target: "current",
        tag: "action_open_spreadsheet_history",
        type: "ir.actions.client",
    };
};

actionRegistry.add("action_open_spreadsheet_history", loadActionSpreadsheetHistory);
