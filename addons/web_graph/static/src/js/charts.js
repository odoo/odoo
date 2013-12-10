
openerp.web_graph.draw_chart = function (mode, pivot, svg) {
    openerp.web_graph[mode](pivot, svg);
};


openerp.web_graph.bar_chart = function (pivot, svg) {
    var dim_x = pivot.rows.groupby.length,
        dim_y = pivot.cols.groupby.length,
        data;

    if ((dim_x === 0) && (dim_y === 0)) {
        data = [{key: 'Expected Revenue', values:[{
            title: 'Total',
            value: pivot.get_value(pivot.rows.main.id, pivot.cols.main.id),
        }]}];
        // debugger;
    } else if ((dim_x === 0) && (dim_y === 1)){
       
     } else
    {
        data = _.map(pivot.rows.main.children, function (pt) {
            var value = pivot.get_value(pt.id, pivot.cols.main.id),
                title = (pt.title !== undefined) ? pt.title : 'Undefined';
            return {title: title, value: value};
        });
        data = [{key: 'Bar chart', values:data}];
    }
    nv.addGraph(function () {
      var chart = nv.models.discreteBarChart()
            .x(function(d) { return d.title;})
            .y(function(d) { return d.value;})
            .tooltips(false)
            .showValues(true)
            .staggerLabels(true)
            .width(650)
            .height(400);

        d3.select(svg)
            .datum(data)
            .attr('width', 650)
            .attr('height', 400)
            .call(chart);

        nv.utils.windowResize(chart.update);
        return chart;
    });
};


openerp.web_graph.line_chart = function (pivot, svg) {
    var data = _.map(pivot.rows.main.children, function (pt) {
    var value = pivot.get_value(pt.id, pivot.cols.main.id),
        title = (pt.title !== undefined) ? pt.title : 'Undefined';
            return {x: title, y: value};
        });

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

openerp.web_graph.pie_chart = function (pivot, svg) {
    var data = _.map(pivot.rows.main.children, function (pt) {
        var value = pivot.get_value(pt.id, pivot.cols.main.id),
            title = (pt.title !== undefined) ? pt.title : 'Undefined';
        return {x: title, y: value};
    });
    
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
