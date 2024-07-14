/** @odoo-module */

import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { registry } from "@web/core/registry";
import { SpreadsheetComponent } from "@spreadsheet_edition/bundle/actions/spreadsheet_component";
import { SpreadsheetControlPanel } from "@spreadsheet_edition/bundle/actions/control_panel/spreadsheet_control_panel";
import { _t } from "@web/core/l10n/translation";

import { useSubEnv } from "@odoo/owl";

export class DashboardEditAction extends AbstractSpreadsheetAction {
    resModel = "spreadsheet.dashboard";
    notificationMessage = _t("New dashboard created");

    setup() {
        super.setup();
        useSubEnv({
            makeCopy: this.makeCopy.bind(this),
        });
    }

    async _onSpreadSheetNameChanged(detail) {
        await super._onSpreadSheetNameChanged(detail);
        const { name } = detail;
        await this.orm.write("spreadsheet.dashboard", [this.resId], {
            name,
        });
    }

    async shareSpreadsheet(data, excelExport) {
        const url = await this.orm.call("spreadsheet.dashboard.share", "action_get_share_url", [
            {
                dashboard_id: this.resId,
                spreadsheet_data: JSON.stringify(data),
                excel_files: excelExport.files,
            },
        ]);
        return url;
    }
}

DashboardEditAction.template = "spreadsheet_dashboard_edition.DashboardEditAction";
DashboardEditAction.components = {
    SpreadsheetControlPanel,
    SpreadsheetComponent,
};

registry.category("actions").add("action_edit_dashboard", DashboardEditAction, { force: true });
