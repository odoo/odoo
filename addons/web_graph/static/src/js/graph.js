/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

'use strict';
/* jshint undef: false  */


openerp.web_graph = function (instance) {

var _lt = instance.web._lt;
var _t = instance.web._t;

instance.web.views.add('graph', 'instance.web_graph.GraphView');

 /**
  * GraphView view.  It mostly contains two widgets (PivotTable and ChartView)
  * and some data.
  */
instance.web_graph.GraphView = instance.web.View.extend({
    template: 'GraphView',
    display_name: _lt('Graph'),
    view_type: 'graph',

    events: {
        'click .graph_mode_selection li' : function (event) {
            event.preventDefault();
            var self = this,
                mode = event.target.attributes['data-mode'].nodeValue;
            if (mode == 'data') {
                this.chart_view.hide();
                this.pivot_table.show();
            } else {
                this.pivot_table.hide();
                this.chart_view.set_mode(mode);
                this.chart_view.show();
            }
        },
    },

    view_loading: function (fields_view_get) {
        var self = this;
        var model = new instance.web.Model(fields_view_get.model, {group_by_no_leaf: true});
        var measure = null;
        var groupbys = []

        // get the default groupbys and measure defined in the field view
        _.each(fields_view_get.arch.children, function (field) {
            if ('name' in field.attrs) {
                if ('operator' in field.attrs) {
                    measure = field.attrs.name;
                } else {
                    groupbys.push(field.attrs.name);
                }
            }
        });

        return model.call('fields_get', []).then(function (fields) {
            var view_fields = groupbys.concat(measure);
            query_groups(model, view_fields, self.domain, groupbys).done(function (data) {
                self.pivot_table = new PivotTable(data, fields, groupbys, measure);
                self.chart_view = new ChartView(data, fields, groupbys, measure);
                self.pivot_table.appendTo('.graph_main_content')
                    .done(function () {
                        self.pivot_table.draw();
                    });
                self.chart_view.appendTo('.graph_main_content')
                    .done(function () {
                        self.chart_view.hide();
                    });
            });
        });
    },

    do_search: function (domain, context, group_by) {
        this.domain = new instance.web.CompoundDomain(domain);
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
    init: function (data, fields, groupby, measure) {
        this.data = data;
        this.fields = fields;
        this.groupby = groupby;
        this.measure = measure;
    },

    show: function () {
        this.$el.css('display', 'block');
    },

    hide: function () {
        this.$el.css('display', 'none');
    },
});

 /**
  * PivotTable widget.  It displays the data in tabular data and allows the
  * user to drill down and up in the table
  */
var PivotTable = BasicDataView.extend({
    template: 'pivot_table',

    draw: function () {
        console.log('data',this.data);
    },
});

 /**
  * ChartView widget.  It displays the data in chart form, using the nvd3
  * library.  Various modes include bar charts, pie charts or line charts.
  */
var ChartView = BasicDataView.extend({
    template: 'chart_view',
    mode: 'bar_chart',

    set_mode: function (mode) {
        this.mode = mode;
        this.draw();
    },

    draw: function () {
        this.$el.empty();
        this.$el.append('<svg></svg>');

        switch (this.mode) {
            case 'bar_chart':
                this.render_bar_chart();
                break;
            case 'line_chart':
                this.render_line_chart();
                break;
            case 'pie_chart':
                this.render_pie_chart();
                break;
        }
    },

    format_data:  function (datapt) {
        var val = datapt.attributes;
        return {
            x: datapt.attributes.value[1],
            y: this.measure ? val.aggregates[this.measure] : val.length,
        };
    },

    render_bar_chart: function () {
        var formatted_data = [{
                key: 'Bar chart',
                values: _.map(this.data, this.format_data.bind(this)),
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

    render_line_chart: function () {
        var measure_label = (this.measure) ? this.measure : 'Quantity';

        var formatted_data = [{
                key: measure_label,
                values: _.map(this.data, this.format_data.bind(this))
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

    render_pie_chart: function () {
        var formatted_data = _.map(this.data, this.format_data.bind(this));

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

