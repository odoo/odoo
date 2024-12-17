import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";
import { onOdooChartItemHover, onOdooChartItemClick } from "./odoo_chart_helpers";

const { chartRegistry } = registries;

const {
    getPieChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getPieChartTooltip,
    getChartTitle,
    getPieChartLegend,
    getChartShowValues,
    truncateLabel,
} = chartHelpers;

export class OdooPieChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.isDoughnut = definition.isDoughnut;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            isDoughnut: this.isDoughnut,
        };
    }
}

chartRegistry.add("odoo_pie", {
    match: (type) => type === "odoo_pie",
    createChart: (definition, sheetId, getters) => new OdooPieChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooPieChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooPieChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => OdooPieChart.getDefinitionFromContextCreation(),
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
        type: definition.isDoughnut ? "doughnut" : "pie",
        data: {
            labels: chartData.labels.map(truncateLabel),
            datasets: getPieChartDatasets(definition, chartData),
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition),
            plugins: {
                title: getChartTitle(definition),
                legend: getPieChartLegend(definition, chartData),
                tooltip: getPieChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            onHover: onOdooChartItemHover(),
            onClick: onOdooChartItemClick(getters, chart),
        },
    };

    return { background, chartJsConfig: config };
}
