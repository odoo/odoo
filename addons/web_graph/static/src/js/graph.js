/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/
/*global openerp:true*/
/*global $:true*/
'use strict';

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
                this.get_data().done(function (data) {
                    self.chart_view.draw(data, mode);
                    self.chart_view.show(mode);
                });
            }
        },
    },

    init: function(parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
        this.pivot_table = new PivotTable(this);
        this.chart_view = new ChartView(this);
        this.x_groups = [];
        this.measure = null;
        this.domain = [];
        this.model = null;

    },

    view_loading: function (fields_view_get) {
        var self = this;
        this.model = new instance.web.Model(fields_view_get.model, {group_by_no_leaf: true});

        // get the default groupbys and measure defined in the field view
        _.each(fields_view_get.arch.children, function (field) {
            if ('name' in field.attrs) {
                if ('operator' in field.attrs) {
                    self.measure = field.attrs.name;
                } else {
                    self.x_groups.push(field.attrs.name);
                }
            }
        });

        this.chart_view.set_measure(this.measure);
        this.pivot_table.appendTo('.graph_pivot');
        this.chart_view.appendTo('.graph_chart');
        this.chart_view.hide();
        this.get_data().done(this.pivot_table.draw);
    },

    get_data: function () {
        var view_fields = this.x_groups.concat(this.measure);

        return query_groups(this.model, view_fields, this.domain, this.x_groups);
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
  * PivotTable widget.  It displays the data in tabular data and allows the
  * user to drill down and up in the table
  */
var PivotTable = instance.web.Widget.extend({
    template: 'pivot_table',

    show: function () {
        this.$el.css('display', 'block');
    },

    hide: function () {
        this.$el.css('display', 'none');
    },

    draw: function (data) {
        console.log("data",data);
    },
});

 /**
  * ChartView widget.  It displays the data in chart form, using the nvd3
  * library.  Various modes include bar charts, pie charts or line charts.
  */
var ChartView = instance.web.Widget.extend({
    template: 'chart_view',
    measure: null,

    show: function () {
        this.$el.css('display', 'block');
    },

    hide: function () {
        this.$el.css('display', 'none');
    },

    set_measure: function (measure) {
        this.measure = measure;
    },

    draw: function (data, mode) {
        $('.graph_chart').empty();
        $('.graph_chart').append('<svg></svg>');

        switch (mode) {
            case 'bar_chart':
                this.render_bar_chart(data);
                break;
            case 'line_chart':
                this.render_line_chart(data);
                break;
            case 'pie_chart':
                this.render_pie_chart(data);
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

    render_bar_chart: function (data) {
        var formatted_data = [{
                key: 'Bar chart',
                values: _.map(data, this.format_data.bind(this)),
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
        var measure_label = (this.measure) ? this.measure : 'Quantity';

        var formatted_data = [{
                key: measure_label,
                values: _.map(data, this.format_data.bind(this))
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
        var formatted_data = _.map(data, this.format_data.bind(this));

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
