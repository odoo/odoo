/** @odoo-module */

import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";
import { _t } from "@web/core/l10n/translation";

const { Model } = spreadsheet;

async function downloadSpreadsheet(env, action) {
    let { orm, name, data, stateUpdateMessages, xlsxData } = action.params;
    if (!xlsxData) {
        const dataSources = new DataSources(orm);
        const model = new Model(migrate(data), { dataSources }, stateUpdateMessages);
        await waitForDataLoaded(model);
        xlsxData = model.exportXLSX();
    }
    await download({
        url: "/spreadsheet/xlsx",
        data: {
            zip_name: `${name}.xlsx`,
            files: JSON.stringify(xlsxData.files),
        },
    });
}

/**
 * Ensure that the spreadsheet does not contains cells that are in loading state
 * @param {Model} model
 * @returns {Promise<void>}
 */
export async function waitForDataLoaded(model) {
    const dataSources = model.config.dataSources;
    return new Promise((resolve, reject) => {
        function check() {
            model.dispatch("EVALUATE_CELLS");
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
        for (const cell of Object.values(model.getters.getCells(sheetId))) {
            if (
                cell.evaluated &&
                cell.evaluated.type === "error" &&
                cell.evaluated.error.message === _t("Data is loading")
            ) {
                return false;
            }
        }
    }
    return true;
}

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });
