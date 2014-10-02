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

        var all_chart_data = [
            {
                "key": "Series 1",
                // "values": [[1025409600000 , 0] , [1028088000000 , 20] , [1030766400000 , 7] , [1033358400000 , 1]]
                "values": [[1025409600000 , 0], [1411596000000 , 14] , [1411941600000 , 7] , [1412028000000 , 19]]
            },
        ];

        console.log(all_chart_data);

        openerp.jsonRpc('/r/gere/chart', 'call', {})
            .then(function(result) {
                console.log(result);

                var clicks = {};

                //result.unshift({create_date: '2014-09-15'});

                for(var i = 0 ; i < result.length ; i++) {
                    var link_date = moment(result[i].create_date, 'YYYY-MM-DD');
                    var timestamp = link_date.format('X') * 1000;
                    timestamp in clicks ? clicks[timestamp] += 1 : clicks[timestamp] = 1;
                }

                var clicks_array = [];

                for(var key in clicks) {
                    clicks_array.push([key, clicks[key]]);
                }

                console.log(clicks);
                console.log(clicks_array);

                var all_chart_data2 = [{}];
                all_chart_data2[0]['key'] = 'Series 1';
                all_chart_data2[0]['values'] = clicks_array;

                console.log(all_chart_data2);

                // All Chart
                nv.addGraph(function() {
                    var chart = nv.models.lineChart()
                        .x(function(d) { return d[0] })
                        .y(function(d) { return d[1] })
                        .color(d3.scale.category10().range())
                        .useInteractiveGuideline(true);

                    chart.xAxis.tickFormat(function(d) {
                        // return d3.time.format('%x')(new Date(d))
                        return moment(d).format('DD/MM/YYYY');
                    });

                    d3.select('#all_chart svg')
                        .datum(all_chart_data2)
                        // .transition().duration(500)
                        .call(chart);

                    // nv.utils.windowResize(chart.update);

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