import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Widget responsible for the initialization and the drawing of the various charts.
 *
 */
publicWidget.registry.SurveyResultChart = publicWidget.Widget.extend({

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * Initializes the widget based on its defined graph_type and loads the chart.
     *
     * @override
     */
    start: function () {
        var self = this;

        return this._super.apply(this, arguments).then(function () {
            self.graphData = self.$el.data("graphData");
            self.rightAnswers = self.$el.data("rightAnswers") || [];

            if (self.graphData && self.graphData.length !== 0) {
                switch (self.$el.data("graphType")) {
                    case 'multi_bar':
                        self.chartConfig = self._getMultibarChartConfig();
                        break;
                    case 'bar':
                        self.chartConfig = self._getBarChartConfig();
                        break;
                    case 'pie':
                        self.chartConfig = self._getPieChartConfig();
                        break;
                    case 'doughnut':
                        self.chartConfig = self._getDoughnutChartConfig();
                        break;
                    case 'by_section':
                        self.chartConfig = self._getSectionResultsChartConfig();
                        break;
                }
                self.chart = self._loadChart();
            }
        });
    },

    willStart: async function () {
        await loadBundle("web.chartjs_lib");
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Returns a standard multi bar chart configuration.
     *
     * @private
     */
    _getMultibarChartConfig: function () {
        return {
            type: 'bar',
            data: {
                labels: this.graphData[0].values.map(this._markIfCorrect, this),
                datasets: this.graphData.map(function (group, index) {
                    var data = group.values.map(function (value) {
                        return value.count;
                    });
                    return {
                        label: group.key,
                        data: data,
                        backgroundColor: D3_COLORS[index % 20],
                    };
                })
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
    },

    /**
     * Returns a standard bar chart configuration.
     *
     * @private
     */
    _getBarChartConfig: function () {
        return {
            type: 'bar',
            data: {
                labels: this.graphData[0].values.map(this._markIfCorrect, this),
                datasets: this.graphData.map(function (group) {
                    var data = group.values.map(function (value) {
                        return value.count;
                    });
                    return {
                        label: group.key,
                        data: data,
                        backgroundColor: data.map(function (val, index) {
                            return D3_COLORS[index % 20];
                        }),
                    };
                })
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
    },

    /**
     * Returns a standard pie chart configuration.
     *
     * @private
     */
    _getPieChartConfig: function () {
        var counts = this.graphData.map(function (point) {
            return point.count;
        });

        return {
            type: 'pie',
            data: {
                labels: this.graphData.map(this._markIfCorrect, this),
                datasets: [{
                    label: '',
                    data: counts,
                    backgroundColor: counts.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                aspectRatio: 2,
            },
        };
    },

    _getDoughnutChartConfig: function () {
        var totalsGraphData = this.graphData.totals;
        var counts = totalsGraphData.map(function (point) {
            return point.count;
        });

        return {
            type: 'doughnut',
            data: {
                labels: totalsGraphData.map(this._markIfCorrect, this),
                datasets: [{
                    label: '',
                    data: counts,
                    backgroundColor: counts.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                    borderColor: 'rgba(0, 0, 0, 0.1)'
                }]
            },
            options: {
                plugins: {
                    title: {
                        display: true,
                        text: _t("Overall Performance"),
                    },
                },
                aspectRatio: 2,
            }
        };
    },

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
     *
     * @private
     */
    _getSectionResultsChartConfig: function () {
        var sectionGraphData = this.graphData.by_section;

        var resultKeys = {
            'correct': _t('Correct'),
            'partial': _t('Partially'),
            'incorrect': _t('Incorrect'),
            'skipped': _t('Unanswered'),
        };
        var resultColorIndex = 0;
        var datasets = [];
        for (var resultKey in resultKeys) {
            var data = [];
            for (var section in sectionGraphData) {
                data.push((sectionGraphData[section][resultKey]) / sectionGraphData[section]['question_count'] * 100);
            }
            datasets.push({
                label: resultKeys[resultKey],
                data: data,
                backgroundColor: D3_COLORS[resultColorIndex % 20],
            });
            resultColorIndex++;
        }

        return {
            type: 'bar',
            data: {
                labels: Object.keys(sectionGraphData),
                datasets: datasets
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
                                var roundedValue = Math.round(tooltipItem.parsed.y * 100) / 100;
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
                                return label + '%';
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
    },

    /**
     * Loads the chart using the provided Chart library.
     *
     * @private
     */
    _loadChart: function () {
        this.$el.css({position: 'relative'});
        var $canvas = this.$('canvas');
        var ctx = $canvas.get(0).getContext('2d');
        return new Chart(ctx, this.chartConfig);
    },

    /**
     * Adds a unicode 'check' mark if the answer's text is among the question's right answers.
     * @private
     * @param  {Object} value
     * @param  {String} value.text The original text of the answer
     */
    _markIfCorrect: function (value) {
        return `${value.text}${this.rightAnswers.indexOf(value.text) >= 0 ? " \u2713": ''}`;
    },

});

export default {
    chartWidget: publicWidget.registry.SurveyResultChart,
};
