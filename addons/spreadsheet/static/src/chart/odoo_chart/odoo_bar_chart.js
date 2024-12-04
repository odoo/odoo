import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = registries;

const {
    getBarChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getBarChartScales,
    getBarChartTooltip,
    getChartTitle,
    getBarChartLegend,
    getChartShowValues,
    getTrendDatasetForBarChart,
<<<<<<< saas-18.1
    truncateLabel,
} = chartHelpers;
||||||| 923a389f1b707f582fb08bd84afe145c41b90fde
    formatTickValue
} = spreadsheet.helpers;

const { TREND_LINE_XAXIS_ID } = spreadsheet.constants;
=======
    formatValue,
    formatTickValue,
} = spreadsheet.helpers;

const { TREND_LINE_XAXIS_ID } = spreadsheet.constants;
>>>>>>> be776e735dd4a5db1090df66dea41876be431911

export class OdooBarChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.verticalAxisPosition = definition.verticalAxisPosition;
        this.stacked = definition.stacked;
        this.axesDesign = definition.axesDesign;
        this.horizontal = definition.horizontal;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            verticalAxisPosition: this.verticalAxisPosition,
            stacked: this.stacked,
            axesDesign: this.axesDesign,
            trend: this.trend,
            horizontal: this.horizontal,
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
            layout: getChartLayout(definition),
            scales: getBarChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition),
                legend: getBarChartLegend(definition, chartData),
                tooltip: getBarChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
<<<<<<< saas-18.1
            ...getters.getChartDatasetActionCallbacks(chart),
||||||| 923a389f1b707f582fb08bd84afe145c41b90fde
            title: getChartAxisTitleRuntime(chart.axesDesign?.x),
        },
        y: {
            position: chart.verticalAxisPosition,
            ticks: { color },
            beginAtZero: true, // the origin of the y axis is always zero
            title: getChartAxisTitleRuntime(chart.axesDesign?.y),
=======
            title: getChartAxisTitleRuntime(chart.axesDesign?.x),
        },
        y: {
            position: chart.verticalAxisPosition,
            ticks: {
                color,
                callback: (value) =>
                    formatValue(value, {
                        locale,
                        format: Math.abs(value) >= 1000 ? "#,##" : undefined,
                    }),
            },
            beginAtZero: true, // the origin of the y axis is always zero
            title: getChartAxisTitleRuntime(chart.axesDesign?.y),
>>>>>>> be776e735dd4a5db1090df66dea41876be431911
        },
    };

    return { background, chartJsConfig: config };
}
