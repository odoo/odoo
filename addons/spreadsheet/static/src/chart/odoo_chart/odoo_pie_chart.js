import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";

const { chartRegistry } = spreadsheet.registries;
const { INTERACTIVE_LEGEND_CONFIG } = spreadsheet.constants;

const { getDefaultChartJsRuntime, chartFontColor, ColorGenerator, formatTickValue } =
    spreadsheet.helpers;

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
    const locale = getters.getLocale();
    const dataSetsLength = Math.max(0, ...datasets.map((ds) => ds?.data?.length ?? 0));
    const backgroundColors = getPieColors(new ColorGenerator(dataSetsLength), datasets);
    const chartJsConfig = getPieConfiguration(chart, labels, locale, backgroundColors);
    chartJsConfig.options = {
        ...chartJsConfig.options,
        ...getters.getChartDatasetActionCallbacks(chart),
    };
    for (const { label, data } of datasets) {
        const dataset = {
            label,
            data,
            borderColor: "#FFFFFF",
            backgroundColor: backgroundColors,
            hoverOffset: 30,
        };
        chartJsConfig.data.datasets.push(dataset);
    }
    return { background, chartJsConfig };
}

function getPieConfiguration(chart, labels, locale, colors) {
    const color = chartFontColor(chart.background);
    const config = getDefaultChartJsRuntime(chart, labels, color, { locale });
    config.type = chart.type.replace("odoo_", "");
    const legend = {
        ...config.options.legend,
        display: chart.legendPosition !== "none",
        ...INTERACTIVE_LEGEND_CONFIG,
        labels: {
            color,
            usePointStyle: true,
            generateLabels: (_chart) =>
                _chart.data.labels.map((label, index) => ({
                    text: label,
                    strokeStyle: colors[index],
                    fillStyle: colors[index],
                    pointStyle: "rect",
                    hidden: false,
                    lineWidth: 2,
                })),
        },
    };
    legend.position = chart.legendPosition;
    config.options.plugins = config.options.plugins || {};
    config.options.plugins.legend = legend;
    config.options.layout = {
        padding: { left: 20, right: 20, top: chart.title ? 10 : 25, bottom: 10 },
    };
    config.options.plugins.tooltip = {
        callbacks: {
            title: function (tooltipItem) {
                return tooltipItem.label;
            },
        },
    };

    config.options.plugins.chartShowValuesPlugin = {
        showValues: chart.showValues,
        callback: formatTickValue({ locale }),
    };
    return config;
}

function getPieColors(colors, dataSetsValues) {
    const pieColors = [];
    const maxLength = Math.max(...dataSetsValues.map((ds) => ds.data.length));
    for (let i = 0; i <= maxLength; i++) {
        pieColors.push(colors.next());
    }

    return pieColors;
}
