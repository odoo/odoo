(function () {
   'use strict';

   $(document).ready(function() {

        // Charts Data
        var pie_data = [
            {
                "label" : "India",
                "value" : 5
            },
            {
                "label" : "Africa",
                "value" : 10
            }
        ];

        openerp.jsonRpc('/r/gere/chart', 'call', {})
            .then(function(result) {

                var clicks = {};

                for(var i = 0 ; i < result.length ; i++) {
                    var link_date = moment(result[i].create_date, 'YYYY-MM-DD').format('YYYY-MM-DD');
                    link_date in clicks ? clicks[link_date] += 1 : clicks[link_date] = 1;
                }

                var clicks_array = [];

                for(var key in clicks) {
                    clicks_array.push([key, clicks[key]]);
                }

                var all_chart_data2 = [{}];
                all_chart_data2[0]['key'] = 'Series 1';
                all_chart_data2[0]['values'] = clicks_array;

                console.log(all_chart_data2);

                function getDate(d) {
                    var d = new Date(d[0])
                    console.log('getDate() : ' + d);
                    return d;
                }

                var minDate = getDate(all_chart_data2[0]['values'][0]),
                    maxDate = getDate(all_chart_data2[0]['values'][all_chart_data2[0]['values'].length - 1]);

                var x = d3.time.scale().domain([minDate, maxDate]).range([0, 450]);

                // All Chart
                nv.addGraph(function() {
                    var chart = nv.models.lineChart()
                        .x(function(d) {
                            var nx = x(getDate(d));
                            console.log(nx);
                            return nx;
                        })
                        .y(function(d) { return d[1] })
                        .color(d3.scale.category10().range())
                        .useInteractiveGuideline(true);

                    chart.xAxis.tickFormat(function(d) {
                        return moment(x.invert(d)).format('DD/MM/YYYY');
                    });

                    d3.select('#all_chart svg')
                        .datum(all_chart_data2)
                        .call(chart);

                    return chart;
                });
            });

        // Pie Chart
        nv.addGraph(function() {
            var chart = nv.models.pieChart()
                .x(function(d) { return d.label })
                .y(function(d) { return d.value })
                .showLabels(true);


            d3.select("#pie_chart svg")
                .datum(pie_data)
                .transition().duration(1200)
                .call(chart);

            return chart;
        });

        
    });
})();