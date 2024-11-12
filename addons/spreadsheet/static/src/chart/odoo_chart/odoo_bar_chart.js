import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = registries;

const {
    getBarChartDatasets,
    CHART_COMMON_OPTIONS,
    getBarChartLayout,
    getBarChartScales,
    getBarChartTooltip,
    getChartTitle,
    getBarChartLegend,
    getChartShowValues,
    getTrendDatasetForBarChart,
    truncateLabel,
} = chartHelpers;

export class OdooBarChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.verticalAxisPosition = definition.verticalAxisPosition;
        this.stacked = definition.stacked;
        this.axesDesign = definition.axesDesign;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            verticalAxisPosition: this.verticalAxisPosition,
            stacked: this.stacked,
            axesDesign: this.axesDesign,
            trend: this.trend,
        };
    }
}

chartRegistry.add("odoo_bar", {
    match: (type) => type === "odoo_bar",
    createChart: (definition, sheetId, getters) => new OdooBarChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooBarChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooBarChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => OdooBarChart.getDefinitionFromContextCreation(),
    name: _t("Bar"),
});

function createOdooChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getData();
    const definition = chart.getDefinition();

    const trendDataSetsValues = datasets.map((dataset, index) => {
        const trend = definition.dataSets[index]?.trend;
        return !trend?.display || chart.horizontal
            ? undefined
            : getTrendDatasetForBarChart(trend, dataset.data);
    });

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale: getters.getLocale(),
        trendDataSetsValues,
    };

    const config = {
        type: "bar",
        data: {
            labels: chartData.labels.map(truncateLabel),
            datasets: getBarChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            indexAxis: chart.horizontal ? "y" : "x",
            layout: getBarChartLayout(definition),
            scales: getBarChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition),
                legend: getBarChartLegend(definition, chartData),
                tooltip: getBarChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            ...getters.getChartDatasetActionCallbacks(chart),
        },
    };

    return { background, chartJsConfig: config };
}
