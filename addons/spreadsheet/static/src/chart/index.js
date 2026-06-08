import * as spreadsheet from "@odoo/o-spreadsheet";
import { OdooChartCorePlugin } from "./plugins/odoo_chart_core_plugin";
import { ChartOdooLinkPlugin } from "./plugins/chart_odoo_link_plugin";
import { OdooChartCoreViewPlugin } from "./plugins/odoo_chart_core_view_plugin";
import { chartOdooLinkPlugin } from "./odoo_link/odoo_link_chartjs_plugin";

const { chartJsExtensionRegistry } = spreadsheet.registries;

chartJsExtensionRegistry.add("chartOdooLinkPlugin", {
    register: (Chart) => Chart.register(chartOdooLinkPlugin),
    unregister: (Chart) => Chart.unregister(chartOdooLinkPlugin),
});

export { OdooChartCorePlugin, ChartOdooLinkPlugin, OdooChartCoreViewPlugin };
