/*---------------------------------------------------------
 * OpenERP web_graph
 *---------------------------------------------------------*/

/* jshint undef: false  */

openerp.web_graph = function (instance) {
'use strict';

var _lt = instance.web._lt;
var _t = instance.web._t;

instance.web.views.add('graph', 'instance.web_graph.GraphView');

instance.web_graph.GraphView = instance.web.View.extend({
    display_name: _lt('Graph'),
    view_type: 'graph',

    // ----------------------------------------------------------------------
    // Init stuff
    // ----------------------------------------------------------------------
    init: function(parent, dataset, view_id, options) {
        var self = this;
        this._super(parent, dataset, view_id, options);
        this.dataset = dataset;
        this.model = new instance.web.Model(dataset.model, {group_by_no_leaf: true});
        this.search_view = parent.searchview;
        this.col_search_field = {
            get_context: function() { return { col_group_by: self.graph_widget.get_col_groupbys()};},
            get_domain: function () {},
            get_groupby: function () {},
        };
    },

    view_loading: function (fields_view_get) {
        var self = this,
            arch = fields_view_get.arch;

        this.widget_config = {
            title: arch.attrs.string,
            stacked : (arch.attrs.stacked === 'True'),
            mode: arch.attrs.type || 'bar',
            measures: [],
            row_groupby: [],
            col_groupby: [],
            graph_view: this,
        };

        _.each(arch.children, function (field) {
            var field_name = field.attrs.name;
            if (_.has(field.attrs, 'interval')) {
                field_name = field.attrs.name + ':' + field.attrs.interval;
            } 
            if (_.has(field.attrs, 'type')) {
                switch (field.attrs.type) {
                    case 'row':
                        self.widget_config.row_groupby.push(field_name);
                        break;
                    case 'col':
                        self.widget_config.col_groupby.push(field_name);
                        break;
                    case 'measure':
                        self.widget_config.measures.push(field_name);
                        break;
                }
            } else {  // old style, kept for backward compatibility
                if ('operator' in field.attrs) {
                    self.widget_config.measures.push(field_name);
                } else {
                    self.widget_config.row_groupby.push(field_name);
                }
            }
        });
        if (self.widget_config.measures.length === 0) {
            self.widget_config.measures.push('__count');
        }
    },

    do_search: function (domain, context, group_by) {
        var self = this,
            col_group_by = context.col_group_by || this.get_groupbys_from_searchview('ColGroupBy', 'col_group_by');

        if (!this.graph_widget) {
            if (group_by.length) {
                this.widget_config.row_groupby = group_by;
            }
            if (col_group_by.length) {
                this.widget_config.col_groupby = group_by;
            }
            this.graph_widget = new openerp.web_graph.Graph(this, this.model, domain, this.widget_config);
            this.graph_widget.appendTo(this.$el);
            this.ViewManager.on('switch_mode', this, function (e) {
                var col_gb = self.get_groupbys_from_searchview('ColGroupBy', 'col_group_by'),
                    row_gb = self.get_groupbys_from_searchview('GroupBy', 'group_by');

                if (e === 'graph') this.graph_widget.set(domain, row_gb, col_gb);
            });
            return;
        }

        this.graph_widget.set(domain, group_by, col_group_by);
    },

    get_groupbys_from_searchview: function (cat_name, cat_field) {
        var facet = this.search_view.query.findWhere({category:cat_name}),
            groupby_list = facet ? facet.values.models : [];
        return _.map(groupby_list, function (g) { 
            var context = g.attributes.value.attrs.context;
            if (_.isString(context)) {
                return py.eval(context).group_by;
            } else {
                return context[cat_field]; 
            }
        });
    },

    do_show: function () {
        this.do_push_state({});
        return this._super();
    },

    // ----------------------------------------------------------------------
    // Search view integration
    // ----------------------------------------------------------------------

    // add groupby to the search view
    register_groupby: function(row_groupby, col_groupby) {
        var query = this.search_view.query;

        if (!_.has(this.search_view, '_s_groupby')) { return; }

        // add row groupbys
        var row_facet = this.make_row_groupby_facets(row_groupby),
            row_search_facet = query.findWhere({category:'GroupBy'});

        if (row_search_facet) {
            row_search_facet.values.reset(row_facet.values);
        } else {
            if (row_groupby.length) {
                query.add(row_facet);
            }
        }
         // add col groupbys
        var col_facet = this.make_col_groupby_facets(col_groupby),
            col_search_facet = query.findWhere({category:'ColGroupBy'});

        if (col_search_facet) {
            col_search_facet.values.reset(col_facet.values);
        } else {
            if (col_groupby.length) {
                query.add(col_facet);
            }
        }
    },

    make_row_groupby_facets: function(groupbys) {
        return {
            category:'GroupBy',
            values: this.make_groupby_values(groupbys, 'group_by'),
            icon:'w',
            field: this.search_view._s_groupby
        };
    },

    make_col_groupby_facets: function(groupbys) {
        return {
            category:'ColGroupBy',
            values: this.make_groupby_values(groupbys, 'col_group_by'),
            icon:'f',
            field: this.col_search_field
        };
    },

    make_groupby_values: function (groupbys, category) {
        return _.map(groupbys, function (groupby) {
            var context = {};
            context[category] = groupby.field;
            var value;
            if (category === 'group_by' && groupby.type !== 'date' && groupby.type !== 'datetime') {
                value = groupby.filter || {attrs: {domain: [], context: context}};
            } else {
                value = {attrs: {domain: [], context: context}};
            }
            return {
                label: groupby.string,
                value: value
            };
        });
    },
});
};








