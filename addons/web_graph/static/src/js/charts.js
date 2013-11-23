
function format_chart_data (pivot) {
    var values = _.map(pivot.rows.headers[0].children.reverse(), function (pt) {
        var val = pivot.get_value(pt.id, 2);
        return {x: pt.name, y: val};
    });
    return [{key: 'Bar chart', values: values}];

};

var Charts = {
    bar_chart : function (pivot) {
        var data = format_chart_data(pivot);
        nv.addGraph(function () {
          var chart = nv.models.discreteBarChart()
                .tooltips(false)
                .showValues(true)
                .staggerLabels(true)
                .width(650)
                .height(400);

            d3.select('.graph_main_content svg')
                .datum(data)
                .attr('width', 650)
                .attr('height', 400)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    },

    line_chart: function (pivot) {
        data = format_chart_data(pivot);
        nv.addGraph(function () {
            var chart = nv.models.lineChart()
                .x(function (d,u) { return u; })
                .width(600)
                .height(300)
                .margin({top: 30, right: 20, bottom: 20, left: 60});

            d3.select('.graph_main_content svg')
                .attr('width', 600)
                .attr('height', 300)
                .datum(data)
                .call(chart);

            return chart;
          });
    },

    pie_chart: function (pivot) {
        data = format_chart_data(pivot);
        nv.addGraph(function () {
            var chart = nv.models.pieChart()
                .color(d3.scale.category10().range())
                .width(650)
                .height(400);

            d3.select('.graph_main_content svg')
                .datum(data[0].values)
                .transition().duration(1200)
                .attr('width', 650)
                .attr('height', 400)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    },
};