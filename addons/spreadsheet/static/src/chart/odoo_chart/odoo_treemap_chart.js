import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";
import { onOdooChartItemHover, onTreemapOdooChartItemClick } from "./odoo_chart_helpers";

const { chartRegistry } = registries;

const {
    getTreeMapChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getChartTitle,
    getTreeMapChartTooltip,
} = chartHelpers;

export class OdooTreemapChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.showLabels = definition.showLabels;
        this.valuesDesign = definition.valuesDesign;
        this.coloringOptions = definition.coloringOptions;
        this.headerDesign = definition.headerDesign;
        this.showHeaders = definition.showHeaders;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            showLabels: this.showLabels,
            valuesDesign: this.valuesDesign,
            coloringOptions: this.coloringOptions,
            headerDesign: this.headerDesign,
            showHeaders: this.showHeaders,
        };
    }
}

chartRegistry.add("odoo_treemap", {
    match: (type) => type === "odoo_treemap",
    createChart: (definition, sheetId, getters) =>
        new OdooTreemapChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooTreemapChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooTreemapChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () =>
        OdooTreemapChart.getDefinitionFromContextCreation(),
    name: _t("Treemap"),
});

function createOdooChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getHierarchicalData();

    const definition = chart.getDefinition();
    const locale = getters.getLocale();

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale,
    };

    const config = {
        type: "treemap",
        data: {
            labels: chartData.labels,
            datasets: getTreeMapChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition, chartData),
            plugins: {
                title: getChartTitle(definition, getters),
                legend: { display: false },
                tooltip: getTreeMapChartTooltip(definition, chartData),
            },
            onHover: onOdooChartItemHover(),
            onClick: onTreemapOdooChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
