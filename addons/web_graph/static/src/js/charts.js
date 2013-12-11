
openerp.web_graph.draw_chart = function (options) {
    openerp.web_graph[options.mode](options);
};


openerp.web_graph.bar_chart = function (options) {
    var pivot = options.pivot,
        dim_x = pivot.rows.groupby.length,
        dim_y = pivot.cols.groupby.length,
        data = [];

    // No groupby **************************************************************
    if ((dim_x === 0) && (dim_y === 0)) {
        data = [{key: 'Total', values:[{
            title: 'Total',
            value: options.pivot.get_value(pivot.rows.main.id, pivot.cols.main.id),
        }]}];
        nv.addGraph(function () {
          var chart = nv.models.discreteBarChart()
                .x(function(d) { return d.title;})
                .y(function(d) { return d.value;})
                .tooltips(false)
                .showValues(true)
                .width(options.width)
                .height(options.height)
                .staggerLabels(true);

            d3.select(options.svg)
                .datum(data)
                .attr('width', options.width)
                .attr('height', options.height)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    // Only column groupbys ****************************************************
    } else if ((dim_x === 0) && (dim_y >= 1)){
        data =  _.map(pivot.get_columns_depth(1), function (header) {
            return {
                key: header.title,
                values: [{x:header.root.main.title, y: pivot.get_total(header)}]
            };
        });
        nv.addGraph(function() {
            var chart = nv.models.multiBarChart()
                    .stacked(true)
                    .tooltips(false)
                    .width(options.width)
                    .height(options.height)
                    .showControls(false);

            d3.select(options.svg)
                .datum(data)
                .attr('width', options.width)
                .attr('height', options.height)
                .transition()
                .duration(500)
                .call(chart);

            nv.utils.windowResize(chart.update);

            return chart;
        });
    // Just 1 row groupby ******************************************************
    } else if ((dim_x === 1) && (dim_y === 0))  {
        data = _.map(pivot.rows.main.children, function (pt) {
            var value = pivot.get_value(pt.id, pivot.cols.main.id),
                title = (pt.title !== undefined) ? pt.title : 'Undefined';
            return {title: title, value: value};
        });
        data = [{key: options.measure_label, values:data}];
        nv.addGraph(function () {
          var chart = nv.models.discreteBarChart()
                .x(function(d) { return d.title;})
                .y(function(d) { return d.value;})
                .tooltips(false)
                .showValues(true)
                .width(options.width)
                .height(options.height)
                .staggerLabels(true);

            d3.select(options.svg)
                .datum(data)
                .attr('width', options.width)
                .attr('height', options.height)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    // 1 row groupby and some col groupbys**************************************
    } else if ((dim_x === 1) && (dim_y >= 1))  {
        data = _.map(pivot.get_columns_depth(1), function (colhdr) {
            var values = _.map(pivot.get_rows_depth(1), function (header) {
                return {
                    x: header.title || 'Undefined',
                    y: pivot.get_value(header.id, colhdr.id, 0)
                };
            });
            return {key: colhdr.title || 'Undefined', values: values};
        });

        nv.addGraph(function () {
          var chart = nv.models.multiBarChart()
                .stacked(true)
                .staggerLabels(true)
                .width(options.width)
                .height(options.height)
                .tooltips(false);

            d3.select(options.svg)
                .datum(data)
                .attr('width', options.width)
                .attr('height', options.height)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    // At least two row groupby*************************************************
    } else {
        var keys = _.uniq(_.map(pivot.get_rows_depth(2), function (hdr) {
            return hdr.title || 'Undefined';
        }));
        data = _.map(keys, function (key) {
            var values = _.map(pivot.get_rows_depth(1), function (hdr) {
                var subhdr = _.find(hdr.children, function (child) {
                    return ((child.title === key) || ((child.title === undefined) && (key === 'Undefined')));
                });
                return {
                    x: hdr.title || 'Undefined',
                    y: (subhdr) ? pivot.get_total(subhdr) : 0
                };
            });
            return {key:key, values: values};
        });

        nv.addGraph(function () {
          var chart = nv.models.multiBarChart()
                .stacked(true)
                .staggerLabels(true)
                .width(options.width)
                .height(options.height)
                .tooltips(false);

            d3.select(options.svg)
                .datum(data)
                .attr('width', options.width)
                .attr('height', options.height)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    }
};


openerp.web_graph.line_chart = function (options) {
    var pivot = options.pivot,
        dim_x = pivot.rows.groupby.length,
        dim_y = pivot.cols.groupby.length;

    var data = _.map(pivot.get_cols_leaves(), function (col) {
        var values = _.map(pivot.get_rows_depth(dim_x), function (row) {
            return {x: row.title, y: pivot.get_value(row.id,col.id, 0)};
        });
        var title = _.map(col.path, function (p) {
            return p || 'Undefined';
        }).join('/');
        if (dim_y === 0) {
            title = options.measure_label;
        }
        return {values: values, key: title};
    });

    nv.addGraph(function () {
        var chart = nv.models.lineChart()
            .x(function (d,u) { return u; })
            .width(options.width)
            .height(options.height)
            .margin({top: 30, right: 20, bottom: 20, left: 60});

        d3.select(options.svg)
            .attr('width', options.width)
            .attr('height', options.height)
            .datum(data)
            .call(chart);

        return chart;
      });
};

openerp.web_graph.pie_chart = function (options) {
    var pivot = options.pivot,
        dim_x = pivot.rows.groupby.length,
        dim_y = pivot.cols.groupby.length;

    var data = _.map(pivot.get_rows_leaves(), function (row) {
        var title = _.map(row.path, function (p) {
            return p || 'Undefined';
        }).join('/');
        if (dim_x === 0) {
            title = options.measure_label;
        }
        return {x: title, y: pivot.get_total(row)};
    });

    nv.addGraph(function () {
        var chart = nv.models.pieChart()
            .color(d3.scale.category10().range())
            .width(options.width)
            .height(options.height);

        d3.select(options.svg)
            .datum(data)
            .transition().duration(1200)
            .attr('width', options.width)
            .attr('height', options.height)
            .call(chart);

        nv.utils.windowResize(chart.update);
        return chart;
    });
};
