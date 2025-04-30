import * as spreadsheet from "@odoo/o-spreadsheet";
import { chartOdooMenuPlugin } from "./odoo_menu/odoo_menu_chartjs_plugin";

const { chartComponentRegistry, chartJsExtensionRegistry } = spreadsheet.registries;
const { ChartJsComponent } = spreadsheet.components;

chartComponentRegistry.add("odoo_bar", ChartJsComponent);
chartComponentRegistry.add("odoo_line", ChartJsComponent);
chartComponentRegistry.add("odoo_pie", ChartJsComponent);
chartComponentRegistry.add("odoo_radar", ChartJsComponent);
chartComponentRegistry.add("odoo_waterfall", ChartJsComponent);
chartComponentRegistry.add("odoo_pyramid", ChartJsComponent);
chartComponentRegistry.add("odoo_scatter", ChartJsComponent);
chartComponentRegistry.add("odoo_combo", ChartJsComponent);

chartJsExtensionRegistry.add("chartOdooMenuPlugin", {
    register: (Chart) => Chart.register(chartOdooMenuPlugin),
    unregister: (Chart) => Chart.unregister(chartOdooMenuPlugin),
});

import { OdooChartCorePlugin } from "./plugins/odoo_chart_core_plugin";
import { ChartOdooMenuPlugin } from "./plugins/chart_odoo_menu_plugin";
import { OdooChartUIPlugin } from "./plugins/odoo_chart_ui_plugin";

export { OdooChartCorePlugin, ChartOdooMenuPlugin, OdooChartUIPlugin };
