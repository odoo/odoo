import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";
import { onOdooChartItemHover, onOdooChartItemClick } from "./odoo_chart_helpers";

const { chartRegistry } = registries;

const {
    getComboChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getBarChartScales,
    getBarChartTooltip,
    getChartTitle,
    getComboChartLegend,
    getChartShowValues,
    getTrendDatasetForBarChart,
    truncateLabel,
} = chartHelpers;

export class OdooComboChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.axesDesign = definition.axesDesign;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            axesDesign: this.axesDesign,
        };
    }

    get dataSets() {
        const dataSets = super.dataSets;
        if (dataSets.every((ds) => !ds.type)) {
            return dataSets.map((ds, index) => ({
                ...ds,
                type: index === 0 ? "bar" : "line",
            }));
        }
        return dataSets;
    }
}

chartRegistry.add("odoo_combo", {
    match: (type) => type === "odoo_combo",
    createChart: (definition, sheetId, getters) => new OdooComboChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooComboChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooComboChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => OdooComboChart.getDefinitionFromContextCreation(),
    name: _t("Combo"),
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
            datasets: getComboChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition),
            scales: getBarChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition),
                legend: getComboChartLegend(definition, chartData),
                tooltip: getBarChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            onHover: onOdooChartItemHover(),
            onClick: onOdooChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
