odoo.define('survey.result', function (require) {
'use strict';

var _t = require('web.core')._t;
var ajax = require('web.ajax');
var publicWidget = require('web.public.widget');

// The given colors are the same as those used by D3
var D3_COLORS = ["#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
                    "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
                    "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"];

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
    start: function () {
        var superDef = this._super.apply(this, arguments);
        var self = this;

        //Script For Pagination
        var survey_pagination = $('.pagination');
        $.each(survey_pagination, function(index, pagination){
            var question_id = $(pagination).attr("data-question_id");
            var limit = $(pagination).attr("data-record_limit"); //Number of Record Par Page. If you want to change number of record per page, change record_limit in pagination template.
            self.$('#table_question_'+ question_id +' tbody tr:lt('+limit+')').removeClass('d-none');
            self.$('#pagination_'+question_id+' li a').click(function(event){
                event.preventDefault();
                self.$('#pagination_'+question_id+' li').removeClass('active');
                $(this).parent('li').addClass('active');
                self.$('#table_question_'+ question_id +' tbody tr').addClass('d-none');
                var num = $(this).text();
                var min = (limit * (num-1))-1;
                if (min === -1){
                    self.$('#table_question_'+ question_id +' tbody tr:lt('+ limit * num +')').removeClass('d-none');
                }
                else{
                    self.$('#table_question_'+question_id+' tbody tr:lt('+ limit * num +'):gt('+min+')').removeClass('d-none');
                }
            });
            self.$('#pagination_'+question_id+' li:first').addClass('active').find('a').click();
        });

        //Script For Graph
        var survey_graphs = self.$('.survey_graph');
        $.each(survey_graphs, function(index, graph){
            var question_id = $(graph).attr("data-question_id");
            var graph_type = $(graph).attr("data-graph_type");
            var graph_data = JSON.parse($(graph).attr("graph-data"));
            var containerSelector = '#graph_question_' + question_id;
            var chartConfig;
            if(graph_type === 'multi_bar'){
                chartConfig = self._initMultibarChart(graph_data);
                self._loadChart(chartConfig, containerSelector);
            }
            else if(graph_type === 'bar'){
                chartConfig = self._initBarChart(graph_data);
                self._loadChart(chartConfig, containerSelector);
            }
            else if(graph_type === 'pie'){
                chartConfig = self._initPieChart(graph_data);
                self._loadChart(chartConfig, containerSelector);
            }
            else if (graph_type === 'doughnut') {
                var quizz_score = $(graph).attr("quizz-score") || 0.0;
                chartConfig = init_doughnut_chart(graph_data, quizz_score);
                self._loadChart(chartConfig, containerSelector);
            }
        });

        var $scoringResultsChart = $('#scoring_results_chart');
        if ($scoringResultsChart.length > 0) {
            var chartConfig = self._initPieChart($scoringResultsChart.data('graph_data'));
            self._loadChart(chartConfig, '#scoring_results_chart');
        }

        return superDef;
    },

    // -------------------------------------------------------------------------
    // Private - Tools
    // -------------------------------------------------------------------------

    // Custom Tick fuction for replacing long text with '...'
    _customTick: function (tick_limit) {
        return function(label) {
            if (label.length <= tick_limit) {
                return label;
            }
            else {
                return label.slice(0, tick_limit) + '...';
            }
        };
    },

    //initialize MultiBar Chart
    _initMultibarChart: function (graph_data) {
        var chartConfig = {
            type: 'bar',
            data: {
                labels: graph_data[0].values.map(function (value) {
                    return value.text;
                }),
                datasets: graph_data.map(function (group, index) {
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
        return chartConfig;
    },

    //initialize discreteBar Chart
    _initBarChart: function (graph_data) {
        var chartConfig = {
            type: 'bar',
            data: {
                labels: graph_data[0].values.map(function (value) {
                    return value.text;
                }),
                datasets: graph_data.map(function (group) {
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
        return chartConfig;
    },

        //initialize Pie Chart
    _initPieChart: function (graph_data) {
        var data = graph_data.map(function (point) {
            return point.count;
        });
        var chartConfig = {
            type: 'pie',
            data: {
                labels: graph_data.map(function (point) {
                    return point.text;
                }),
                datasets: [{
                    label: '',
                    data: data,
                    backgroundColor: data.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                }]
            }
        };
        return chartConfig;
    },

    //initialize doughnut Chart
    _init_doughnut_chart: function (graph_data, quizz_score){
        var data = graph_data.map(function (point) {
            return point.count;
        });
        var chartConfig = {
            type: 'doughnut',
            data: {
                labels: graph_data.map(function (point) {
                    return point.text;
                }),
                datasets: [{
                    label: '',
                    data: data,
                    backgroundColor: data.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                title: {
                    display: true,
                    text: _.str.sprintf(_t("Overall Performance %.2f%s"), parseFloat(quizz_score), '%'),
                },
            }
        };
        return chartConfig;
    }

    //load chart to svg element chart:initialized chart, response:AJAX response, quistion_id:if of survey question, tick_limit:text length limit
    _loadChart: function (chartConfig, containerSelector) {
        var $container = this.$(containerSelector).css({position: 'relative'});
        var $canvas = $container.find('canvas');
        var ctx = $canvas.get(0).getContext('2d');
        return new Chart(ctx, chartConfig);
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

        var params = this._getQueryStringParams();
        var filters = params['filters'] ? params['filters'] + "|" + row_id + ',' + answer_id : row_id + ',' + answer_id
        params['filters'] = filters;

        window.location.href = window.location.pathname + '?' + this._toQueryString(params);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClearFilterClick: function (ev) {
        var params = this._getQueryStringParams();
        delete params['filters'];
        delete params['finished'];
        window.location.href = window.location.pathname + '?' + this._toQueryString(params);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterAllClick: function (ev) {
        var params = this._getQueryStringParams();
        delete params['finished'];
        window.location.href = window.location.pathname + '?' + this._toQueryString(params);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onFilterFinishedClick: function (ev) {
        var params = this._getQueryStringParams();
        params['finished'] = true;
        window.location.href = window.location.pathname + '?' + this._toQueryString(params);
    },

    // TODO DBE : Remove the two next functions in v13 and use URLSearchParams instead (see task id : 1985506)
    // as IE will not be supported anymore in v13.
    _getQueryStringParams: function () {
        var paramsDict = {};
        var params = window.location.search.split('?');
        if (params.length === 1) {
            return paramsDict;
        }
        params = params[1].split('&');
        params.forEach(function (param) {
            var paramKeyValue = param.split('=');
            paramsDict[paramKeyValue[0]] = paramKeyValue.length === 2 ? paramKeyValue[1] : null;
        });
        return paramsDict;
    },

    _toQueryString: function (paramsDict) {
        var queryString = "";
        _.each(paramsDict, function (value, key) {
            if (value) {
                queryString += key + '=' + value + '&';
            } else {
                queryString += key + '&';
            }
        });
        if (queryString.length > 0) {
            queryString = queryString.substring(0, queryString.length-1);
        }
        return queryString;
    },
});

return publicWidget.registry.SurveyResultWidget;

});
