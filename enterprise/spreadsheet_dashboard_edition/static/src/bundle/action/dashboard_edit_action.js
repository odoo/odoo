/** @odoo-module */

import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { useSubEnv } from "@odoo/owl";

export class DashboardEditAction extends AbstractSpreadsheetAction {
    static template = "spreadsheet_dashboard_edition.DashboardEditAction";

    resModel = "spreadsheet.dashboard";
    threadField = "dashboard_id";
    notificationMessage = _t("New dashboard created");

    setup() {
        super.setup();
        useSubEnv({
            makeCopy: this.makeCopy.bind(this),
            onSpreadsheetShared: this.shareSpreadsheet.bind(this),
            isDashboardPublished: () => this.data && this.data.is_published,
            toggleDashboardPublished: this.togglePublished.bind(this),
            isRecordReadonly: () => this.data && this.data.isReadonly,
        });
    }

    togglePublished(is_published) {
        this.orm.write("spreadsheet.dashboard", [this.resId], {
            is_published,
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

registry.category("actions").add("action_edit_dashboard", DashboardEditAction, { force: true });
