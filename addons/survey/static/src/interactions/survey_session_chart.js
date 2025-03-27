/* global ChartDataLabels */

import { loadJS } from "@web/core/assets";
import SESSION_CHART_COLORS from "@survey/interactions/survey_session_colors";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class SurveySessionChart extends Interaction {
    static selector = ".o_survey_session_chart";
    dynamicContent = {
        _root: {
            "t-on-updateState": this.updateState,
            "t-att-class": () => ({ chart_is_ready: !!this.chart }),
        },
    };
    setup() {
        const sessionManageEl = this.el.closest(".o_survey_session_manage");
        this.questionType = sessionManageEl.dataset.questionType;
        this.answersValidity = JSON.parse(sessionManageEl.dataset.answersValidity);
        this.hasCorrectAnswers = sessionManageEl.dataset.hasCorrectAnswers;
        this.questionStatistics = this.processQuestionStatistics(
            JSON.parse(sessionManageEl.dataset.questionStatistics)
        );
        this.showAnswers = false;
        this.showInputs = false;
    }

    async willStart() {
        await loadJS("/survey/static/src/js/libs/chartjs-plugin-datalabels.js");
    }

    start() {
        const canvas = this.el.querySelector("canvas");
        const ctx = canvas.getContext("2d");
        this.chart = new Chart(ctx, this.buildChartConfiguration());
        this.registerCleanup(() => this.chart.destroy());
        // survey_session_manage waits for us to start.
        // If we are ready before survey_session_manage, this is signaled
        // by the presence of the class `chart_is_ready` (see dynamicContent).
        // If survey_session_manage is ready before us, it will wait for this
        //  signal on the bus.
        this.env.bus.trigger("SURVEY:CHART_INTERACTION_STARTED");
    }

    /**
     * Update the chart state based on the CustomEvent received.
     * Possible options, passed in detail, are:
     * - showInputs: boolean, show the user inputs on the chart
     * - showAnswers: boolean, show the correct and incorrect answers on the chart
     * - questionStatistics: object, the statistics of the current question
     *
     * @param {CustomEvent} ev
     */
    updateState(ev) {
        if ("showInputs" in ev.detail) {
            this.showInputs = ev.detail.showInputs;
        }
        if ("showAnswers" in ev.detail) {
            this.showAnswers = ev.detail.showAnswers;
        }
        this.updateChart(ev.detail.questionStatistics);
    }

    /**
     * Updates the chart data using the latest received question user inputs.
     *
     * By updating the numbers in the dataset, we take advantage of the Chartjs API
     * that will automatically add animations to show the new number.
     *
     * @param {Object} questionStatistics object containing chart data (counts / labels / ...)
     */
    updateChart(questionStatistics) {
        if (questionStatistics) {
            this.questionStatistics = this.processQuestionStatistics(questionStatistics);
        }
        if (this.chart) {
            // only a single dataset for our bar charts
            const chartData = this.chart.data.datasets[0].data;
            for (let i = 0; i < chartData.length; i++) {
                const value = this.showInputs ? this.questionStatistics[i].count : 0;
                this.chart.data.datasets[0].data[i] = value;
            }
            this.chart.update();
        }
    }

    /**
     * Custom bar chart configuration for our survey session use case.
     *
     * Quick summary of enabled features:
     * - background_color is one of the 10 custom colors from SESSION_CHART_COLORS
     *   (see getBackgroundColor for details)
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
    buildChartConfiguration() {
        return {
            type: "bar",
            data: {
                labels: this.extractChartLabels(),
                datasets: [
                    {
                        backgroundColor: this.getBackgroundColor.bind(this),
                        data: this.extractChartData(),
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    datalabels: {
                        color: this.getLabelColor.bind(this),
                        font: {
                            size: "50",
                            weight: "bold",
                        },
                        anchor: "end",
                        align: "top",
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
                            display: false,
                        },
                    },
                    x: {
                        ticks: {
                            minRotation: 20,
                            maxRotation: 90,
                            font: {
                                size: "35",
                                weight: "bold",
                            },
                            color: "#212529",
                            autoSkip: false,
                        },
                        grid: {
                            drawOnChartArea: false,
                            color: "rgba(0, 0, 0, 0.2)",
                        },
                    },
                },
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        top: 70,
                        bottom: 0,
                    },
                },
            },
            plugins: [
                ChartDataLabels,
                {
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
                     * When the screen space is too small for long words, those long words are split over multiple rows.
                     * At 6 chars per row, the above example becomes ["this", "is an", "examp-", "le of", "a label"]
                     * Which is displayed as "this<br/>is an<br/>examp-<br/>le of<br/>a label"
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
                        // Between 1 and 2 -> 35, 3 and 4 -> 30, 5 and 6 -> 30, ...
                        const charPerLineBreakpoints = [
                            [1, 2, 35, minRatio],
                            [3, 4, 30, minRatio],
                            [5, 6, 30, 0.45],
                            [7, 8, 30, 0.65],
                            [9, null, 30, 0.7],
                        ];

                        let charPerLine;
                        let fontRatio;
                        charPerLineBreakpoints.forEach(([lowerBound, upperBound, value, ratio]) => {
                            if (
                                nbrCol >= lowerBound &&
                                (upperBound === null || nbrCol <= upperBound)
                            ) {
                                charPerLine = value;
                                fontRatio = ratio;
                            }
                        });

                        // Adapt font size if the number of characters per line is under the maximum
                        if (charPerLine < 35) {
                            const allWords = chart.data.labels.reduce((accumulator, words) =>
                                accumulator.concat(" ".concat(words))
                            );
                            const maxWordLength = Math.max(
                                ...allWords.split(" ").map((word) => word.length)
                            );
                            fontRatio = maxWordLength > charPerLine ? minRatio : fontRatio;
                            chart.options.scales.x.ticks.font.size = Math.min(
                                parseInt(chart.options.scales.x.ticks.font.size),
                                (chart.width * fontRatio) / nbrCol
                            );
                        }

                        chart.data.labels.forEach(function (label, index, labelsList) {
                            // Split all the words of the label
                            const words = label.split(" ");
                            const resultLines = [];
                            let currentLine = [];
                            for (let i = 0; i < words.length; i++) {
                                // Chop down words that do not fit on a single line, add each part on its own line.
                                let word = words[i];
                                while (word.length > charPerLine) {
                                    resultLines.push(word.slice(0, charPerLine - 1) + "-");
                                    word = word.slice(charPerLine - 1);
                                }
                                currentLine.push(word);

                                // Continue to add words in the line if there is enough space and if there is at least one more word to add
                                const nextWord = i + 1 < words.length ? words[i + 1] : null;
                                if (nextWord) {
                                    const nextLength =
                                        currentLine.join(" ").length + nextWord.length;
                                    if (nextLength <= charPerLine) {
                                        continue;
                                    }
                                }
                                // Add the constructed line and reset the variable for the next line
                                const newLabelLine = currentLine.join(" ");
                                resultLines.push(newLabelLine);
                                currentLine = [];
                            }
                            labelsList[index] = resultLines;
                        });
                    },
                },
            ],
        };
    }

    /**
     * Returns the label of the associated survey.question.answer.
     */
    extractChartLabels() {
        return this.questionStatistics.map((point) => point.text);
    }

    /**
     * We simply return an array of zeros as initial value.
     * The chart will update afterwards as attendees add their user inputs.
     */
    extractChartData() {
        return Array(this.questionStatistics.length).fill(0);
    }

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
     */
    getBackgroundColor(metaData) {
        const opacity =
            this.showAnswers && this.hasCorrectAnswers && !this.isValidAnswer(metaData.dataIndex)
                ? "0.2"
                : "0.8";
        // If metaData.dataIndex is greater than SESSION_CHART_COLORS.length, it should start from the beginning
        const rgb = SESSION_CHART_COLORS[metaData.dataIndex % SESSION_CHART_COLORS.length];
        return `rgba(${rgb},${opacity})`;
    }

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
     */
    getLabelColor(metaData) {
        let color = "#212529";
        if (this.showAnswers && this.hasCorrectAnswers) {
            color = this.isValidAnswer(metaData.dataIndex) ? "#2CBB70" : "#D9534F";
        }
        return color;
    }

    /**
     * Small helper method that returns the validity of the answer based on its index.
     *
     * We need this special handling because of Chartjs data structure.
     * The library determines the parameters (color/label/...) by only passing the answer 'index'
     * (and not the id or anything else we can identify).
     *
     * @param {Integer} answerIndex
     */
    isValidAnswer(answerIndex) {
        return this.answersValidity[answerIndex];
    }

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
     */
    processQuestionStatistics(rawStatistics) {
        if (["multiple_choice", "scale"].includes(this.questionType)) {
            return rawStatistics[0].values;
        }
        return rawStatistics;
    }
}

registry.category("public.interactions").add("survey.survey_session_chart", SurveySessionChart);
