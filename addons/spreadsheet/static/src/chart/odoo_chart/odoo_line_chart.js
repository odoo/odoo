import { registries, chartHelpers } from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = registries;

const {
    getLineChartDatasets,
    CHART_COMMON_OPTIONS,
    getChartLayout,
    getLineChartScales,
    getLineChartTooltip,
    getChartTitle,
    getLineChartLegend,
    getChartShowValues,
    getTrendDatasetForLineChart,
<<<<<<< saas-18.1
    truncateLabel,
} = chartHelpers;
||||||| 923a389f1b707f582fb08bd84afe145c41b90fde
    getChartAxisType,
    formatTickValue,
} = spreadsheet.helpers;

const { TREND_LINE_XAXIS_ID } = spreadsheet.constants;

const LINE_FILL_TRANSPARENCY = 0.4;
=======
    getChartAxisType,
    formatValue,
    formatTickValue,
} = spreadsheet.helpers;

const { TREND_LINE_XAXIS_ID } = spreadsheet.constants;

const LINE_FILL_TRANSPARENCY = 0.4;
>>>>>>> be776e735dd4a5db1090df66dea41876be431911

export class OdooLineChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.verticalAxisPosition = definition.verticalAxisPosition;
        this.stacked = definition.stacked;
        this.cumulative = definition.cumulative;
        this.axesDesign = definition.axesDesign;
        this.fillArea = definition.fillArea;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            verticalAxisPosition: this.verticalAxisPosition,
            stacked: this.stacked,
            cumulative: this.cumulative,
            axesDesign: this.axesDesign,
            fillArea: this.fillArea,
        };
    }
}

chartRegistry.add("odoo_line", {
    match: (type) => type === "odoo_line",
    createChart: (definition, sheetId, getters) => new OdooLineChart(definition, sheetId, getters),
    getChartRuntime: createOdooChartRuntime,
    validateChartDefinition: (validator, definition) =>
        OdooLineChart.validateChartDefinition(validator, definition),
    transformDefinition: (definition) => OdooLineChart.transformDefinition(definition),
    getChartDefinitionFromContextCreation: () => OdooLineChart.getDefinitionFromContextCreation(),
    name: _t("Line"),
});

function createOdooChartRuntime(chart, getters) {
    const background = chart.background || "#FFFFFF";
    let { datasets, labels } = chart.dataSource.getData();
    datasets = computeCumulatedDatasets(chart, datasets);

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
    };

    const chartJsDatasets = getLineChartDatasets(definition, chartData);
    const config = {
        type: "line",
        data: {
            labels: chartData.labels.map(truncateLabel),
            datasets: chartJsDatasets,
        },
        options: {
            ...CHART_COMMON_OPTIONS,
            layout: getChartLayout(definition),
            scales: getLineChartScales(definition, chartData),
            plugins: {
                title: getChartTitle(definition),
                legend: getLineChartLegend(definition, chartData),
                tooltip: getLineChartTooltip(definition, chartData),
                chartShowValuesPlugin: getChartShowValues(definition, chartData),
            },
            ...getters.getChartDatasetActionCallbacks(chart),
        },
    };

    return { background, chartJsConfig: config };
}

function computeCumulatedDatasets(chart, datasets) {
    const cumulatedDatasets = [];
    for (const dataset of datasets) {
        if (chart.cumulative) {
            let accumulator = dataset.cumulatedStart || 0;
            const data = dataset.data.map((value) => {
                accumulator += value;
                return accumulator;
            });
            cumulatedDatasets.push({ ...dataset, data });
        } else {
            cumulatedDatasets.push(dataset);
        }
    }
<<<<<<< saas-18.1
    return cumulatedDatasets;
||||||| 923a389f1b707f582fb08bd84afe145c41b90fde

    if (trendDatasets.length) {
        /* We add a second x axis here to draw the trend lines, with the labels length being
         * set so that the second axis points match the classical x axis
         */
        chartJsConfig.options.scales[TREND_LINE_XAXIS_ID] = {
            ...chartJsConfig.options.scales.x,
            type: "category",
            labels: Array(maxLength).fill(""),
            offset: false,
            display: false,
        };
        /* These datasets must be inserted after the original datasets to ensure the way we
         * distinguish the originals and trendLine datasets after
         */
        trendDatasets.forEach((x) => chartJsConfig.data.datasets.push(x));

        const originalTooltipTitle = chartJsConfig.options.plugins.tooltip.callbacks.title;
        chartJsConfig.options.plugins.tooltip.callbacks.title = function (tooltipItems) {
            if (tooltipItems.some((item) => item.dataset.xAxisID !== TREND_LINE_XAXIS_ID)) {
                return originalTooltipTitle?.(tooltipItems);
            }
            return "";
        };
    }
    return { background, chartJsConfig };
}

