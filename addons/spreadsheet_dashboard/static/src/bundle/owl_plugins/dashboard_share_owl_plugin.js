import { Plugin, types, useConfig, usePlugin } from "@odoo/owl";
import { ORM } from "@web/core/orm_plugin";

export class DashboardSharePlugin extends Plugin {
    orm = usePlugin(ORM);
    resId = useConfig("resIdSignal", types.signal());

    async shareDashboard(data, excelExport) {
        const url = await this.orm.call("spreadsheet.dashboard.share", "action_get_share_url", [
            {
                dashboard_id: this.resId(),
                spreadsheet_data: JSON.stringify(data),
                excel_files: excelExport.files,
            },
        ]);
        return url;
    }
}
