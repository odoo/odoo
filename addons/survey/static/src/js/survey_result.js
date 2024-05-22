odoo.define('survey.result', function (require) {
'use strict';

var _t = require('web.core')._t;
var ajax = require('web.ajax');
var publicWidget = require('web.public.widget');

// The given colors are the same as those used by D3
var D3_COLORS = ["#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
                    "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
                    "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"];

// TODO awa: this widget loads all records and only hides some based on page
// -> this is ugly / not efficient, needs to be refactored
publicWidget.registry.SurveyResultPagination = publicWidget.Widget.extend({
    events: {
        'click li.o_survey_js_results_pagination a': '_onPageClick',
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
        this.$questionsEl.find('tbody tr').addClass('d-none');

        var num = $target.text();
        var min = (this.limit * (num-1))-1;
        if (min === -1){
            this.$questionsEl.find('tbody tr:lt('+ this.limit * num +')')
                .removeClass('d-none');
        } else {
            this.$questionsEl.find('tbody tr:lt('+ this.limit * num +'):gt(' + min + ')')
                .removeClass('d-none');
        }

    },
});

/**
 * Widget responsible for the initialization and the drawing of the various charts.
 *
 */
publicWidget.registry.SurveyResultChart = publicWidget.Widget.extend({
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],

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
                }

                self._loadChart();
            }
        });
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
                labels: this.graphData[0].values.map(function (value) {
                    return value.text;
                }),
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
                    xAxes: [{
                        ticks: {
                            callback: this._customTick(25),
                        },
                    }],
                    yAxes: [{
                        ticks: {
                            precision: 0,
                        },
                    }],
                },
                tooltips: {
                    callbacks: {
                        title: function (tooltipItem, data) {
                            return data.labels[tooltipItem[0].index];
                        }
                    }
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
                labels: this.graphData[0].values.map(function (value) {
                    return value.text;
                }),
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
                legend: {
                    display: false,
                },
                scales: {
                    xAxes: [{
                        ticks: {
                            callback: this._customTick(35),
                        },
                    }],
                    yAxes: [{
                        ticks: {
                                precision: 0,
                        },
                    }],
                },
                tooltips: {
                    enabled: false,
                }
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
                labels: this.graphData.map(function (point) {
                    return point.text;
                }),
                datasets: [{
                    label: '',
                    data: counts,
                    backgroundColor: counts.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                }]
            }
        };
    },

    _getDoughnutChartConfig: function () {
        var scoring_percentage = this.$el.data("scoring_percentage") || 0.0;
        var counts = this.graphData.map(function (point) {
            return point.count;
        });

        return {
            type: 'doughnut',
            data: {
                labels: this.graphData.map(function (point) {
                    return point.text;
                }),
                datasets: [{
                    label: '',
                    data: counts,
                    backgroundColor: counts.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                title: {
                    display: true,
                    text: _.str.sprintf(_t("Overall Performance %.2f%s"), parseFloat(scoring_percentage), '%'),
                },
            }
        };
    },

    /**
     * Custom Tick function to replace overflowing text with '...'
     *
     * @private
     * @param {Integer} tickLimit
     */
    _customTick: function (tickLimit) {
        return function (label) {
            if (label.length <= tickLimit) {
                return label;
            } else {
                return label.slice(0, tickLimit) + '...';
            }
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
    }
});

publicWidget.registry.SurveyResultWidget = publicWidget.Widget.extend({
    selector: '.o_survey_result',
    events: {
        'click td.survey_answer i.fa-filter': '_onSurveyAnswerFilterClick',
        'click .clear_survey_filter': '_onClearFilterClick',
        'click span.filter-all': '_onFilterAllClick',
        'click span.filter-finished': '_onFilterFinishedClick',
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    willStart: function () {
        var url = '/web/webclient/locale/' + (document.documentElement.getAttribute('lang') || 'en_US').replace('-', '_');
        var localeReady = ajax.loadJS(url);
        return Promise.all([this._super.apply(this, arguments), localeReady]);
    },

    /**
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var allPromises = [];

            self.$('.pagination').each(function (){
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
     * @private
     * @param {Event} ev
     */
    _onSurveyAnswerFilterClick: function (ev) {
        var cell = $(ev.target);
        var row_id = cell.data('row_id') | 0;
        var answer_id = cell.data('answer_id');

        var params = new URLSearchParams(window.location.search);
        var filters = params.get('filters') ? params.get('filters') + "|" + row_id + ',' + answer_id : row_id + ',' + answer_id;
        params.set('filters', filters);

        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClearFilterClick: function (ev) {
        var params = new URLSearchParams(window.location.search);
        params.delete('filters');
        params.delete('finished');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterAllClick: function (ev) {
        var params = new URLSearchParams(window.location.search);
        params.delete('finished');
        window.location.href = window.location.pathname + '?' + params.toString();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterFinishedClick: function (ev) {
        var params = new URLSearchParams(window.location.search);
        params.set('finished', true);
        window.location.href = window.location.pathname + '?' + params.toString();
    },
});

return {
    resultWidget: publicWidget.registry.SurveyResultWidget,
    chartWidget: publicWidget.registry.SurveyResultChart,
    paginationWidget: publicWidget.registry.SurveyResultPagination
};

});
