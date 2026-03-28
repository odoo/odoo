import { components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

patch(components.ZoomableChartJsComponent.prototype, {
    getMasterChartConfiguration(chartData) {
        const config = super.getMasterChartConfiguration(chartData);
        config.options = {
            ...config.options,
            onHover: undefined,
            onClick: undefined,
        };
        return config;
    },
});
