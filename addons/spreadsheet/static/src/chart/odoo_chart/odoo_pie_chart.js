import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = registries;

const {
    getPieChartDatasets,
    CHART_COMMON_OPTIONS,
    getPieChartLayout,
    getPieChartTooltip,
    getChartTitle,
    getPieChartLegend,
    getChartShowValues,
    truncateLabel,
} = chartHelpers;

chartRegistry.add("odoo_pie", {
    match: (type) => type === "odoo_pie",
    createChart: (definition, sheetId, getters) => new OdooChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => OdooChart.getDefinitionFromContextCreation(),
    name: _t("Pie"),
});

function createOdooChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getData();
    const definition = chart.getDefinition();
    definition.dataSets = datasets.map(() => ({ trend: definition.trend }));

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale: getters.getLocale(),
    };

    const config = {
        type: "pie",
        data: {
            labels: chartData.labels.map(truncateLabel),
            datasets: getPieChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getPieChartLayout(definition),
            plugins: {
                title: getChartTitle(definition),
                legend: getPieChartLegend(definition, chartData),
                tooltip: getPieChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            ...getters.getChartDatasetActionCallbacks(chart),
        },
    };

    return { background, chartJsConfig: config };
}
