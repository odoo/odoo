/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { SurveyImageZoomer } from "@survey/js/survey_image_zoomer";
import publicWidget from "@web/legacy/js/public/public_widget";

// The given colors are the same as those used by D3
var D3_COLORS = ["#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
                    "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
                    "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"];

// TODO awa: this widget loads all records and only hides some based on page
// -> this is ugly / not efficient, needs to be refactored
publicWidget.registry.SurveyResultPagination = publicWidget.Widget.extend({
    events: {
        'click li.o_survey_js_results_pagination a': '_onPageClick',
        "click .o_survey_question_answers_show_btn": "_onShowAllAnswers",
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {$.Element} params.questionsEl The element containing the actual questions
     *   to be able to hide / show them based on the page number
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.$questionsEl = params.questionsEl;
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.limit = self.$el.data("record_limit");
        });
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPageClick: function (ev) {
        ev.preventDefault();
        this.$('li.o_survey_js_results_pagination').removeClass('active');

        var $target = $(ev.currentTarget);
        $target.closest('li').addClass('active');
        this.$questionsEl.find("tbody tr").addClass("d-none");

        var num = $target.text();
        var min = this.limit * (num - 1) - 1;
        if (min === -1) {
            this.$questionsEl
                .find("tbody tr:lt(" + this.limit * num + ")")
                .removeClass("d-none");
        } else {
            this.$questionsEl
                .find("tbody tr:lt(" + this.limit * num + "):gt(" + min + ")")
                .removeClass("d-none");
        }
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onShowAllAnswers: function (ev) {
        const btnEl = ev.currentTarget;
        const pager = btnEl.previousElementSibling;
        btnEl.classList.add("d-none");
        this.$questionsEl.find("tbody tr").removeClass("d-none");
        pager.classList.add("d-none");
        this.$questionsEl.parent().addClass("h-auto");
    },
});

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
                window.addEventListener("afterprint", self._onAfterPrint.bind(self));
                window.addEventListener("beforeprint", self._onBeforePrint.bind(self));
                self.chart = self._loadChart();
            }
        });
    },

    willStart: async function () {
        await loadBundle("web.chartjs_lib");
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Prepare chart for media print
     * @private
     */
    _onBeforePrint: function () {
        const printWidth = 630; // Value to fit any graphic into the width of an A4 portrait page
        this.chart.resize(printWidth, Math.floor(printWidth / this.chart.aspectRatio));
    },

    /**
     * Turn back chart to original size, for media screen
     * @private
     */
    _onAfterPrint: function () {
        this.chart.resize();
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

publicWidget.registry.SurveyResultWidget = publicWidget.Widget.extend({
    selector: '.o_survey_result',
    events: {
        'click .o_survey_results_topbar_clear_filters': '_onClearFiltersClick',
        'click .filter-add-answer': '_onFilterAddAnswerClick',
        'click i.filter-remove-answer': '_onFilterRemoveAnswerClick',
        'click a.filter-finished-or-not': '_onFilterFinishedOrNotClick',
        'click a.filter-finished': '_onFilterFinishedClick',
        'click a.filter-failed': '_onFilterFailedClick',
        'click a.filter-passed': '_onFilterPassedClick',
        'click a.filter-passed-and-failed': '_onFilterPassedAndFailedClick',
        'click .o_survey_answer_image': '_onAnswerImgClick',
        "click .o_survey_results_print": "_onPrintResultsClick",
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var allPromises = [];
            self.$('.pagination_wrapper').each(function (){
                var questionId = $(this).data("question_id");
                allPromises.push(new publicWidget.registry.SurveyResultPagination(self, {
                    'questionsEl': self.$('#survey_table_question_'+ questionId)
                }).attachTo($(this)));
            });
            self.$('.survey_graph').each(function () {
                allPromises.push(new publicWidget.registry.SurveyResultChart(self)
                    .attachTo($(this)));
            });

            if (allPromises.length !== 0) {
                return Promise.all(allPromises);
            } else {
                return Promise.resolve();
            }
        });
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Add an answer filter by updating the URL and redirecting.
     * @private
     * @param {Event} ev
     */
    _onFilterAddAnswerClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.set('filters', this._prepareAnswersFilters(params.get('filters'), 'add', ev));
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * Remove an answer filter by updating the URL and redirecting.
     * @private
     * @param {Event} ev
     */
    _onFilterRemoveAnswerClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        let filters = this._prepareAnswersFilters(params.get('filters'), 'remove', ev);
        if (filters) {
            params.set('filters', filters);
        } else {
            params.delete('filters')
        }
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClearFiltersClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.delete('filters');
        params.delete('finished');
        params.delete('failed');
        params.delete('passed');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterFinishedOrNotClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.delete('finished');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterFinishedClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.set('finished', 'true');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterFailedClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.set('failed', 'true');
        params.delete('passed');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterPassedClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.set('passed', 'true');
        params.delete('failed');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterPassedAndFailedClick: function (ev) {
        let params = new URLSearchParams(window.location.search);
        params.delete('failed');
        params.delete('passed');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * Called when an image on an answer in multi-answers question is clicked.
     * Starts a widget opening a dialog to display the now zoomable image.
     * this.imgZoomer is the zoomer widget linked to the survey result widget, if any.
     *
     * @private
     * @param {Event} ev
     */
    _onAnswerImgClick: function (ev) {
        ev.preventDefault();
        new SurveyImageZoomer({
            sourceImage: $(ev.currentTarget).attr('src')
        }).appendTo(document.body);
    },

    /**
     * Call print dialog
     * @private
     */
    _onPrintResultsClick: function () {
        window.print();
    },

    /**
     * Returns the modified pathname string for filters after adding or removing an
     * answer filter (from click event).
     * @private
     * @param {String} filters Existing answer filters, formatted as
     * `modelX,rowX,ansX|modelY,rowY,ansY...` - row is used for matrix-type questions row id, 0 for others
     * "model" specifying the model to query depending on the question type we filter on.
       - 'A': 'survey.question.answer' ids: simple_choice, multiple_choice, matrix
       - 'L': 'survey.user_input.line' ids: char_box, text_box, numerical_box, date, datetime
     * @param {"add" | "remove"} operation Whether to add or remove the filter.
     * @param {Event} ev Event defining the filter.
     * @returns {String} Updated filters.
     */
    _prepareAnswersFilters(filters, operation, ev) {
        const cellDataset = ev.currentTarget.dataset;
        const filter = `${cellDataset.modelShortKey},${cellDataset.rowId || 0},${cellDataset.recordId}`;

        if (operation === 'add') {
            if (filters) {
                filters = !filters.split("|").includes(filter) ? filters += `|${filter}` : filters;
            } else {
                filters = filter;
            }
        } else if (operation === 'remove') {
            filters = filters
                .split("|")
                .filter(filterItem => filterItem !== filter)
                .join("|");
        } else {
            throw new Error('`operation` parameter for `_prepareAnswersFilters` must be either "add" or "remove".')
        }
        return filters;
    }
});

export default {
    resultWidget: publicWidget.registry.SurveyResultWidget,
    chartWidget: publicWidget.registry.SurveyResultChart,
    paginationWidget: publicWidget.registry.SurveyResultPagination
};
