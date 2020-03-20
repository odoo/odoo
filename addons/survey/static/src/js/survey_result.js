odoo.define('survey.result', function (require) {
'use strict';

require('web.dom_ready');
var _t = require('web.core')._t;

if(!$('.js_surveyresult').length) {
    return Promise.reject("DOM doesn't contain '.js_surveyresult'");
}

    // The given colors are the same as those used by D3
    var D3_COLORS = ["#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
                        "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
                        "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"];

    //Script For Pagination
    var survey_pagination = $('.pagination');
    $.each(survey_pagination, function(index, pagination){
        var question_id = $(pagination).attr("data-question_id");
        var limit = $(pagination).attr("data-record_limit"); //Number of Record Par Page. If you want to change number of record per page, change record_limit in pagination template.
        $('#table_question_'+ question_id +' tbody tr:lt('+limit+')').removeClass('d-none');
        $('#pagination_'+question_id+' li a').click(function(event){
            event.preventDefault();
            $('#pagination_'+question_id+' li').removeClass('active');
            $(this).parent('li').addClass('active');
            $('#table_question_'+ question_id +' tbody tr').addClass('d-none');
            var num = $(this).text();
            var min = (limit * (num-1))-1;
            if (min == -1){
                $('#table_question_'+ question_id +' tbody tr:lt('+ limit * num +')').removeClass('d-none');
            }
            else{
                $('#table_question_'+question_id+' tbody tr:lt('+ limit * num +'):gt('+min+')').removeClass('d-none');
            }
        });
        $('#pagination_'+question_id+' li:first').addClass('active').find('a').click();
    });

    // Custom Tick fuction for replacing long text with '...'
    var customtick_function = function (tick_limit) {
        return function(label) {
            if (label.length <= tick_limit) {
                return label;
            }
            else {
                return label.slice(0, tick_limit) + '...';
            }
        };
    };

    //initialize MultiBar Chart
    function init_multibar_chart (graph_data) {
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
                            callback: customtick_function(25),
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
    }

    //initialize discreteBar Chart
    function init_bar_chart(graph_data){
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
                            callback: customtick_function(35),
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
    }

    //initialize Pie Chart
    function init_pie_chart(graph_data){
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
    }

    //initialize doughnut Chart
    function init_doughnut_chart(graph_data, quizz_score){
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
    function load_chart(chartConfig, containerSelector){
        var $container = $(containerSelector).css({position: 'relative'});
        var $canvas = $container.find('canvas');
        var ctx = $canvas.get(0).getContext('2d');
        return new Chart(ctx, chartConfig);
    }

    //Script For Graph
    var survey_graphs = $('.survey_graph');
    $.each(survey_graphs, function(index, graph){
        var question_id = $(graph).attr("data-question_id");
        var graph_type = $(graph).attr("data-graph_type");
        var graph_data = JSON.parse($(graph).attr("graph-data"));
        var containerSelector = '#graph_question_' + question_id;
        var chartConfig;
        if(graph_type == 'multi_bar'){
            chartConfig = init_multibar_chart(graph_data);
            load_chart(chartConfig, containerSelector);
        }
        else if(graph_type == 'bar'){
            chartConfig = init_bar_chart(graph_data);
            load_chart(chartConfig, containerSelector);
        }
        else if(graph_type == 'pie'){
            chartConfig = init_pie_chart(graph_data);
            load_chart(chartConfig, containerSelector);
        }
        else if (graph_type === 'doughnut') {
            var quizz_score = $(graph).attr("quizz-score") || 0.0;
            chartConfig = init_doughnut_chart(graph_data, quizz_score);
            return load_chart(chartConfig, containerSelector);
        }
    });

    var $scoringResultsChart = $('#scoring_results_chart');
    if ($scoringResultsChart.length > 0) {
        var chartConfig = init_pie_chart($scoringResultsChart.data('graph_data'));
        load_chart(chartConfig, '#scoring_results_chart');
    }

    // Script for filter
    $('td.survey_answer').hover(function(){
        $(this).find('i.fa-filter').removeClass('invisible');
    }, function(){
        $(this).find('i.fa-filter').addClass('invisible');
    });
    $('td.survey_answer i.fa-filter').click(function(){
        var cell = $(this);
        var row_id = cell.attr('data-row_id') | 0;
        var answer_id = cell.attr('data-answer_id');
        if(document.URL.indexOf("?") == -1){
            window.location.href = document.URL + '?' + encodeURI(row_id + ',' + answer_id);
        }
        else {
            window.location.href = document.URL + '&' + encodeURI(row_id + ',' + answer_id);
        }
    });

    // for clear all filters
    $('.clear_survey_filter').click(function(){
        window.location.href = document.URL.substring(0,document.URL.indexOf("?"));
    });
    $('span.filter-all').click(function(){
        event.preventDefault();
        if(document.URL.indexOf("finished") != -1){
            window.location.href = document.URL.replace('?finished&','?').replace('&finished&','&').replace('?finished','').replace('&finished','');
        }
    }).hover(function(){
        if(document.URL.indexOf("finished") == -1){
            $(this)[0].style.cursor = 'default';
        }
    });
    // toggle finished/all surveys filter
    $('span.filter-finished').click(function(){
        event.preventDefault();
        if(document.URL.indexOf("?") == -1){
            window.location.href = document.URL + '?' + encodeURI('finished');
        }
        else if(document.URL.indexOf("finished") == -1){
            window.location.href = document.URL + '&' + encodeURI('finished');
        }
    }).hover(function(){
        if(document.URL.indexOf("finished") != -1){
            $(this)[0].style.cursor = 'default';
        }
    });

});
