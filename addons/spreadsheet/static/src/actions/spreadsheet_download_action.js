/** @odoo-module */

import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { createSpreadsheetModel, waitForDataLoaded } from "@spreadsheet/helpers/model";

async function downloadSpreadsheet(env, action) {
    let { orm, name, data, stateUpdateMessages, xlsxData } = action.params;
    if (!xlsxData) {
        const model = await createSpreadsheetModel({ orm, data, revisions: stateUpdateMessages });
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

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });
