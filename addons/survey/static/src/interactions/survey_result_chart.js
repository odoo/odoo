import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// The given colors are the same as those used by D3
const D3_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#aec7e8",
    "#ffbb78",
    "#2ca02c",
    "#98df8a",
    "#d62728",
    "#ff9896",
    "#9467bd",
    "#c5b0d5",
    "#8c564b",
    "#c49c94",
    "#e377c2",
    "#f7b6d2",
    "#7f7f7f",
    "#c7c7c7",
    "#bcbd22",
    "#dbdb8d",
    "#17becf",
    "#9edae5",
];

/**
 * Interaction responsible for the initialization and the drawing of the various charts.
 *
 */
export class SurveyResultChart extends Interaction {
    static selector = ".survey_graph";

    /**
     * Initializes the interaction based on its defined graph_type and loads the chart.
     *
     */
    start() {
        this.graphData = JSON.parse(this.el.dataset.graphData);
        this.rightAnswers = this.el.dataset.rightAnswers || [];
        if (this.graphData && this.graphData.length !== 0) {
            switch (this.el.dataset.graphType) {
                case "multi_bar":
                    this.chartConfig = this.getMultibarChartConfig();
                    break;
                case "bar":
                    this.chartConfig = this.getBarChartConfig();
                    break;
                case "pie":
                    this.chartConfig = this.getPieChartConfig();
                    break;
                case "doughnut":
                    this.chartConfig = this.getDoughnutChartConfig();
                    break;
                case "by_section":
                    this.chartConfig = this.getSectionResultsChartConfig();
                    break;
            }
            this.chart = this.loadChart();
            this.registerCleanup(() => this.chart?.destroy());
        }
    }

    async willStart() {
        await loadBundle("web.chartjs_lib");
    }

