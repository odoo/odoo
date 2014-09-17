/*
 *    OpenERP, Open Source Management Solution
 *    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
 *
 *    This program is free software: you can redistribute it and/or modify
 *    it under the terms of the GNU Affero General Public License as
 *    published by the Free Software Foundation, either version 3 of the
 *    License, or (at your option) any later version.
 *
 *    This program is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU Affero General Public License for more details.
 *
 *    You should have received a copy of the GNU Affero General Public License
 *    along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

$(document).ready(function () {
    'use strict';
    console.debug("[survey] Survey Result JS is loading...");

    //Script For Pagination
    var survey_pagination = $('.pagination');
    $.each(survey_pagination, function(index, pagination){
        var question_id = $(pagination).attr("data-question_id");
        var limit = $(pagination).attr("data-record_limit"); //Number of Record Par Page. If you want to change number of record per page, change record_limit in pagination template.
        $('#table_question_'+ question_id +' tbody tr:lt('+limit+')').removeClass('hidden');
        $('#pagination_'+question_id+' li a').click(function(event){
            event.preventDefault();
            $('#pagination_'+question_id+' li').removeClass('active');
            $(this).parent('li').addClass('active');
            $('#table_question_'+ question_id +' tbody tr').addClass('hidden');
            var num = $(this).text();
            var min = (limit * (num-1))-1;
            if (min == -1){
                $('#table_question_'+ question_id +' tbody tr:lt('+ limit * num +')').removeClass('hidden');
            }
            else{
                $('#table_question_'+question_id+' tbody tr:lt('+ limit * num +'):gt('+min+')').removeClass('hidden');
            }
        });
        $('#pagination_'+question_id+' li:first').addClass('active').find('a').click();
    });

    //initialize MultiBar Chart
    function init_multibar_chart(){
        var chart = nv.models.multiBarChart()
            .x(function(d) { return d.text; })
            .y(function(d) { return d.count; })
            .staggerLabels(true);

        // Replacing Library's Default Tooltip with our Custom One
        chart.tooltip(function(key, x, y, e, graph) {
            return '<h5 class="panel-primary"><div class="panel-heading">' + x + '</div></h5>' +
            '<p>' + '<b>Responses : </b>' + key + '</p>' +
            '<p>' + "<b>Total Vote : </b>" + y + '</p>';
        });
        return chart;
    }

    //initialize discreteBar Chart
    function init_bar_chart(){
        return nv.models.discreteBarChart()
            .x(function(d) { return d.text; })
            .y(function(d) { return d.count; })
            .staggerLabels(true)
            .tooltips(false)
            .showValues(true);
    }

    //initialize Pie Chart
    function init_pie_chart(){
        return nv.models.pieChart()
            .x(function(d) { return d.text; })
            .y(function(d) { return d.count; })
            .showLabels(false);
    }

    //load chart to svg element chart:initialized chart, response:AJAX response, quistion_id:if of survey question, tick_limit:text length limit
    function load_chart(chart, response, question_id, tick_limit, graph_type){
        // Custom Tick fuction for replacing long text with '...'
        var customtick_function = function(d){
            if(! this || d.length <= tick_limit){
                return d;
            }
            else{
                return d.slice(0,tick_limit) + '...';
            }
        };
        if (graph_type != 'pie'){
            chart.xAxis
                .tickFormat(customtick_function);
            chart.yAxis
                .tickFormat(d3.format('d'));
        }
        d3.select('#graph_question_' + question_id + ' svg')
            .datum(response)
            .transition().duration(500).call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    }
    //Script For Graph
    var survey_graphs = $('.survey_graph');
    $.each(survey_graphs, function(index, graph){
        var question_id = $(graph).attr("data-question_id");
        var graph_type = $(graph).attr("data-graph_type");
        var graph_data = JSON.parse($(graph).attr("graph-data"));
        if(graph_type == 'multi_bar'){
            nv.addGraph(function(){
                var chart = init_multibar_chart();
                return load_chart(chart, graph_data, question_id, 25);
            });
        }
        else if(graph_type == 'bar'){
            nv.addGraph(function() {
                var chart = init_bar_chart();
                return load_chart(chart, graph_data, question_id, 35);
            });
        }
        else if(graph_type == 'pie'){
            nv.addGraph(function() {
                var chart = init_pie_chart();
                return load_chart(chart, graph_data, question_id, 25, 'pie');
            });
        }
    });

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

    console.debug("[survey] Survey Result JS loaded!");
});