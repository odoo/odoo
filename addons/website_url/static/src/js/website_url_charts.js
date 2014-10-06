(function () {
   'use strict';

   $(document).ready(function() {

        $(".graph-tabs a").click(function (e) {
            console.log('click');
            e.preventDefault();
            $(this).tab('show');
            $(window).trigger('resize'); // Added this line to force NVD3 to redraw the chart
        });

        var code = $('#code').val();

        openerp.jsonRpc('/r/' + code + '/chart', 'call', {})
            .then(function(result) {

                console.log(result);

                var total_clicks = result['total_clicks'];
                var month_clicks = result['month_clicks'];
                var clicks_by_country = result['clicks_by_country'];

                // Process month data
                var result_dic = {}
                for(var i = 0 ; i < month_clicks.length ; i++) {
                    result_dic[month_clicks[i].to_char] = month_clicks[i].count;
                }

                var nb_unit = 30;
                var time_unit = 'days';
                var begin_date = moment().subtract(nb_unit, time_unit);

                var clicks_array = [];
                for(var i = 0 ; i < nb_unit ; i++) {
                    var new_date = begin_date.add(1, time_unit).format('YYYY-MM-DD');
                    clicks_array.push([new_date, (new_date in result_dic) ? result_dic[new_date] : 0]);
                }

                var all_chart_data = [{}];
                all_chart_data[0]['key'] = '# of clicks';
                all_chart_data[0]['values'] = clicks_array;

                function getDate(d) {
                    return new Date(d[0])
                }

                var minDate = getDate(all_chart_data[0]['values'][0]),
                    maxDate = getDate(all_chart_data[0]['values'][all_chart_data[0]['values'].length - 1]);

                var x = d3.time.scale().domain([minDate, maxDate]).range([0, 450]);

                // Month Chart
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
                    ;

                    chart.xAxis.tickFormat(function(d) {
                        return moment(x.invert(d)).format('DD/MM/YYYY');
                    });

                    chart.yAxis
                        .tickFormat(d3.format(',i'));

                    d3.select('#last_month_chart svg')
                        .datum(all_chart_data)
                        .call(chart);

                    nv.utils.windowResize(chart.update);

                    return chart;
                });

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

                console.log(clicks_by_country_data)

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

        // // Charts Data
        // var pie_data = [
        //     {
        //         "label" : "India",
        //         "value" : 5
        //     },
        //     {
        //         "label" : "Africa",
        //         "value" : 10
        //     }
        // ];

        
    });
})();