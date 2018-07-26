odoo.define('website_links.charts', function (require) {
'use strict';

var Widget = require('web.Widget');
var base = require('web_editor.base');
var website = require('website.website');
var Model = require('web.Model');

var exports = {};

if(!$('.o_website_links_chart').length) {
    return $.Deferred().reject("DOM doesn't contain '.o_website_links_chart'");
}

    var BarChart = Widget.extend({
        init: function($element, begin_date, end_date, dates) {
            this.$element = $element;
            this.begin_date = begin_date;
            this.end_date = end_date;
            this.number_of_days = this.end_date.diff(this.begin_date, 'days') + 2;
            this.dates = dates;
        },
        start: function() {
            var self = this;

            // Accessor functions
            function getDate(d) { return new Date(d[0]); }
            function getNbClicks(d) { return d[1]; }

            // Prune tick values for visibility purpose
            function getPrunedTickValues(ticks, nb_desired_ticks) {
                var nb_values = ticks.length;
                var keep_one_of = Math.max(1, Math.floor(nb_values / nb_desired_ticks));

                return _.filter(ticks, function(d, i) {
                    return i % keep_one_of === 0;
                });
            }

            // Fill data for each day (with 0 click for days without data)
            var clicks_array = [];
            var begin_date_copy = this.begin_date;
            for(var i = 0 ; i < this.number_of_days ; i++) {
                var date_key = begin_date_copy.format('YYYY-MM-DD');
                clicks_array.push([date_key, (date_key in this.dates) ? this.dates[date_key] : 0]);
                begin_date_copy.add(1, 'days');
            }

            // Set title
            var nb_clicks = _.reduce(clicks_array, function(total, val) { return total + val[1] ; }, 0);
            $(this.$element + ' .title').html(nb_clicks + ' clicks');

            // Fit data into the NVD3 scheme
            var chart_data = [{}];
                chart_data[0]['key'] = '# of clicks';
                chart_data[0]['values'] = clicks_array;

            nv.addGraph(function() {
                var chart = nv.models.lineChart()
                    .x(function(d) { return getDate(d); })
                    .y(function(d) { return getNbClicks(d); })
                    .showYAxis(true)
                    .showXAxis(true);

                // Reduce the number of labels on the X axis for visibility
                var tick_values = getPrunedTickValues(chart_data[0]['values'], 10);

                chart.xAxis
                    .tickFormat(function(d) { return d3.time.format("%d/%m/%y")(new Date(d)); })
                    .tickValues(_.map(tick_values, function(d) { return getDate(d).getTime(); }))
                    .rotateLabels(55);

                chart.yAxis
                    .tickFormat(d3.format("d"))
                    .ticks(chart_data[0]['values'].length - 1);

                d3.select(self.$element + ' svg')
                    .datum(chart_data)
                    .call(chart);

                return self.chart = chart;
            });
        },
    });

    var PieChart = Widget.extend({
        init: function($element, data) {
            this.data = data;
            this.$element = $element;
        },
        start: function() {
            var self = this;

            // Process country data to fit into the NVD3 scheme
            var processed_data = [];
            for(var i = 0 ; i < this.data.length ; i++) {
                var country_name = this.data[i]['country_id'] ? this.data[i]['country_id'][1] : 'Undefined';
                processed_data.push({'label':country_name + ' (' + this.data[i]['country_id_count'] + ')', 'value':this.data[i]['country_id_count']});
            }

            // Set title
            $(this.$element + ' .title').html(this.data.length + ' countries');

            nv.addGraph(function() {
                var chart = nv.models.pieChart()
                    .x(function(d) { return d.label; })
                    .y(function(d) { return d.value; })
                    .showLabels(false);

                d3.select(self.$element + ' svg')
                    .datum(processed_data)
                    .transition().duration(1200)
                    .call(chart);

                return self.chart = chart;
            });
        },
    });

    base.ready().done(function() {
        // Resize the chart when a tab is opened, because NVD3 automatically reduce the size
        // of the chart to 5px width when the bootstrap tab is closed.
        var charts = {};
        $(".graph-tabs li a").click(function (e) {
            e.preventDefault();
            $(this).tab('show');
            _.chain(charts).pluck('chart').invoke('update'); // Force NVD3 to redraw the chart
        });

        // Get the code of the link
        var link_id = $('#link_id').val();

        var clicks = new Model('link.tracker.click');
        var links_domain = ['link_id', '=', parseInt(link_id)];

        var total_clicks = function() {
            return clicks.call('search_count', [[links_domain]]);
        };

        var clicks_by_day = function() {
            return clicks.call('read_group', [[links_domain], ['create_date']],
                               {'groupby':'create_date:day'});
        };

        var clicks_by_country = function() {
            return clicks.call('read_group',  [[links_domain], ['country_id']], 
                               {'groupby':'country_id'});
        };

        var last_week_clicks_by_country = function() {
            var interval = moment().subtract(7, 'days').format("YYYY-MM-DD");
            return clicks.call('read_group', [[links_domain, ['create_date', '>', interval]], ['country_id']],
                               {'groupby':'country_id'});
        };

        var last_month_clicks_by_country = function() {
            var interval = moment().subtract(30, 'days').format("YYYY-MM-DD");
            return clicks.call('read_group', [[links_domain, ['create_date', '>', interval]], ['country_id']],
                               {'groupby':'country_id'});
        };

        $.when(total_clicks(), 
               clicks_by_day(),
               clicks_by_country(),
               last_week_clicks_by_country(),
               last_month_clicks_by_country())
        .done(function(total_clicks, clicks_by_day, clicks_by_country, last_week_clicks_by_country, last_month_clicks_by_country) {

            if(total_clicks) {
                var formatted_clicks_by_day = {};
                var begin_date, end_date;
                for(var i = 0 ; i < clicks_by_day.length ; i++) {
                    var date = moment(clicks_by_day[i]['create_date:day'], "DD MMMM YYYY");
                    if (i === 0) { begin_date = date; }
                    if (i == clicks_by_day.length - 1) { end_date = date; }
                    formatted_clicks_by_day[date.format("YYYY-MM-DD")] = clicks_by_day[i]['create_date_count'];
                }

                // Process all time line chart data
                var now = moment();

                charts.all_time_bar = new BarChart('#all_time_clicks_chart', begin_date, now, formatted_clicks_by_day);

                // Process month line chart data
                begin_date = moment().subtract(30, 'days');
                charts.last_month_bar = new BarChart('#last_month_clicks_chart', begin_date, now, formatted_clicks_by_day);

                // Process week line chart data
                begin_date = moment().subtract(7, 'days');
                charts.last_week_bar = new BarChart('#last_week_clicks_chart', begin_date, now, formatted_clicks_by_day);

                // Process pie charts
                charts.all_time_pie = new PieChart('#all_time_countries_charts', clicks_by_country);
                charts.last_month_pie = new PieChart('#last_month_countries_charts', last_month_clicks_by_country);
                charts.last_week_pie = new PieChart('#last_week_countries_charts', last_week_clicks_by_country);

                var row_width = $('#all_time_countries_charts').parent().width();
                var charts_svg = $('#all_time_countries_charts,last_month_countries_charts,last_week_countries_charts').find('svg');
                charts_svg.css('height', Math.max(clicks_by_country.length * (row_width > 750 ? 1 : 2), 20) + 'em');

                _.invoke(charts, 'start');

                nv.utils.windowResize(function () {
                    _.chain(charts).pluck('chart').invoke('update');
                });
            }
            else {
                $('#all_time_charts').prepend('There is no data to show');
                $('#last_month_charts').prepend('There is no data to show');
                $('#last_week_charts').prepend('There is no data to show');
            }
        });

        // Copy to clipboard link
        ZeroClipboard.config({swfPath: location.origin + "/web/static/lib/zeroclipboard/ZeroClipboard.swf" });
        new ZeroClipboard($('.copy-to-clipboard'));

        var animating_copy = false;

        $('.copy-to-clipboard').on('click', function(e) {

            e.preventDefault();

            if(!animating_copy) {
                animating_copy = true;

                $('.o_website_links_short_url').clone()
                    .css('position', 'absolute')
                    .css('left', '15px')
                    .css('bottom', '10px')
                    .css('z-index', 2)
                    .removeClass('.o_website_links_short_url')
                    .addClass('animated-link')
                    .appendTo($('.o_website_links_short_url'))
                    .animate({
                        opacity: 0,
                        bottom: "+=20",
                    }, 500, function() {
                        $('.animated-link').remove();
                        animating_copy = false;
                    });
                }
        });
    });

    exports.BarChart = BarChart;
    exports.PieChart = PieChart;

return exports;
});
