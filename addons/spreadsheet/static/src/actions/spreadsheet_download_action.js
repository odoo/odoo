/** @odoo-module */

import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { createSpreadsheetModel, waitForDataLoaded } from "@spreadsheet/helpers/model";

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {object} action
 */
async function downloadSpreadsheet(env, action) {
    const { name, data, stateUpdateMessages } = action.params;
    const model = await createSpreadsheetModel({ env, data, revisions: stateUpdateMessages });
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

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });
