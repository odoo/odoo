import * as spreadsheet from "@odoo/o-spreadsheet";
import { OdooChartCorePlugin } from "./plugins/odoo_chart_core_plugin";
import { ChartOdooLinkPlugin } from "./plugins/chart_odoo_link_plugin";
import { OdooChartCoreViewPlugin } from "./plugins/odoo_chart_core_view_plugin";
import { chartJsOdooLinkPlugin } from "./odoo_link/chartjs/odoo_link_chartjs_plugin";

const { chartJsExtensionRegistry } = spreadsheet.registries;

chartJsExtensionRegistry.add("chartJsOdooLinkPlugin", {
    register: (Chart) => Chart.register(chartJsOdooLinkPlugin),
    unregister: (Chart) => Chart.unregister(chartJsOdooLinkPlugin),
});

export { OdooChartCorePlugin, ChartOdooLinkPlugin, OdooChartCoreViewPlugin };
