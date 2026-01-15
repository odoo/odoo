import * as spreadsheet from "@odoo/o-spreadsheet";
import { OdooChartCorePlugin } from "./plugins/odoo_chart_core_plugin";
import { ChartOdooMenuPlugin } from "./plugins/chart_odoo_menu_plugin";
import { OdooChartCoreViewPlugin } from "./plugins/odoo_chart_core_view_plugin";
import { _t } from "@web/core/l10n/translation";
import { chartOdooMenuPlugin } from "./odoo_menu/odoo_menu_chartjs_plugin";

const { chartComponentRegistry, chartSubtypeRegistry, chartJsExtensionRegistry } =
    spreadsheet.registries;
const { ChartJsComponent, ZoomableChartJsComponent } = spreadsheet.components;

chartComponentRegistry.add("odoo_bar", ZoomableChartJsComponent);
chartComponentRegistry.add("odoo_line", ZoomableChartJsComponent);
chartComponentRegistry.add("odoo_pie", ChartJsComponent);
chartComponentRegistry.add("odoo_radar", ChartJsComponent);
chartComponentRegistry.add("odoo_sunburst", ChartJsComponent);
chartComponentRegistry.add("odoo_treemap", ChartJsComponent);
chartComponentRegistry.add("odoo_waterfall", ZoomableChartJsComponent);
chartComponentRegistry.add("odoo_pyramid", ChartJsComponent);
chartComponentRegistry.add("odoo_scatter", ZoomableChartJsComponent);
chartComponentRegistry.add("odoo_combo", ZoomableChartJsComponent);
chartComponentRegistry.add("odoo_geo", ChartJsComponent);
chartComponentRegistry.add("odoo_funnel", ChartJsComponent);

