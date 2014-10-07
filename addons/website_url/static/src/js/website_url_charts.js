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

            var x = d3.time.scale().domain([minDate, maxDate]).range([0, 450]);

            nv.addGraph(function() {
                var chart = nv.models.multiBarChart()
                    .x(function(d) {
                        return x(getDate(d));
                    })
                    .y(function(d) { return d[1] })
                    .color(d3.scale.category10().range())
                    .tooltips(true)
                    .showControls(false)
                    .rotateLabels(45)
                    .transitionDuration(0)
                ;

                chart.xAxis.tickFormat(function(d) {
                    return moment(x.invert(d)).format('DD/MM/YYYY');
                });

                chart.yAxis
                    .tickFormat(d3.format(',i'));

                d3.select(self.element)
                    .datum(chart_data)
                    .call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        },
    });

   $(document).ready(function() {

        $(".graph-tabs a").click(function (e) {
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

                // Process dashboard data
                $('#total_clicks_data').html(total_clicks);
                $('#number_of_countries_data').html(clicks_by_country.length);

                // Flat clicks by day data
                var result_dic = {}
                for(var i = 0 ; i < clicks_by_day.length ; i++) {
                    result_dic[clicks_by_day[i].to_char] = clicks_by_day[i].count;
                }

                // Process all time data
                var begin_date = moment(clicks_by_day[clicks_by_day.length - 1].to_char);
                var end_date = moment(clicks_by_day[0].to_char);

                var all_time_chart = new openerp.website_url.BarChart('#all_time_chart svg', begin_date, end_date, result_dic);
                all_time_chart.start();

                // Process month data
                var begin_date = moment().subtract(30, 'days');

                var month_chart = new openerp.website_url.BarChart('#last_month_chart svg', begin_date, end_date, result_dic);
                month_chart.start();

                // Processus week data
                var begin_date = moment().subtract(7, 'days');

                var week_chart = new openerp.website_url.BarChart('#last_week_chart svg', begin_date, end_date, result_dic);
                week_chart.start();

                // Process country data
                var clicks_by_country_data = [];
                for(var i = 0 ; i < clicks_by_country.length ; i++) {

                    if(clicks_by_country[i]['name']) {
                        clicks_by_country_data.push({'label':clicks_by_country[i]['name'] + ' (' + clicks_by_country[i]['count'] + ')',
                                                     'value':clicks_by_country[i]['count']});
                    }
                    else {
                        clicks_by_country_data.push({'label':'Undefined (' + clicks_by_country[i]['count'] + ')',
                                                     'value':clicks_by_country[i]['count']});
                    }
                }

                // Country Chart
                nv.addGraph(function() {
                    var chart = nv.models.pieChart()
                        .x(function(d) { return d.label })
                        .y(function(d) { return d.value })
                        .showLabels(true);


                    d3.select("#clicks_by_country svg")
                        .datum(clicks_by_country_data)
                        .transition().duration(1200)
                        .call(chart);

                    nv.utils.windowResize(chart.update);

                    return chart;
                });
            });   
    });
})();