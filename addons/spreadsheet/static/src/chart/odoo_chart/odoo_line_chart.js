/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = spreadsheet.registries;

const {
    getDefaultChartJsRuntime,
    getChartAxisTitleRuntime,
    chartFontColor,
    ColorGenerator,
    getFillingMode,
    colorToRGBA,
    rgbaToHex,
    getTrendDatasetForLineChart,
    getChartAxisType,
    formatValue,
    formatTickValue,
} = spreadsheet.helpers;

const { TREND_LINE_XAXIS_ID } = spreadsheet.constants;

const LINE_FILL_TRANSPARENCY = 0.4;

export class OdooLineChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.verticalAxisPosition = definition.verticalAxisPosition;
        this.stacked = definition.stacked;
        this.cumulative = definition.cumulative;
        this.axesDesign = definition.axesDesign;
        this.fillArea = definition.fillArea;
        this.trend = definition.trend;
        this.cumulatedStart = definition.cumulatedStart;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            verticalAxisPosition: this.verticalAxisPosition,
            stacked: this.stacked,
            cumulative: this.cumulative,
            axesDesign: this.axesDesign,
            fillArea: this.fillArea,
            trend: this.trend,
            cumulatedStart: this.cumulatedStart,
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
    const { datasets, labels } = chart.dataSource.getData();
    const locale = getters.getLocale();
    const chartJsConfig = getLineConfiguration(chart, labels, locale);
    chartJsConfig.options = {
        ...chartJsConfig.options,
        ...getters.getChartDatasetActionCallbacks(chart),
    };
    const colors = new ColorGenerator(datasets.length);

    let maxLength = 0;
    const trendDatasets = [];
    const axisType = getChartAxisType(chart, getters);

    for (const index in datasets) {
        let { label, data, cumulatedStart } = datasets[index];

        const color = colors.next();
        let backgroundColor = color;
        if (chart.fillArea) {
            const backgroundRGBA = colorToRGBA(color);
            // use the transparency of Odoo to keep consistency
            backgroundRGBA.a = LINE_FILL_TRANSPARENCY;
            backgroundColor = rgbaToHex(backgroundRGBA);
        }
        if (chart.cumulative) {
            let accumulator = cumulatedStart;
            data = data.map((value) => {
                accumulator += value;
                return accumulator;
            });
        }

        const dataset = {
            label,
            data,
            lineTension: 0,
            borderColor: color,
            backgroundColor,
            pointBackgroundColor: color,
            fill: chart.fillArea ? getFillingMode(parseInt(index), chart.stacked) : false,
        };
        chartJsConfig.data.datasets.push(dataset);

        const trend = chart.getDefinition().trend;
        if (!trend?.display) {
            continue;
        }

        const trendDataset = getTrendDatasetForLineChart(trend, dataset, axisType, locale);
        if (trendDataset) {
            maxLength = Math.max(maxLength, trendDataset.data.length);
            trendDatasets.push(trendDataset);
        }
    }

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
}
