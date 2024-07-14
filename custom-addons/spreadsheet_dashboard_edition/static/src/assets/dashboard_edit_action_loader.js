/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadSpreadsheetAction } from "@spreadsheet/assets_backend/spreadsheet_action_loader";

const actionRegistry = registry.category("actions");

const loadDashboardAction = async (env, context) => {
    await loadSpreadsheetAction(env, "action_edit_dashboard", loadDashboardAction);
    return {
        ...context,
        target: "current",
        tag: "action_edit_dashboard",
        type: "ir.actions.client",
    };
};

actionRegistry.add("action_edit_dashboard", loadDashboardAction);
