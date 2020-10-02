odoo.define('survey.session_chart', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var SESSION_CHART_COLORS = require('survey.session_colors');

publicWidget.registry.SurveySessionChart = publicWidget.Widget.extend({
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.questionType = options.questionType;
        this.answersValidity = options.answersValidity;
        this.hasCorrectAnswers = options.hasCorrectAnswers;
        this.questionStatistics = this._processQuestionStatistics(options.questionStatistics);
        this.showInputs = options.showInputs;
        this.showAnswers = false;
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._setupChart();
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the chart data using the latest received question user inputs.
     *
     * By updating the numbers in the dataset, we take advantage of the Chartjs API
     * that will automatically add animations to show the new number.
     *
     * @param {Object} questionStatistics object containing chart data (counts / labels / ...)
     * @param {Integer} newAttendeesCount: max height of chart, not used anymore (deprecated)
     */
    updateChart: function (questionStatistics, newAttendeesCount) {
        if (questionStatistics) {
            this.questionStatistics = this._processQuestionStatistics(questionStatistics);
        }

        if (this.chart) {
            // only a single dataset for our bar charts
            var chartData = this.chart.data.datasets[0].data;
            for (var i = 0; i < chartData.length; i++){
                var value = 0;
                if (this.showInputs) {
                    value = this.questionStatistics[i].count;
                }
                this.chart.data.datasets[0].data[i] = value;
            }

            this.chart.update();
        }
    },

    /**
     * Toggling this parameter will display or hide the correct and incorrect answers of the current
     * question directly on the chart.
     *
     * @param {Boolean} showAnswers
     */
    setShowAnswers: function (showAnswers) {
        this.showAnswers = showAnswers;
    },

    /**
     * Toggling this parameter will display or hide the user inputs of the current question directly
     * on the chart.
     *
     * @param {Boolean} showInputs
     */
    setShowInputs: function (showInputs) {
        this.showInputs = showInputs;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _setupChart: function () {
        var $canvas = this.$('canvas');
        var ctx = $canvas.get(0).getContext('2d');

        this.chart = new Chart(ctx, this._buildChartConfiguration());
    },

    /**
     * Custom bar chart configuration for our survey session use case.
     *
     * Quick summary of enabled features:
     * - background_color is one of the 10 custom colors from SESSION_CHART_COLORS
     *   (see _getBackgroundColor for details)
     * - The ticks are bigger and bolded to be able to see them better on a big screen (projector)
     * - We don't use tooltips to keep it as simple as possible
     * - We don't set a suggestedMin or Max so that Chart will adapt automatically himself based on the given data
     *   The '+1' part is a small trick to avoid the datalabels to be clipped in height
     * - We use a custom 'datalabels' plugin to be able to display the number value on top of the
     *   associated bar of the chart.
     *   This allows the host to discuss results with attendees in a more interactive way.
     *
     * @private
     */
    _buildChartConfiguration: function () {
        return {
            type: 'bar',
            data: {
                labels: this._extractChartLabels(),
                datasets: [{
                    backgroundColor: this._getBackgroundColor.bind(this),
                    data: this._extractChartData(),
                }]
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    datalabels: {
                        color: this._getLabelColor.bind(this),
                        font: {
                            size: '50',
                            weight: 'bold',
                        },
                        anchor: 'end',
                        align: 'top',
                    }
                },
                legend: {
                    display: false,
                },
                scales: {
                    yAxes: [{
                        ticks: {
                            display: false,
                        },
                        gridLines: {
                            display: false
                        }
                    }],
                    xAxes: [{
                        ticks: {
                            maxRotation: 0,
                            fontSize: '35',
                            fontStyle: 'bold',
                            fontColor: '#212529'
                        },
                        gridLines: {
                            drawOnChartArea: false,
                            color: 'rgba(0, 0, 0, 0.2)'
                        }
                    }]
                },
                tooltips: {
                    enabled: false,
                },
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        top: 70,
                        bottom: 0
                    }
                }
            },
        };
    },

    /**
     * Returns the label of the associated survey.question.answer.
     *
     * @private
     */
    _extractChartLabels: function () {
        return this.questionStatistics.map(function (point) {
            return point.text.length > 20 ? point.text.substring(0, 17) + '...' : point.text;
        });
    },

    /**
     * We simply return an array of zeros as initial value.
     * The chart will update afterwards as attendees add their user inputs.
     *
     * @private
     */
    _extractChartData: function () {
        return this.questionStatistics.map(function () {
            return 0;
        });
    },

    /**
     * Custom method that returns a color from SESSION_CHART_COLORS.
     * It loops through the ten values and assign them sequentially.
     *
     * We have a special mechanic when the host shows the answers of a question.
     * Wrong answers are "faded out" using a 0.3 opacity.
     *
     * @param {Object} metaData
     * @param {Integer} metaData.dataIndex the index of the label, matching the index of the answer
     *   in 'this.answersValidity'
     * @private
     */
    _getBackgroundColor: function (metaData) {
        var opacity = '0.8';
        if (this.showAnswers && this.hasCorrectAnswers) {
            if (!this._isValidAnswer(metaData.dataIndex)){
                opacity = '0.2';
            }
        }
        var rgb = SESSION_CHART_COLORS[metaData.dataIndex];
        return `rgba(${rgb},${opacity})`;
    },

    /**
     * Custom method that returns the survey.question.answer label color.
     *
     * Break-down of use cases:
     * - Red if the host is showing answer, and the associated answer is not correct
     * - Green if the host is showing answer, and the associated answer is correct
     * - Black in all other cases
     *
     * @param {Object} metaData
     * @param {Integer} metaData.dataIndex the index of the label, matching the index of the answer
     *   in 'this.answersValidity'
     * @private
     */
    _getLabelColor: function (metaData) {
        if (this.showAnswers && this.hasCorrectAnswers) {
            if (this._isValidAnswer(metaData.dataIndex)){
                return '#2CBB70';
            } else {
                return '#D9534F';
            }
        }
        return '#212529';
    },

    /**
     * Small helper method that returns the validity of the answer based on its index.
     *
     * We need this special handling because of Chartjs data structure.
     * The library determines the parameters (color/label/...) by only passing the answer 'index'
     * (and not the id or anything else we can identify).
     *
     * @param {Integer} answerIndex
     * @private
     */
    _isValidAnswer: function (answerIndex) {
        return this.answersValidity[answerIndex];
    },

    /**
     * Special utility method that will process the statistics we receive from the
     * survey.question#_prepare_statistics method.
     *
     * For multiple choice questions, the values we need are stored in a different place.
     * We simply return the values to make the use of the statistics common for both simple and
     * multiple choice questions.
     *
     * See survey.question#_get_stats_data for more details
     *
     * @param {Object} rawStatistics
     * @private
     */
    _processQuestionStatistics: function (rawStatistics) {
        if (this.questionType === 'multiple_choice') {
            return rawStatistics[0].values;
        }

        return rawStatistics;
    }
});

return publicWidget.registry.SurveySessionChart;

});
