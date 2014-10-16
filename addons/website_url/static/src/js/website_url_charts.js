(function () {
   'use strict';

   var QWeb = openerp.qweb;

    openerp.website_url = {};
    
    openerp.website_url.BarChart = openerp.Widget.extend({
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
                    return i % keep_one_of == 0;
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
                    .tooltips(true)
                    .transitionDuration(0)
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
                    .ticks(chart_data[0]['values'].length - 1)

                d3.select(self.$element + ' svg')
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

            // Process country data to fit into the NVD3 scheme
            var processed_data = [];
            for(var i = 0 ; i < this.data.length ; i++) {
                var country_name = this.data[i]['name'] ? this.data[i]['name'] : 'Undefined';
                processed_data.push({'label':country_name + ' (' + this.data[i]['count'] + ')', 'value':this.data[i]['count']});
            }

            // Set title
            $(this.$element + ' .title').html(this.data.length + ' countries');

            nv.addGraph(function() {
                var chart = nv.models.pieChart()
                    .x(function(d) { return d.label })
                    .y(function(d) { return d.value })
                    .showLabels(true);

                d3.select(self.$element + ' svg')
                    .datum(processed_data)
                    .transition().duration(1200)
                    .call(chart);

                nv.utils.windowResize(chart.update);
                return chart;
            });
        },
    });

   $(document).ready(function() {

        // Resize the chart when a tab is opened, because NVD3 automatically reduce the size
        // of the chart to 5px width when the bootstrap tab is closed.
        $(".graph-tabs li a").click(function (e) {
            e.preventDefault();
            $(this).tab('show');
            $(window).trigger('resize'); // Force NVD3 to redraw the chart
        });

        // Get the code of the link
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

                    var all_time_chart = new openerp.website_url.BarChart('#all_time_clicks_chart', begin_date, end_date, result_dic);
                    all_time_chart.start();

                    // Process month line chart data
                    var begin_date = moment().subtract(30, 'days');
                    var month_chart = new openerp.website_url.BarChart('#last_month_clicks_chart', begin_date, now, result_dic);
                    month_chart.start();

                    // Process week line chart data
                    var begin_date = moment().subtract(7, 'days');
                    var week_chart = new openerp.website_url.BarChart('#last_week_clicks_chart', begin_date, now, result_dic);
                    week_chart.start();

                    // Process pie charts
                    var all_time_pie_chart = new openerp.website_url.PieChart('#all_time_countries_charts', clicks_by_country);
                    all_time_pie_chart.start();

                    var last_month_pie_chart = new openerp.website_url.PieChart('#last_month_countries_charts', last_month_clicks_by_country);
                    last_month_pie_chart.start();

                    var last_week_pie_chart = new openerp.website_url.PieChart('#last_week_countries_charts', last_week_clicks_by_country);
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

        // Copy to clipboard link
        ZeroClipboard.config({swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" });
        new ZeroClipboard($('.copy-to-clipboard'));

        $('.copy-to-clipboard').on('click', function(e) {
            e.preventDefault();

            $(".copy-to-clipboard").text('copied').removeClass("btn-primary").addClass("btn-success");

            setTimeout(function() {
                $(".copy-to-clipboard").text("copy").removeClass("btn-success").addClass("btn-primary");
            }, '5000');
        });

        // Edit the short URL code
        $('.edit-code').on('click', function(e) {
            e.preventDefault();

            var init_code = $('#short-url-code').html();

            $('#short-url-code').html("<form style='display:inline;' id='edit-code-form'><input type='hidden' id='init_code' value='" + init_code + "'/><input type='text' id='new_code' value='" + init_code + "'/></form>");
            $('.edit-code').hide();
            $('.copy-to-clipboard').hide();
            $('.cancel-edit').show();

            $('.cancel-edit').on('click', function(e) {
                e.preventDefault();

                $('.edit-code').show();
                $('.copy-to-clipboard').show();
                $('.cancel-edit').hide();                

                var old_code = $('#edit-code-form #init_code').val();
                $('#short-url-code').html(old_code);

                $('#code-error').remove();
                $('#short-url-code form').remove();
            })

            $('#edit-code-form').submit(function(e) {
                e.preventDefault();

                var init_code = $('#edit-code-form #init_code')
                var new_code = $('#edit-code-form #new_code').val();

                openerp.jsonRpc('/r/add_code', 'call', {'init_code':code, 'new_code':new_code})
                    .then(function(result) {
                        if(result['error']) {
                            if($('#code-error').length == 0) {
                                $('#short-url-code').append("<p id='code-error' style='color:red;font-weight:bold;'>This code is already taken</p>");
                            }
                        }
                        else {
                            $('#code-error').remove();
                            $('#short-url-code form').remove();

                            // Show new code
                            var new_code = result['new_code'];
                            var host = $('#short-url-host').html();
                            $('#short-url-code').html(new_code);

                            // Update button copy to clipboard
                            $('.copy-to-clipboard').attr('data-clipboard-text', host + new_code)
                            
                            // Show action again
                            $('.edit-code').show();
                            $('.copy-to-clipboard').show();
                            $('.cancel-edit').hide();
                        }
                    });
            });
        });
    });
})();