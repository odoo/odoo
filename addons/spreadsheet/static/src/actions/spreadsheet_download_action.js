/** @odoo-module */

import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";
import { _t } from "@web/core/l10n/translation";

const { Model } = spreadsheet;

async function downloadSpreadsheet(env, action) {
    const { orm, name, data, stateUpdateMessages } = action.params;
    const dataSources = new DataSources(orm);
    const model = new Model(migrate(data), { dataSources }, stateUpdateMessages);
    await dataSources.waitForAllLoaded();
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
 * @returns {Promise}
 */
async function waitForDataLoaded(model) {
    model.dispatch("EVALUATE_CELLS");
    return new Promise((resolve, reject) => {
        let interval = undefined;
        interval = browser.setInterval(() => {
            for (const sheetId of model.getters.getSheetIds()) {
                for (const cell of Object.values(model.getters.getCells(sheetId))) {
                    if (
                        cell.evaluated &&
                        cell.evaluated.type === "error" &&
                        cell.evaluated.error.message === _t("Data is loading")
                    ) {
                        model.dispatch("EVALUATE_CELLS");
                        return;
                    }
                }
            }
            browser.clearInterval(interval);
            resolve();
        }, 50);
    });
}

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });
