import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";
import { onOdooChartItemHover, onOdooChartItemClick } from "./odoo_chart_helpers";

const { chartRegistry } = registries;

const {
    getScatterChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getScatterChartScales,
    getLineChartTooltip,
    getChartTitle,
    getScatterChartLegend,
    getChartShowValues,
    getTrendDatasetForLineChart,
} = chartHelpers;

export class OdooScatterChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.verticalAxisPosition = definition.verticalAxisPosition;
        this.axesDesign = definition.axesDesign;
        this.zoomable = definition.zoomable;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            verticalAxisPosition: this.verticalAxisPosition,
            axesDesign: this.axesDesign,
            zoomable: this.zoomable,
        };
    }
}

chartRegistry.add("odoo_scatter", {
    match: (type) => type === "odoo_scatter",
    createChart: (definition, sheetId, getters) =>
        new OdooScatterChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooScatterChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooScatterChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () =>
        OdooScatterChart.getDefinitionFromContextCreation(),
    name: _t("Scatter"),
});

function createOdooChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getData();

    const definition = chart.getDefinition();
    const locale = getters.getLocale();

    const trendDataSetsValues = datasets.map((dataset, index) => {
        const trend = definition.dataSets[index]?.trend;
        return !trend?.display
            ? undefined
            : getTrendDatasetForLineChart(trend, dataset.data, labels, "category", locale);
    });

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale,
        trendDataSetsValues,
        axisType: definition.axisType || "category",
    };

    const config = {
        type: "line",
        data: {
            labels: chartData.labels,
            datasets: getScatterChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition, chartData),
            scales: getScatterChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition),
                legend: getScatterChartLegend(definition, chartData),
                tooltip: getLineChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            onHover: onOdooChartItemHover(),
            onClick: onOdooChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
