/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

/* jshint undef: false  */


openerp.web_graph = function (instance) {
'use strict';

var _lt = instance.web._lt;
var _t = instance.web._t;
var QWeb = instance.web.qweb;

instance.web.views.add('graph', 'instance.web_graph.GraphView');

 /**
  * GraphView view.  It mostly contains two widgets (PivotTable and ChartView)
  * and some data.
  */
instance.web_graph.GraphView = instance.web.View.extend({
    template: 'GraphView',
    display_name: _lt('Graph'),
    view_type: 'graph',
    mode: 'pivot',   // pivot => display pivot table, chart => display chart

    events: {
        'click .graph_mode_selection li' : function (event) {
            event.preventDefault();
            var view_mode = event.target.attributes['data-mode'].nodeValue;
            if (view_mode === 'data') {
                this.mode = 'pivot';
            } else {
                this.mode = 'chart';
                this.chart_view.set_mode(view_mode);
            }
            this.display_data();
        },
    },

    view_loading: function (fields_view_get) {
        var self = this;
        var model = new instance.web.Model(fields_view_get.model, {group_by_no_leaf: true});
        var options = {};
        options.domain = [];
        options.col_groupby = [];

        // get the default groupbys and measure defined in the field view
        options.measure = null;
        options.row_groupby = [];
        _.each(fields_view_get.arch.children, function (field) {
            if ('name' in field.attrs) {
                if ('operator' in field.attrs) {
                    options.measure = field.attrs.name;
                } else {
                    options.row_groupby.push(field.attrs.name);
                }
            }
        });

        // get the most important fields (of the model) by looking at the
        // groupby filters defined in the search view
        options.important_fields = []
        var load_view = instance.web.fields_view_get({
            model: model,
            view_type: 'search',
        });

        var important_fields_def = $.when(load_view).then(function (search_view) {
            var groups = _.select(search_view.arch.children, function (c) {
                return (c.tag == 'group') && (c.attrs.string != 'Display');
            });

            _.each(groups, function(g) {
                _.each(g.children, function (g) {
                    if (g.attrs.context) {
                        var field_id = py.eval(g.attrs.context).group_by;
                        options.important_fields.push(field_id);
                    }
                });
            });
        }).then

        // get the fields descriptions from the model
        var field_descr_def = model.call('fields_get', [])
            .then(function (fields) { options.fields = fields; });


        return $.when(important_fields_def, field_descr_def)
            .then(function () {
                self.pivot_table = new PivotTable(model, options);
                self.chart_view = new ChartView(model, options);
            })
            .then(function () {
                return self.pivot_table.appendTo('.graph_main_content')                
            })
            .then(function() {
                return self.chart_view.appendTo('.graph_main_content');
            });
    },

    display_data : function () {
        if (this.mode === 'pivot') {
            this.chart_view.hide();
            this.pivot_table.show();
        } else {
            this.pivot_table.hide();
            this.chart_view.show();
        }
    },

    do_search: function (domain, context, group_by) {
        this.domain = new instance.web.CompoundDomain(domain);
        this.pivot_table.set_domain(domain);
        this.chart_view.set_domain(domain);
        this.display_data();
    },

    do_show: function () {
        this.do_push_state({});
        return this._super();
    },

});

 /**
  * BasicDataView widget.  Basic widget to manage show/hide functionality
  * and to initialize some attributes.  It is inherited by PivotTable 
  * and ChartView widget.
  */
var BasicDataView = instance.web.Widget.extend({

    need_redraw: false,

    // Input parameters: 
    //      model: model to display
    //      fields: dictionary returned by field_get on model (desc of model)
    //      domain: constraints on model records 
    //      row_groupby: groubys on rows (so, row headers in the pivot table)
    //      col_groupby: idem, but on col
    //      measure: quantity to display. either a field from the model, or 
    //            null, in which case we use the "count" measure
    init: function (model, options) {
        this.model = model;
        this.fields = options.fields;
        this.domain = options.domain;
        this.row_groupby = options.row_groupby;
        this.col_groupby = options.col_groupby;
        this.measure = options.measure;
        this.measure_label = options.measure ? options.fields[options.measure].string : 'Quantity';
        this.data = [];
        this.need_redraw = true;
        this.important_fields = options.important_fields;
    },

    set_domain: function (domain) {
        this.domain = domain;
        this.need_redraw = true;
    },

    set_row_groupby: function (row_groupby) {
        this.row_groupby = row_groupby;
        this.need_redraw = true;
    },

    set_col_groupby: function (col_groupby) {
        this.col_groupby = col_groupby;
        this.need_redraw = true;
    },

    set_measure: function (measure) {
        this.measure = measure;
        this.need_redraw = true;
    },

    show: function () {
        if (this.need_redraw) {
            this.draw();
            this.need_redraw = false;
        }
        this.$el.css('display', 'block');
    },

    hide: function () {
        this.$el.css('display', 'none');
    },

    draw: function() {
    },

    get_data: function (groupby) {
        var view_fields = this.row_groupby.concat(this.measure, this.col_groupby);
        return query_groups(this.model, view_fields, this.domain, groupby);
    },

});

 /**
  * PivotTable widget.  It displays the data in tabular data and allows the
  * user to drill down and up in the table
  */
var PivotTable = BasicDataView.extend({
    template: 'pivot_table',
    rows: null,
    cols: null,
    current_row_id : 0,

    events: {
        'click .graph_border a' : function (event) {
            event.preventDefault();
            var row_id = event.target.attributes['data-row-id'].nodeValue;
            console.log("clickclick on row ", row_id);
        },
    },

    generate_id: function () {
        this.current_row_id += 1;
        return this.current_row_id - 1;
    },

    draw: function () {
        this.get_data(this.row_groupby)
            .then(this.proxy('build_table'))
            .done(this.proxy('_draw'));
    },

    build_table: function (data) {
        var self = this;
        function make_cell (content, is_border) {
            return '<td' +
                   ((is_border) ? ' class="graph_border"' : '') +
                   '>' + content + '</td>';
        }

        this.cols = [{
            path: [],
            value: this.measure_label,
            expanded: false,
            parent: null,
            children: [],
            html_tds: [],
            domain: this.domain,
            header: $(make_cell(this.measure_label, true)),
        }];

        this.rows = _.map(data, function (datapt) {
            var jquery_row = $('<tr></tr>');
            var header = $(make_cell(datapt.attributes.value[1], true));
            var row_id = self.generate_id();

            header.prepend('<a data-row-id="'+ row_id + '" href="#">+ </a>');
            jquery_row.html(header);
            jquery_row.append(make_cell(datapt.attributes.aggregates[self.measure]));

            var row = {
                path: [datapt.attributes.grouped_on],
                value: datapt.attributes.value[1],
                expanded: false,
                parent: null,
                children: [],
                html_tr: jquery_row,
                domain: datapt.model._domain
            };
            return row;
        });
    }, 

    _draw: function () {

        this.$el.empty();
        var self = this;

        var header = '<tr><td class="graph_border">' +
                    this.fields[this.row_groupby[0]].string +
                    '</td><td class="graph_border">' +
                    this.measure_label +
                    '</td></tr>';
        this.$el.append(header);

        _.each(this.rows, function (row) {
            self.$el.append(row.html_tr);
        });

    }
});

 /**
  * ChartView widget.  It displays the data in chart form, using the nvd3
  * library.  Various modes include bar charts, pie charts or line charts.
  */
var ChartView = BasicDataView.extend({
    template: 'chart_view',

    set_mode: function (mode) {
        this.render = this['render_' + mode];
        this.need_redraw = true;
    },

    draw: function () {
        var self = this;
        this.$el.empty();
        this.$el.append('<svg></svg>');
        this.get_data(this.row_groupby).done(function (data) {
            self.render(data);
        });
    },

    format_data:  function (datapt) {
        var val = datapt.attributes;
        return {
            x: datapt.attributes.value[1],
            y: this.measure ? val.aggregates[this.measure] : val.length,
        };
    },

    render_bar_chart: function (data) {
        var formatted_data = [{
                key: 'Bar chart',
                values: _.map(data, this.proxy('format_data')),
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

    render_line_chart: function (data) {
        var formatted_data = [{
                key: this.measure_label,
                values: _.map(data, this.proxy('format_data'))
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

    render_pie_chart: function (data) {
        var formatted_data = _.map(data, this.proxy('format_data'));

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

});

/**
 * Query the server and return a deferred which will return the data
 * with all the groupbys applied (this is done for now, but the goal
 * is to modify read_group in order to allow eager and lazy groupbys
 */
function query_groups (model, fields, domain, groupbys) {
    return model.query(fields)
        .filter(domain)
        .group_by(groupbys)
        .then(function (results) {
            var non_empty_results = _.filter(results, function (group) {
                return group.attributes.length > 0;
            });
            if (groupbys.length <= 1) {
                return non_empty_results;
            } else {
                var get_subgroups = $.when.apply(null, _.map(non_empty_results, function (result) {
                    var new_domain = result.model._domain;
                    var new_groupings = groupbys.slice(1);
                    return query_groups(model, fields,new_domain, new_groupings).then(function (subgroups) {
                        result.subgroups_data = subgroups;
                    });
                }));
                return get_subgroups.then(function () {
                    return non_empty_results;
                });
            }
        });
}


};

