/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { CommonOdooChartConfigPanel } from "./common/config_panel";
import { OdooBarChartConfigPanel } from "./odoo_bar/odoo_bar_config_panel";
import { OdooLineChartConfigPanel } from "./odoo_line/odoo_line_config_panel";
import { OdooChartWithAxisDesignPanel } from "./odoo_chart_with_axis/design_panel";
import { _t } from "@web/core/l10n/translation";

const { chartSidePanelComponentRegistry, chartSubtypeRegistry } = spreadsheet.registries;
const { PieChartDesignPanel } = spreadsheet.components;

chartSidePanelComponentRegistry
    .add("odoo_line", {
        configuration: OdooLineChartConfigPanel,
        design: OdooChartWithAxisDesignPanel,
    })
    .add("odoo_bar", {
        configuration: OdooBarChartConfigPanel,
        design: OdooChartWithAxisDesignPanel,
    })
    .add("odoo_pie", {
        configuration: CommonOdooChartConfigPanel,
        design: PieChartDesignPanel,
    });

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
    matcher: (definition) => definition.type === "odoo_bar" && !definition.stacked,
    subtypeDefinition: { stacked: false },
    displayName: _t("Column"),
    chartSubtype: "odoo_bar",
    chartType: "odoo_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.COLUMN_CHART",
});
chartSubtypeRegistry.add("odoo_stacked_bar", {
    matcher: (definition) => definition.type === "odoo_bar" && definition.stacked,
    subtypeDefinition: { stacked: true },
    displayName: _t("Stacked Column"),
    chartSubtype: "odoo_stacked_bar",
    chartType: "odoo_bar",
    category: "column",
    preview: "o-spreadsheet-ChartPreview.STACKED_COLUMN_CHART",
});
chartSubtypeRegistry.add("odoo_pie", {
    displayName: _t("Pie"),
    chartSubtype: "odoo_pie",
    chartType: "odoo_pie",
    category: "pie",
    preview: "o-spreadsheet-ChartPreview.PIE_CHART",
});
