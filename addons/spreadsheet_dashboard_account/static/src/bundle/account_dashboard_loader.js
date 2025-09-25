import { DashboardLoader } from "@spreadsheet_dashboard/bundle/dashboard_action/dashboard_loader_service";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;

patch(DashboardLoader.prototype, {
    getModelConfig(data) {
        const config = super.getModelConfig(data);
        config.custom = {
            ...config.custom,
            currentFiscalYearStart: DateTime.fromISO(data.current_fiscal_year_start),
            currentFiscalYearEnd: DateTime.fromISO(data.current_fiscal_year_end),
        };
        return config;
    },
});
