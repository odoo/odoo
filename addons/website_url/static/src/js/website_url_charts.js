(function () {
   'use strict';

   var QWeb = openerp.qweb;

    openerp.website_url = {};
    
    openerp.website_url.BarChart = openerp.Widget.extend({
        init: function(element, begin_date, end_date, dates) {
            this.element = element;
            this.begin_date = begin_date;
            this.end_date = end_date;
            this.number_of_days = this.end_date.diff(this.begin_date, 'days') + 2;
            this.dates = dates;
        },
        start: function() {
            var self = this;

            function getDate(d) {
                return new Date(d[0])
            }

            var clicks_array = [];
            var begin_date_copy = this.begin_date;
            for(var i = 0 ; i < this.number_of_days ; i++) {

                var date_key = begin_date_copy.format('YYYY-MM-DD');
                clicks_array.push([date_key, (date_key in this.dates) ? this.dates[date_key] : 0]);
                begin_date_copy.add(1, 'days');
            }

            var chart_data = [{}];
                chart_data[0]['key'] = '# of clicks';
                chart_data[0]['values'] = clicks_array;

            var minDate = getDate(chart_data[0]['values'][0]),
                maxDate = getDate(chart_data[0]['values'][chart_data[0]['values'].length - 1]);

            nv.addGraph(function() {
                var chart = nv.models.lineChart()
                    .x(function(d) {
                        return getDate(d);
                    })
                    .y(function(d) { return d[1] })
                    .tooltips(true)
                    .transitionDuration(0)
                    .showYAxis(true)
                    .showXAxis(true)
                ;

                chart.xAxis.tickFormat(function(d) {
                    return moment(d).format('DD/MM/YYYY');
                });

                chart.yAxis
                        .tickFormat(d3.format("d"))
                        .ticks(chart_data[0]['values'].length - 1)

                d3.select(self.element)
                    .datum(chart_data)
                    .call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        },
    });

    openerp.website_url.PieChart = openerp.Widget.extend({
        init: function($element, data) {
            this.data = data;
            this.$element = $element;
        },
        start: function() {

            var self = this;

            var processed_data = [];
            for(var i = 0 ; i < this.data.length ; i++) {
                if(this.data[i]['name']) {
                    processed_data.push({'label':this.data[i]['name'] + ' (' + this.data[i]['count'] + ')',
                                                 'value':this.data[i]['count']});
                }
                else {
                    processed_data.push({'label':'Undefined (' + this.data[i]['count'] + ')',
                                                 'value':this.data[i]['count']});
                }
            }

            nv.addGraph(function() {
                var chart = nv.models.pieChart()
                    .x(function(d) { return d.label })
                    .y(function(d) { return d.value })
                    .showLabels(true);


                d3.select(self.$element)
                    .datum(processed_data)
                    .transition().duration(1200)
                    .call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        },
    });

   $(document).ready(function() {

        $(".graph-tabs li a").click(function (e) {
            e.preventDefault();
            $(this).tab('show');
            $(window).trigger('resize'); // Force NVD3 to redraw the chart
        });

        var code = $('#code').val();

        openerp.jsonRpc('/r/' + code + '/chart', 'call', {})
            .then(function(result) {

                // Sort data
                var total_clicks = result['total_clicks'];
                var clicks_by_day = result['clicks_by_day'];
                var clicks_by_country = result['clicks_by_country'];
                var last_month_clicks_by_country = result['last_month_clicks_by_country'];
                var last_week_clicks_by_country = result['last_week_clicks_by_country'];

                // Process dashboard data
                $('#total_clicks_data').html(total_clicks);
                $('#number_of_countries_data').html(clicks_by_country.length);

                if(total_clicks) {     

                    // Flat clicks by day data
                    var result_dic = {}
                    for(var i = 0 ; i < clicks_by_day.length ; i++) {
                        result_dic[clicks_by_day[i].to_char] = clicks_by_day[i].count;
                    }

                    // Process all time line chart data
                    var begin_date = moment(clicks_by_day[clicks_by_day.length - 1].to_char);
                    var end_date = moment(clicks_by_day[0].to_char);
                    var now = moment();

                    var all_time_chart = new openerp.website_url.BarChart('#all_time_clicks_chart svg', begin_date, end_date, result_dic);
                    all_time_chart.start();

                    // Process month line chart data
                    var begin_date = moment().subtract(30, 'days');
                    var month_chart = new openerp.website_url.BarChart('#last_month_clicks_chart svg', begin_date, now, result_dic);
                    month_chart.start();

                    // Process week line chart data
                    var begin_date = moment().subtract(7, 'days');
                    var week_chart = new openerp.website_url.BarChart('#last_week_clicks_chart svg', begin_date, now, result_dic);
                    week_chart.start();

                    // Process pie charts
                    var all_time_pie_chart = new openerp.website_url.PieChart('#all_time_countries_charts svg', clicks_by_country);
                    all_time_pie_chart.start();

                    var last_month_pie_chart = new openerp.website_url.PieChart('#last_month_countries_charts svg', last_month_clicks_by_country);
                    last_month_pie_chart.start();

                    var last_week_pie_chart = new openerp.website_url.PieChart('#last_week_countries_charts svg', last_week_clicks_by_country);
                    last_week_pie_chart.start();
                }
                else {
                    $('#all_time_clicks_chart').prepend('There is no data to show');
                    $('#all_time_countries_charts').prepend('There is no data to show');
                    $('#last_month_clicks_chart').prepend('There is no data to show');
                    $('#last_month_countries_charts').prepend('There is no data to show');
                    $('#last_week_clicks_chart').prepend('There is no data to show');
                    $('#last_week_countries_charts').prepend('There is no data to show');
                }
            });   
    });
})();