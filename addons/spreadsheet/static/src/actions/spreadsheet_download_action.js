/** @odoo-module */

import { DataSources } from "@spreadsheet/data_sources/data_sources";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";
import { _t } from "@web/core/l10n/translation";

const { Model } = spreadsheet;

async function downloadSpreadsheet(env, action) {
    const canExport = await env.services.user.hasGroup("base.group_allow_export");
    if (!canExport) {
        env.services.notification.add(
            env._t("You don't have the rights to export data. Please contact an Administrator."),
            {
                title: env._t("Access Error"),
                type: "danger",
            }
        );
        return;
    }
    let { orm, name, data, sources, stateUpdateMessages, xlsxData } = action.params;
    if (!xlsxData) {
        const dataSources = new DataSources(orm);
        const model = new Model(migrate(data), { dataSources }, stateUpdateMessages);
        await waitForDataLoaded(model);
        sources = model.getters.getLoadedDataSources();
        xlsxData = model.exportXLSX();
    }
    await download({
        url: "/spreadsheet/xlsx",
        data: {
            zip_name: `${name}.xlsx`,
            files: new Blob([JSON.stringify(xlsxData.files)], {
                type: "application/json",
            }),
            datasources: new Blob([JSON.stringify(sources)], {
                type: "application/json",
            }),
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
