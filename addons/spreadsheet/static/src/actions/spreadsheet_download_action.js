/** @odoo-module */

import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { createSpreadsheetModel } from "@spreadsheet/helpers";

async function downloadSpreadsheet(env, action) {
    const { orm, name, data, stateUpdateMessages } = action.params;
    const model = createSpreadsheetModel({
        orm,
        data,
        stateUpdateMessages,
    });
    await waitForDataLoaded(model);
    const { files } = model.exportXLSX();
    await download({
        url: "/spreadsheet/xlsx",
        data: {
            zip_name: `${name}.xlsx`,
            files: JSON.stringify(files),
        },
    });
}

/**
 * Ensure that the spreadsheet does not contains cells that are in loading state
 * @param {Model} model
 * @returns {Promise<void>}
 */
async function waitForDataLoaded(model) {
    const dataSources = model.config.custom.dataSources;
    return new Promise((resolve, reject) => {
        function check() {
            if (isLoaded(model)) {
                dataSources.removeEventListener("data-source-updated", check);
                resolve();
            }
        }
        dataSources.addEventListener("data-source-updated", check);
        check();
    });
}

function isLoaded(model) {
    for (const sheetId of model.getters.getSheetIds()) {
        for (const cell of Object.values(model.getters.getEvaluatedCells(sheetId))) {
            if (cell.type === "error" && cell.error.message === _t("Data is loading")) {
                return false;
            }
        }
    }
    return true;
}

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });
