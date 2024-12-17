import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";
import { onOdooChartItemHover, onOdooChartItemClick } from "./odoo_chart_helpers";

const { chartRegistry } = registries;

const {
    CHART_COMMON_OPTIONS,
    getBarChartDatasets,
    getChartLayout,
    getChartTitle,
    getChartShowValues,
    getPyramidChartScales,
    getBarChartLegend,
    getPyramidChartTooltip,
    truncateLabel,
} = chartHelpers;

export class OdooPyramidChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.axesDesign = definition.axesDesign;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            axesDesign: this.axesDesign,
            horizontal: true,
            stacked: true,
        };
    }
}

chartRegistry.add("odoo_pyramid", {
    match: (type) => type === "odoo_pyramid",
    createChart: (definition, sheetId, getters) =>
        new OdooPyramidChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooPyramidChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooPyramidChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () =>
        OdooPyramidChart.getDefinitionFromContextCreation(),
    name: _t("Pyramid"),
});

function createOdooChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    const { datasets, labels } = chart.dataSource.getData();

    const pyramidDatasets = [];
    if (datasets[0]) {
        const pyramidData = datasets[0].data.map((value) => (value > 0 ? value : 0));
        pyramidDatasets.push({ ...datasets[0], data: pyramidData });
    }
    if (datasets[1]) {
        const pyramidData = datasets[1].data.map((value) => (value > 0 ? -value : 0));
        pyramidDatasets.push({ ...datasets[1], data: pyramidData });
    }

    const definition = chart.getDefinition();
    const locale = getters.getLocale();

    const chartData = {
        labels,
        dataSetsValues: pyramidDatasets.map((ds) => ({ data: ds.data, label: ds.label })),
        locale,
    };

    const config = {
        type: "bar",
        data: {
            labels: chartData.labels.map(truncateLabel),
            datasets: getBarChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            indexAxis: "y",
            layout: getChartLayout(definition),
            scales: getPyramidChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition),
                legend: getBarChartLegend(definition, chartData),
                tooltip: getPyramidChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            onHover: onOdooChartItemHover(),
            onClick: onOdooChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