    /**
     * Returns a standard multi bar chart configuration.
     *
     */
    getMultibarChartConfig() {
        return {
            type: "bar",
            data: {
                labels: this.graphData[0].values.map(this.markIfCorrect, this),
                datasets: this.graphData.map(function (group, index) {
                    const data = group.values.map(function (value) {
                        return value.count;
                    });
                    return {
                        label: group.key,
                        data: data,
                        backgroundColor: D3_COLORS[index % 20],
                    };
                }),
            },
            options: {
                scales: {
                    x: {
                        ticks: {
                            callback: function (val, index) {
                                // For a category axis, the val is the index so the lookup via getLabelForValue is needed
                                const value = this.getLabelForValue(val);
                                const tickLimit = 25;
                                return value?.length > tickLimit
                                    ? `${value.slice(0, tickLimit)}...`
                                    : value;
                            },
                        },
                    },
                    y: {
                        ticks: {
                            precision: 0,
                        },
                        beginAtZero: true,
                    },
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: function (tooltipItem) {
                                return tooltipItem.label;
                            },
                        },
                    },
                },
            },
        };
    }

    /**
     * Returns a standard bar chart configuration.
     *
     */
    getBarChartConfig() {
        return {
            type: "bar",
            data: {
                labels: this.graphData[0].values.map(this.markIfCorrect, this),
                datasets: this.graphData.map(function (group) {
                    const data = group.values.map(function (value) {
                        return value.count;
                    });
                    return {
                        label: group.key,
                        data: data,
                        backgroundColor: data.map(function (val, index) {
                            return D3_COLORS[index % 20];
                        }),
                    };
                }),
            },
            options: {
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        enabled: false,
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            callback: function (val, index) {
                                // For a category axis, the val is the index so the lookup via getLabelForValue is needed
                                const value = this.getLabelForValue(val);
                                const tickLimit = 35;
                                return value?.length > tickLimit
                                    ? `${value.slice(0, tickLimit)}...`
                                    : value;
                            },
                        },
                    },
                    y: {
                        ticks: {
                            precision: 0,
                        },
                        beginAtZero: true,
                    },
                },
            },
        };
    }

    /**
     * Returns a standard pie chart configuration.
     *
     */
    getPieChartConfig() {
        const counts = this.graphData.map(function (point) {
            return point.count;
        });

        return {
            type: "pie",
            data: {
                labels: this.graphData.map(this.markIfCorrect, this),
                datasets: [
                    {
                        label: "",
                        data: counts,
                        backgroundColor: counts.map(function (val, index) {
                            return D3_COLORS[index % 20];
                        }),
                    },
                ],
            },
            options: {
                plugins: {
                    legend: {
                        labels: {
                            generateLabels: (chart) => this.generateShortLegendLabels(chart),
                        },
                    },
                    tooltip: {
                        callbacks: {
                            title: this.splitTooltipTitle,
                        },
                    },
                },
                aspectRatio: 2,
            },
        };
    }

    /**
     * Returns a standard doughnut chart configuration.
     *
     */
    getDoughnutChartConfig() {
        const totalsGraphData = this.graphData.totals;
        const counts = totalsGraphData.map(function (point) {
            return point.count;
        });

        return {
            type: "doughnut",
            data: {
                labels: totalsGraphData.map(this.markIfCorrect, this),
                datasets: [
                    {
                        label: "",
                        data: counts,
                        backgroundColor: counts.map(function (val, index) {
                            return D3_COLORS[index % 20];
                        }),
                        borderColor: "rgba(0, 0, 0, 0.1)",
                    },
                ],
            },
            options: {
                plugins: {
                    title: {
                        display: true,
                        text: _t("Overall Performance"),
                    },
                },
                aspectRatio: 2,
            },
        };
    }

    /**
     * Displays the survey results grouped by section.
     * For each section, user can see the percentage of answers
     * - Correct
     * - Partially correct (multiple choices and not all correct answers ticked)
     * - Incorrect
     * - Unanswered
     *
     * e.g:
     *
     * Mathematics:
     * - Correct 75%
     * - Incorrect 25%
     * - Partially correct 0%
     * - Unanswered 0%
     *
     * Geography:
     * - Correct 0%
     * - Incorrect 0%
     * - Partially correct 50%
     * - Unanswered 50%
     *
     */
    getSectionResultsChartConfig() {
        const sectionGraphData = this.graphData.by_section;

        const resultKeys = {
            correct: _t("Correct"),
            partial: _t("Partially"),
            incorrect: _t("Incorrect"),
            skipped: _t("Unanswered"),
        };
        let resultColorIndex = 0;
        const datasets = [];
        for (const resultKey in resultKeys) {
            const data = [];
            for (const section in sectionGraphData) {
                data.push(
                    (sectionGraphData[section][resultKey] /
                        sectionGraphData[section]["question_count"]) *
                        100
                );
            }
            datasets.push({
                label: resultKeys[resultKey],
                data: data,
                backgroundColor: D3_COLORS[resultColorIndex % 20],
            });
            resultColorIndex++;
        }

        return {
            type: "bar",
            data: {
                labels: Object.keys(sectionGraphData),
                datasets: datasets,
            },
            options: {
                plugins: {
                    title: {
                        display: true,
                        text: _t("Performance by Section"),
                    },
                    legend: {
                        display: true,
                    },
                    tooltip: {
                        callbacks: {
                            label: (tooltipItem) => {
                                const xLabel = tooltipItem.label;
                                const roundedValue = Math.round(tooltipItem.parsed.y * 100) / 100;
                                return `${xLabel}: ${roundedValue}%`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            callback: function (val, index) {
                                // For a category axis, the val is the index so the lookup via getLabelForValue is needed
                                const value = this.getLabelForValue(val);
                                const tickLimit = 20;
                                return value?.length > tickLimit
                                    ? `${value.slice(0, tickLimit)}...`
                                    : value;
                            },
                        },
                    },
                    y: {
                        gridLines: {
                            display: false,
                        },
                        ticks: {
                            precision: 0,
                            callback: function (label) {
                                return label + "%";
                            },
                            maxTicksLimit: 5,
                            stepSize: 25,
                        },
                        beginAtZero: true,
                        suggestedMin: 0,
                        suggestedMax: 100,
                    },
                },
            },
        };
    }

    /**
     * Adds a unicode 'check' mark if the answer's text is among the question's right answers.
     *
     * @param  value
     * @param  value.text The original text of the answer
     */
    markIfCorrect(value) {
        return value.text + (this.rightAnswers.indexOf(value.text) >= 0 ? " \u2713" : "");
    }

    /**
     * Returns the default pie chart legend items with a shortened text.
     *
     * @param {Chart} chart
     */
    generateShortLegendLabels(chart) {
        const legendItems = Chart.overrides.pie.plugins.legend.labels.generateLabels(chart);
        const labelLimit = 20;
        for (const item of legendItems) {
            const answerText = this.graphData[item.index].text;
            if (answerText.length > labelLimit) {
                item.text = `${answerText.slice(0, labelLimit)}…${item.text.slice(answerText.length)}`;
            }
        }
        return legendItems;
    }

    /**
     * Returns the tooltip title split into lines that fit in the chart width.
     *
     * @param {Object[]} tooltipItems
     */
    splitTooltipTitle(tooltipItems) {
        const { chart, label } = tooltipItems[0];
        const { titleFont, padding } = chart.tooltip.options;
        const maxWidth = chart.width - Chart.helpers.toPadding(padding).width;
        const ctx = chart.ctx;
        ctx.save();
        ctx.font = Chart.helpers.toFont(titleFont).string;
        const lines = [];
        let line = "";
        for (const word of label.split(" ")) {
            const lineWithWord = line ? `${line} ${word}` : word;
            if (ctx.measureText(lineWithWord).width <= maxWidth) {
                line = lineWithWord;
                continue;
            }
            if (line) {
                lines.push(line);
                line = "";
            }
            for (const char of word) {
                if (line && ctx.measureText(line + char).width > maxWidth) {
                    lines.push(line);
                    line = "";
                }
                line += char;
            }
        }
        lines.push(line);
        ctx.restore();
        return lines;
    }

    /**
     * Loads the chart using the provided Chart library.
     *
     */
    loadChart() {
        this.el.style.position = "relative";
        const canvas = this.el.querySelector("canvas");
        const ctx = canvas.getContext("2d");
        return new Chart(ctx, this.chartConfig);
    }
}

registry.category("public.interactions").add("survey.survey_result_chart", SurveyResultChart);
