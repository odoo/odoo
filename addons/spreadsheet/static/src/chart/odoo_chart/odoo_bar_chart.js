/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = spreadsheet.registries;

const {
    getDefaultChartJsRuntime,
    getAxesDesignWithValidRanges,
    getAxesDesignWithRangeString,
    getChartAxisTitleRuntime,
    chartFontColor,
    ColorGenerator,
} = spreadsheet.helpers;

export class OdooBarChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.verticalAxisPosition = definition.verticalAxisPosition;
        this.stacked = definition.stacked;
        this.axesDesign = getAxesDesignWithValidRanges(getters, sheetId, definition.axesDesign);
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            verticalAxisPosition: this.verticalAxisPosition,
            stacked: this.stacked,
            axesDesign: getAxesDesignWithRangeString(this.getters, this.sheetId, this.axesDesign),
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
    const locale = getters.getLocale();
    const chartJsConfig = getBarConfiguration(chart, getters, labels, locale);
    chartJsConfig.options = {
        ...chartJsConfig.options,
        ...getters.getChartDatasetActionCallbacks(chart),
    };
    const colors = new ColorGenerator(datasets.length);
    for (const { label, data } of datasets) {
        const color = colors.next();
        const dataset = {
            label,
            data,
            borderColor: "#FFFFFF",
            borderWidth: 1,
            backgroundColor: color,
        };
        chartJsConfig.data.datasets.push(dataset);
    }
    return { background, chartJsConfig };
}

function getBarConfiguration(chart, getters, labels, locale) {
    const color = chartFontColor(chart.background);
    const config = getDefaultChartJsRuntime(chart, getters, labels, color, { locale });
    config.type = chart.type.replace("odoo_", "");
    const legend = {
        ...config.options.legend,
        display: chart.legendPosition !== "none",
        labels: { color },
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
                color,
            },
            title: getChartAxisTitleRuntime(getters, chart.axesDesign?.x),
        },
        y: {
            position: chart.verticalAxisPosition,
            ticks: { color },
            beginAtZero: true, // the origin of the y axis is always zero
            title: getChartAxisTitleRuntime(getters, chart.axesDesign?.y),
        },
    };
    if (chart.stacked) {
        config.options.scales.x.stacked = true;
        config.options.scales.y.stacked = true;
    }
    return config;
}
