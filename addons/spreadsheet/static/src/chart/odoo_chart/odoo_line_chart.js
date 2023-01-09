/** @odoo-module */

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { _t } from "@web/core/l10n/translation";
import { OdooChart } from "./odoo_chart";
import { LINE_FILL_TRANSPARENCY } from "@web/views/graph/graph_renderer";

const { chartRegistry } = spreadsheet.registries;

const {
    getDefaultChartJsRuntime,
    chartFontColor,
    ChartColors,
    getFillingMode,
    colorToRGBA,
    rgbaToHex,
} = spreadsheet.helpers;

export class OdooLineChart extends OdooChart {
    constructor(definition, sheetId, getters) {
        super(definition, sheetId, getters);
        this.verticalAxisPosition = definition.verticalAxisPosition;
        this.stacked = definition.stacked;
    }

    getDefinition() {
        return {
            ...super.getDefinition(),
            verticalAxisPosition: this.verticalAxisPosition,
            stacked: this.stacked,
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
    const chartJsConfig = getLineConfiguration(chart, labels);
    const colors = new ChartColors();
    for (const [index, { label, data }] of datasets.entries()) {
        const color = colors.next();
        const backgroundRGBA = colorToRGBA(color);
        if (chart.stacked) {
            // use the transparency of Odoo to keep consistency
            backgroundRGBA.a = LINE_FILL_TRANSPARENCY;
        }
        const backgroundColor = rgbaToHex(backgroundRGBA);
        const dataset = {
            label,
            data,
            lineTension: 0,
            borderColor: color,
            backgroundColor,
            pointBackgroundColor: color,
            fill: chart.stacked ? getFillingMode(index) : false,
        };
        chartJsConfig.data.datasets.push(dataset);
    }
    return { background, chartJsConfig };
}

function getLineConfiguration(chart, labels) {
    const fontColor = chartFontColor(chart.background);
    const config = getDefaultChartJsRuntime(chart, labels, fontColor);
    config.type = chart.type.replace("odoo_", "");
    const legend = {
        ...config.options.legend,
        display: chart.legendPosition !== "none",
        labels: {
            fontColor,
            generateLabels(chart) {
                const { data } = chart;
                const labels = window.Chart.defaults.global.legend.labels.generateLabels(chart);
                for (const [index, label] of labels.entries()) {
                    label.fillStyle = data.datasets[index].borderColor;
                }
                return labels;
            },
        },
    };
    legend.position = chart.legendPosition;
    config.options.legend = legend;
    config.options.layout = {
        padding: { left: 20, right: 20, top: chart.title ? 10 : 25, bottom: 10 },
    };
    config.options.scales = {
        xAxes: [
            {
                ticks: {
                    // x axis configuration
                    maxRotation: 60,
                    minRotation: 15,
                    padding: 5,
                    labelOffset: 2,
                    fontColor,
                },
            },
        ],
        yAxes: [
            {
                position: chart.verticalAxisPosition,
                ticks: {
                    fontColor,
                    // y axis configuration
                    beginAtZero: true, // the origin of the y axis is always zero
                },
            },
        ],
    };
    if (chart.stacked) {
        config.options.scales.yAxes[0].stacked = true;
    }
    return config;
}
