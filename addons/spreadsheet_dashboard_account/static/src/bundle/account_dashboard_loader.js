import { DashboardLoader } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_loader_service";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;

patch(DashboardLoader.prototype, {
    getModelConfig(serverResult) {
        const config = super.getModelConfig(serverResult);
        config.custom = {
            ...config.custom,
            currentFiscalYearStart: DateTime.fromISO(serverResult.current_fiscal_year_start),
            currentFiscalYearEnd: DateTime.fromISO(serverResult.current_fiscal_year_end),
        };
        return config;
    },
});
