
openerp.web_graph.draw_chart = function (mode, pivot, svg) {

    var data = _.map(pivot.rows.main.children, function (pt) {
        var val = pivot.get_value(pt.id, pivot.cols.main.id);
        return {x: pt.title, y: val};
    });
    
    switch (mode) {
        case 'bar_chart':
            bar_chart();
            break;
        case 'line_chart':
            line_chart();
            break;
        case 'pie_chart':
            pie_chart();
            break;
    }

    function bar_chart () {
        nv.addGraph(function () {
          var chart = nv.models.discreteBarChart()
                .tooltips(false)
                .showValues(true)
                .staggerLabels(true)
                .width(650)
                .height(400);

            d3.select(svg)
                .datum([{key: 'Bar chart', values:data}])
                .attr('width', 650)
                .attr('height', 400)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    };

    function line_chart () {
        nv.addGraph(function () {
            var chart = nv.models.lineChart()
                .x(function (d,u) { return u; })
                .width(600)
                .height(300)
                .margin({top: 30, right: 20, bottom: 20, left: 60});

            d3.select(svg)
                .attr('width', 600)
                .attr('height', 300)
                .datum([{key: 'Bar chart', values: data}])
                .call(chart);

            return chart;
          });
    };

    function pie_chart () {
        nv.addGraph(function () {
            var chart = nv.models.pieChart()
                .color(d3.scale.category10().range())
                .width(650)
                .height(400);

            d3.select(svg)
                .datum(data)
                .transition().duration(1200)
                .attr('width', 650)
                .attr('height', 400)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    };

}
