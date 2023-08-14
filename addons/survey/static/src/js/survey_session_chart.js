/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import SESSION_CHART_COLORS from "@survey/js/survey_session_colors";

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
     * - We don't set a suggestedMin or Max so that Chart will adapt automatically based on the given data
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
                    },
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        enabled: false,
                    },
                },
                scales: {
                    y: {
                        ticks: {
                            display: false,
                        },
                        grid: {
                            display: false
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 0,
                            font: {
                                size :"35",
                                weight:"bold"
                            },
                            color : '#212529'
                        },
                        grid: {
                            drawOnChartArea: false,
                            color: 'rgba(0, 0, 0, 0.2)'
                        }
                    }
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
            plugins: [{
                /**
                 * The way it works is each label is an array of words.
                 * eg.: if we have a chart label: "this is an example of a label"
                 * The library will split it as: ["this is an example", "of a label"]
                 * Each value of the array represents a line of the label.
                 * So for this example above: it will be displayed as:
                 * "this is an examble<br/>of a label", breaking the label in 2 parts and put on 2 lines visually.
                 *
                 * What we do here is rework the labels with our own algorithm to make them fit better in screen space
                 * based on breakpoints based on number of columns to display.
                 * So this example will become: ["this is an", "example of", "a label"] if we have a lot of labels to put in the chart.
                 * Which will be displayed as "this is an<br/>example of<br/>a label"
                 * Obviously, the more labels you have, the more columns, and less screen space is available.
                 *
                 * We also adapt the font size based on the width available in the chart.
                 *
                 * So we counterbalance multiple times:
                 * - Based on number of columns (i.e. number of survey.question.answer of your current survey.question),
                 *   we split the words of every labels to make them display on more rows.
                 * - Based on the width of the chart (which is equivalent to screen width),
                 *   we reduce the chart font to be able to fit more characters.
                 * - Based on the longest word present in the labels, we apply a certain ratio with the width of the chart
                 *   to get a more accurate font size for the space available.
                 *
                 * @param {Object} chart
                 */
                beforeInit: function (chart) {
                    const nbrCol = chart.data.labels.length;
                    const minRatio = 0.4;
                    // Numbers of maximum characters per line to print based on the number of columns and default ratio for the font size
                    // Between 1 and 2 -> 25, 3 and 4 -> 20, 5 and 6 -> 15, ...
                    const charPerLineBreakpoints = [
                        [1, 2, 25, minRatio],
                        [3, 4, 20, minRatio],
                        [5, 6, 15, 0.45],
                        [7, 8, 10, 0.65],
                        [9, null, 7, 0.7],
                    ];

                    let charPerLine;
                    let fontRatio;
                    charPerLineBreakpoints.forEach(([lowerBound, upperBound, value, ratio]) => {
                        if (nbrCol >= lowerBound && (upperBound === null || nbrCol <= upperBound)) {
                            charPerLine = value;
                            fontRatio = ratio;
                        }
                    });

                    // Adapt font size if the number of characters per line is under the maximum
                    if (charPerLine < 25) {
                        const allWords = chart.data.labels.reduce((accumulator, words) => accumulator.concat(' '.concat(words)));
                        const maxWordLength = Math.max(...allWords.split(' ').map((word) => word.length));
                        fontRatio = maxWordLength > charPerLine ? minRatio : fontRatio;
                        chart.options.scales.x.ticks.font.size = Math.min(parseInt(chart.options.scales.x.ticks.font.size), chart.width * fontRatio / (nbrCol));
                    }

                    chart.data.labels.forEach(function (label, index, labelsList) {
                        // Split all the words of the label
                        const words = label.split(" ");
                        let resultLines = [];
                        let currentLine = [];
                        for (let i = 0; i < words.length; i++) {
                            // If the word we are adding exceed already the number of characters for the line, we add it anyway before passing to a new line
                            currentLine.push(words[i]);

                            // Continue to add words in the line if there is enough space and if there is at least one more word to add
                            const nextWord = i+1 < words.length ? words[i+1] : null;
                            if (nextWord) {
                                const nextLength = currentLine.join(' ').length + nextWord.length;
                                if (nextLength <= charPerLine) {
                                    continue;
                                }
                            }
                            // Add the constructed line and reset the variable for the next line
                            const newLabelLine = currentLine.join(' ');
                            resultLines.push(newLabelLine);
                            currentLine = [];
                        }
                        labelsList[index] = resultLines;
                    });
                },
            }],
        };
    },

    /**
     * Returns the label of the associated survey.question.answer.
     *
     * @private
     */
    _extractChartLabels: function () {
        return this.questionStatistics.map(function (point) {
            return point.text;
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

export default publicWidget.registry.SurveySessionChart;
