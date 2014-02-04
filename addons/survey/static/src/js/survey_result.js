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

/*
 * This file is intended to add interactivity to survey forms rendered by
 * the website engine.
 */

$(document).ready(function () {
    'use strict';
    console.debug("[survey] Survey Result JS is loading...");
    
    //Script For Pagination 
    var survey_pagination = $('.pagination');
    var limit = 5; //Number of Record Par Page. If you change value here, make change in pagination template also.
    $.each(survey_pagination, function(index, pagination){
        var question_id = $(pagination).attr("data-question_id");
        $('#table_question_'+ question_id +' tbody tr:lt('+limit+')').removeClass('hidden');
        $('#pagination_'+question_id+' li:first').addClass('active');
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
    });
    
    //initialize MultiBar Chart
    function init_multibar_chart(){
        var chart = nv.models.multiBarChart()
            .x(function(d) { return d.text })
            .y(function(d) { return d.count })
            .staggerLabels(true);

        // Replacing Library's Default Tooltip with our Custom One
        chart.tooltip(function(key, x, y, e, graph) {
            return '<h5 class="panel-primary"><div class="panel-heading">' + x + '</div></h5>' +
            '<p>'+ '<b>Responses : </b>' + key + '</p>' +
            '<p>' + "<b>Total Vote : </b>" + y + '</p>'  
        })
        return chart
    }
    
    //initialize discreteBar Chart
    function init_bar_chart(){
        return nv.models.discreteBarChart()
        .x(function(d) { return d.text })
        .y(function(d) { return d.count })
        .staggerLabels(true)
        .tooltips(false)
        .showValues(true)
    }
    
    //load chart to svg element chart:initialized chart, response:AJAX response, quistion_id:if of survey question, tick_limit:text length limit
    function load_chart(chart, response, question_id, tick_limit){
        // Custom Tick fuction for replacing long text with '...'
        var customtick_function = function(d){ 
            if(! this || d.length <= tick_limit){
                return d;
            } 
            else{
                return d.slice(0,tick_limit)+'...';
            }
        }
        chart.xAxis
            .tickFormat(customtick_function);
        chart.yAxis
            .tickFormat(d3.format('d'));

        d3.select('#graph_question_' + question_id + ' svg')
            .datum(response)
            .transition().duration(500).call(chart);
        nv.utils.windowResize(chart.update);
        return chart
    }
    //Script For Graph 
    var survey_graphs = $('.survey_graph');
    $.each(survey_graphs, function(index, graph){
        var question_id = $(graph).attr("data-question_id");
        var graph_type = $(graph).attr("data-graph_type");
        $.ajax({
            url: '/survey/results/graph/'+question_id,
            type: 'POST',
            dataType: 'json',
            success: function(response, status, xhr, wfe){ 
                if(graph_type == 'multi_bar'){
                    nv.addGraph(function(){
                        var chart = init_multibar_chart();
                        return load_chart(chart,response,question_id,25);
                    });
                }
                else if(graph_type == 'bar'){
                    nv.addGraph(function() {
                        var chart = init_bar_chart();
                        return load_chart(chart,response,question_id,35);
                    });
                }
            }
        });
    });
    
    console.debug("[survey] Survey Result JS loaded!");
});