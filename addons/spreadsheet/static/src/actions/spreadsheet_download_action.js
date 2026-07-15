import { createSpreadsheetModel, waitForDataLoaded } from "@spreadsheet/helpers/model";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {object} action
 */
async function downloadSpreadsheet(env, action) {
    const notification = useService("notification");
    const canExport = await user.hasGroup("base.group_allow_export");
    if (!canExport) {
        notification.add(
            _t("You don't have the rights to export data. Please contact an Administrator."),
            {
                title: _t("Access Error"),
                type: "danger",
            }
        );
        return;
    }
    let { name, data, sources, stateUpdateMessages, xlsxData } = action.params;
    if (!xlsxData) {
        const model = await createSpreadsheetModel({ env, data, revisions: stateUpdateMessages });
        await waitForDataLoaded(model);
        xlsxData = await model.exportXLSX();
        sources = model.getters.getLoadedDataSources();
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

registry
    .category("actions")
    .add("action_download_spreadsheet", downloadSpreadsheet, { force: true });