chartSubtypeRegistry.add("odoo_line", {
    matcher: (definition) =>
        definition.type === "odoo_line" && !definition.stacked && !definition.fillArea,
    subtypeDefinition: { stacked: false, fillArea: false },
    displayName: _t("Line"),
    chartSubtype: "odoo_line",
    chartType: "odoo_line",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.LINE_CHART",
});
chartSubtypeRegistry.add("odoo_stacked_line", {
    matcher: (definition) =>
        definition.type === "odoo_line" && definition.stacked && !definition.fillArea,
    subtypeDefinition: { stacked: true, fillArea: false },
    displayName: _t("Stacked Line"),
    chartSubtype: "odoo_stacked_line",
    chartType: "odoo_line",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.STACKED_LINE_CHART",
});
chartSubtypeRegistry.add("odoo_area", {
    matcher: (definition) =>
        definition.type === "odoo_line" && !definition.stacked && definition.fillArea,
    subtypeDefinition: { stacked: false, fillArea: true },
    displayName: _t("Area"),
    chartSubtype: "odoo_area",
    chartType: "odoo_line",
    category: "area",
    preview: "o-spreadsheet-ChartPreview.AREA_CHART",
});
chartSubtypeRegistry.add("odoo_stacked_area", {
    matcher: (definition) =>
        definition.type === "odoo_line" && definition.stacked && definition.fillArea,
    subtypeDefinition: { stacked: true, fillArea: true },
    displayName: _t("Stacked Area"),
    chartSubtype: "odoo_stacked_area",
    chartType: "odoo_line",
    category: "area",
    preview: "o-spreadsheet-ChartPreview.STACKED_AREA_CHART",
});
chartSubtypeRegistry.add("odoo_bar", {
    matcher: (definition) =>
        definition.type === "odoo_bar" && !definition.stacked && !definition.horizontal,
    subtypeDefinition: { stacked: false, horizontal: false },
    displayName: _t("Column"),
    chartSubtype: "odoo_bar",
    chartType: "odoo_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.COLUMN_CHART",
});
chartSubtypeRegistry.add("odoo_stacked_bar", {
    matcher: (definition) =>
        definition.type === "odoo_bar" && definition.stacked && !definition.horizontal,
    subtypeDefinition: { stacked: true, horizontal: false },
    displayName: _t("Stacked Column"),
    chartSubtype: "odoo_stacked_bar",
    chartType: "odoo_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.STACKED_COLUMN_CHART",
});
chartSubtypeRegistry.add("odoo_horizontal_bar", {
    matcher: (definition) =>
        definition.type === "odoo_bar" && !definition.stacked && definition.horizontal,
    subtypeDefinition: { stacked: false, horizontal: true },
    displayName: _t("Bar"),
    chartSubtype: "odoo_horizontal_bar",
    chartType: "odoo_bar",
    category: "bar",
    preview: "o-spreadsheet-ChartPreview.BAR_CHART",
});
chartSubtypeRegistry.add("odoo_horizontal_stacked_bar", {
    matcher: (definition) =>
        definition.type === "odoo_bar" && definition.stacked && definition.horizontal,
    subtypeDefinition: { stacked: true, horizontal: true },
    displayName: _t("Stacked Bar"),
    chartSubtype: "odoo_horizontal_stacked_bar",
    chartType: "odoo_bar",
    category: "bar",
    preview: "o-spreadsheet-ChartPreview.STACKED_BAR_CHART",
});
chartSubtypeRegistry.add("odoo_combo", {
    displayName: _t("Combo"),
    chartSubtype: "odoo_combo",
    chartType: "odoo_combo",
    category: "line",
    preview: "o-spreadsheet-ChartPreview.COMBO_CHART",
});
chartSubtypeRegistry.add("odoo_pie", {
    displayName: _t("Pie"),
    matcher: (definition) => definition.type === "odoo_pie" && !definition.isDoughnut,
    subtypeDefinition: { isDoughnut: false },
    chartSubtype: "odoo_pie",
    chartType: "odoo_pie",
    category: "pie",
    preview: "o-spreadsheet-ChartPreview.PIE_CHART",
});
chartSubtypeRegistry.add("odoo_doughnut", {
    matcher: (definition) => definition.type === "odoo_pie" && definition.isDoughnut,
    subtypeDefinition: { isDoughnut: true },
    displayName: _t("Doughnut"),
    chartSubtype: "odoo_doughnut",
    chartType: "odoo_pie",
    category: "pie",
    preview: "o-spreadsheet-ChartPreview.DOUGHNUT_CHART",
});
chartSubtypeRegistry.add("odoo_scatter", {
    displayName: _t("Scatter"),
    chartType: "odoo_scatter",
    chartSubtype: "odoo_scatter",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.SCATTER_CHART",
});
chartSubtypeRegistry.add("odoo_waterfall", {
    displayName: _t("Waterfall"),
    chartSubtype: "odoo_waterfall",
    chartType: "odoo_waterfall",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.WATERFALL_CHART",
});
chartSubtypeRegistry.add("odoo_pyramid", {
    displayName: _t("Population Pyramid"),
    chartSubtype: "odoo_pyramid",
    chartType: "odoo_pyramid",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.POPULATION_PYRAMID_CHART",
});
chartSubtypeRegistry.add("odoo_radar", {
    matcher: (definition) => definition.type === "odoo_radar" && !definition.fillArea,
    displayName: _t("Radar"),
    chartSubtype: "odoo_radar",
    chartType: "odoo_radar",
    subtypeDefinition: { fillArea: false },
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.RADAR_CHART",
});
chartSubtypeRegistry.add("odoo_filled_radar", {
    matcher: (definition) => definition.type === "odoo_radar" && !!definition.fillArea,
    displayName: _t("Filled Radar"),
    chartType: "odoo_radar",
    chartSubtype: "odoo_filled_radar",
    subtypeDefinition: { fillArea: true },
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.FILLED_RADAR_CHART",
});
chartSubtypeRegistry.add("odoo_geo", {
    displayName: _t("Geo chart"),
    chartType: "odoo_geo",
    chartSubtype: "odoo_geo",
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.GEO_CHART",
});
chartSubtypeRegistry.add("odoo_funnel", {
    matcher: (definition) => definition.type === "odoo_funnel",
    displayName: _t("Funnel"),
    chartType: "odoo_funnel",
    chartSubtype: "odoo_funnel",
    subtypeDefinition: { cumulative: true },
    category: "misc",
    preview: "o-spreadsheet-ChartPreview.FUNNEL_CHART",
});
chartSubtypeRegistry.add("odoo_treemap", {
    displayName: _t("Treemap"),
    chartType: "odoo_treemap",
    chartSubtype: "odoo_treemap",
    category: "hierarchical",
    preview: "o-spreadsheet-ChartPreview.TREE_MAP_CHART",
});
chartSubtypeRegistry.add("odoo_sunburst", {
    displayName: _t("Sunburst"),
    chartType: "odoo_sunburst",
    chartSubtype: "odoo_sunburst",
    category: "hierarchical",
    preview: "o-spreadsheet-ChartPreview.SUNBURST_CHART",
});

chartJsExtensionRegistry.add("chartOdooMenuPlugin", {
    register: (Chart) => Chart.register(chartOdooMenuPlugin),
    unregister: (Chart) => Chart.unregister(chartOdooMenuPlugin),
});

export { OdooChartCorePlugin, ChartOdooMenuPlugin, OdooChartCoreViewPlugin };
