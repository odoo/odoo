import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = registries;

const {
    getRadarChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getChartTitle,
    getChartShowValues,
    getRadarChartScales,
    getRadarChartLegend,
    getRadarChartTooltip,
    truncateLabel,
} = chartHelpers;

export class OdooRadarChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.fillArea = definition.fillArea;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            fillArea: this.fillArea,
        };
    }
}

chartRegistry.add("odoo_radar", {
    match: (type) => type === "odoo_radar",
    createChart: (definition, sheetId, getters) => new OdooRadarChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooRadarChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooRadarChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => OdooRadarChart.getDefinitionFromContextCreation(),
    name: _t("Radar"),
});

function createOdooChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getData();

    const definition = chart.getDefinition();
    const locale = getters.getLocale();

    const chartData = {
        labels,
        dataSetsValues: datasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale,
    };

    const config = {
        type: "radar",
        data: {
            labels: chartData.labels.map(truncateLabel),
            datasets: getRadarChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition),
            scales: getRadarChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition),
                legend: getRadarChartLegend(definition, chartData),
                tooltip: getRadarChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            ...getters.getChartDatasetActionCallbacks(chart),
        },
    };

    return { background, chartJsConfig: config };
}
