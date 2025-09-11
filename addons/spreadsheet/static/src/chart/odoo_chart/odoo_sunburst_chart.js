import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";
import { onOdooChartItemHover, onSunburstOdooChartItemClick } from "./odoo_chart_helpers";

const { chartRegistry } = registries;

const {
    getSunburstChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getChartTitle,
    getSunburstShowValues,
    getSunburstChartLegend,
    getSunburstChartTooltip,
} = chartHelpers;

export class OdooSunburstChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.showLabels = definition.showLabels;
        this.valuesDesign = definition.valuesDesign;
        this.groupColors = definition.groupColors;
        this.pieHolePercentage = definition.pieHolePercentage;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            pieHolePercentage: this.pieHolePercentage,
            showLabels: this.showLabels,
            valuesDesign: this.valuesDesign,
            groupColors: this.groupColors,
        };
    }
}

chartRegistry.add("odoo_sunburst", {
    match: (type) => type === "odoo_sunburst",
    createChart: (definition, sheetId, getters) =>
        new OdooSunburstChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooSunburstChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooSunburstChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () =>
        OdooSunburstChart.getDefinitionFromContextCreation(),
    name: _t("Sunburst"),
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
        type: "doughnut",
        data: {
            labels: chartData.labels,
            datasets: getSunburstChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            cutout: chart.pieHolePercentage === undefined ? "25%" : `${chart.pieHolePercentage}%`,
            layout: getChartLayout(definition, chartData),
            plugins: {
                title: getChartTitle(definition, getters),
                legend: getSunburstChartLegend(definition, chartData),
                tooltip: getSunburstChartTooltip(definition, chartData),
                sunburstLabelsPlugin: getSunburstShowValues(definition, chartData),
                sunburstHoverPlugin: { enabled: true },
            },
            onHover: onOdooChartItemHover(),
            onClick: onSunburstOdooChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
