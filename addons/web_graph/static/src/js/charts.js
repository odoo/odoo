
var formatter = function (measure) {
    return function (datapt) {
        var val = datapt.attributes;
        return {
            x: datapt.attributes.value[1],
            y: measure ? val.aggregates[measure] : val.length,
        };        
    };
};


var Charts = {
    bar_chart : function (groups, measure) {
        var formatted_data = [{
                key: 'Bar chart',
                values: _.map(groups, formatter(measure)),
            }];

        nv.addGraph(function () {
            var chart = nv.models.discreteBarChart()
                .tooltips(false)
                .showValues(true)
                .staggerLabels(true)
                .width(650)
                .height(400);

            d3.select('.graph_chart svg')
                .datum(formatted_data)
                .attr('width', 650)
                .attr('height', 400)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    },

    line_chart: function (groups, measure, measure_label) {
        var formatted_data = [{
                key: measure_label,
                values: _.map(groups, formatter(measure))
            }];

        nv.addGraph(function () {
            var chart = nv.models.lineChart()
                .x(function (d,u) { return u; })
                .width(600)
                .height(300)
                .margin({top: 30, right: 20, bottom: 20, left: 60});

            d3.select('.graph_chart svg')
                .attr('width', 600)
                .attr('height', 300)
                .datum(formatted_data)
                .call(chart);

            return chart;
          });
    },

    pie_chart: function (groups, measure) {
        var formatted_data = _.map(groups, formatter(measure));

        nv.addGraph(function () {
            var chart = nv.models.pieChart()
                .color(d3.scale.category10().range())
                .width(650)
                .height(400);

            d3.select('.graph_chart svg')
                .datum(formatted_data)
                .transition().duration(1200)
                .attr('width', 650)
                .attr('height', 400)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    },


};