function getLineConfiguration(chart, labels, locale) {
    const fontColor = chartFontColor(chart.background);
    const config = getDefaultChartJsRuntime(chart, labels, fontColor, { locale });
    config.type = chart.type.replace("odoo_", "");
    const legend = {
        ...config.options.legend,
        display: chart.legendPosition !== "none",
    };
    legend.position = chart.legendPosition;
    config.options.plugins = config.options.plugins || {};
    config.options.plugins.legend = legend;
    config.options.layout = {
        padding: { left: 20, right: 20, top: chart.title ? 10 : 25, bottom: 10 },
    };
    config.options.scales = {
        x: {
            ticks: {
                // x axis configuration
                maxRotation: 60,
                minRotation: 15,
                padding: 5,
                labelOffset: 2,
                color: fontColor,
            },
            title: getChartAxisTitleRuntime(chart.axesDesign?.x),
        },
        y: {
            position: chart.verticalAxisPosition,
            ticks: {
                color: fontColor,
            },
            title: getChartAxisTitleRuntime(chart.axesDesign?.y),
        },
    };
    if (chart.stacked) {
        config.options.scales.y.stacked = true;
    }

    config.options.plugins.chartShowValuesPlugin = {
        showValues: chart.showValues,
        background: chart.background,
        callback: formatTickValue({ locale }),
    };
    return config;
=======

    if (trendDatasets.length) {
        /* We add a second x axis here to draw the trend lines, with the labels length being
         * set so that the second axis points match the classical x axis
         */
        chartJsConfig.options.scales[TREND_LINE_XAXIS_ID] = {
            ...chartJsConfig.options.scales.x,
            type: "category",
            labels: Array(maxLength).fill(""),
            offset: false,
            display: false,
        };
        /* These datasets must be inserted after the original datasets to ensure the way we
         * distinguish the originals and trendLine datasets after
         */
        trendDatasets.forEach((x) => chartJsConfig.data.datasets.push(x));

        const originalTooltipTitle = chartJsConfig.options.plugins.tooltip.callbacks.title;
        chartJsConfig.options.plugins.tooltip.callbacks.title = function (tooltipItems) {
            if (tooltipItems.some((item) => item.dataset.xAxisID !== TREND_LINE_XAXIS_ID)) {
                return originalTooltipTitle?.(tooltipItems);
            }
            return "";
        };
    }
    return { background, chartJsConfig };
}

function getLineConfiguration(chart, labels, locale) {
    const fontColor = chartFontColor(chart.background);
    const config = getDefaultChartJsRuntime(chart, labels, fontColor, { locale });
    config.type = chart.type.replace("odoo_", "");
    const legend = {
        ...config.options.legend,
        display: chart.legendPosition !== "none",
    };
    legend.position = chart.legendPosition;
    config.options.plugins = config.options.plugins || {};
    config.options.plugins.legend = legend;
    config.options.layout = {
        padding: { left: 20, right: 20, top: chart.title ? 10 : 25, bottom: 10 },
    };
    config.options.scales = {
        x: {
            ticks: {
                // x axis configuration
                maxRotation: 60,
                minRotation: 15,
                padding: 5,
                labelOffset: 2,
                color: fontColor,
            },
            title: getChartAxisTitleRuntime(chart.axesDesign?.x),
        },
        y: {
            position: chart.verticalAxisPosition,
            ticks: {
                color: fontColor,
                callback: (value) =>
                    formatValue(value, {
                        locale,
                        format: Math.abs(value) >= 1000 ? "#,##" : undefined,
                    }),
            },
            title: getChartAxisTitleRuntime(chart.axesDesign?.y),
        },
    };
    if (chart.stacked) {
        config.options.scales.y.stacked = true;
    }

    config.options.plugins.chartShowValuesPlugin = {
        showValues: chart.showValues,
        background: chart.background,
        callback: formatTickValue({ locale }),
    };
    return config;
>>>>>>> be776e735dd4a5db1090df66dea41876be431911
}
