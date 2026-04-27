/** @odoo-module */

import { registry } from "@web/core/registry";
import { DocumentSelectorDialog } from "./document_selector_dialog/document_selector_dialog";

async function addSpreadsheetToDashboardSection(env, action) {
    const { dashboardGroupId } = action.params;
    const params = { dashboardGroupId };
    env.services.dialog.add(DocumentSelectorDialog, params);
}

registry
    .category("actions")
    .add("action_dashboard_add_spreadsheet", addSpreadsheetToDashboardSection);
