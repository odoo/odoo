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
        this._super(parent, dataset, view_id, options);
        this.dataset = dataset;
        this.model = new instance.web.Model(dataset.model, {group_by_no_leaf: true});
        this.search_view = parent.searchview;
    },

    view_loading: function (fields_view_get) {
        var self = this,
            arch = fields_view_get.arch;

        this.widget_config = { 
            title: arch.attrs.string,
            stacked : (arch.attrs.stacked === 'True'),
            mode: (arch.attrs.type) ? arch.attrs.type : 'bar',
            measures: [],
            row_groupby: [],
            col_groupby: [],
        };

        _.each(arch.children, function (field) {
            if (_.has(field.attrs, 'type')) {
                switch (field.attrs.type) {
                    case 'row':
                        self.widget_config.row_groupby.push(field.attrs.name);
                        break;
                    case 'col':
                        self.widget_config.col_groupby.push(field.attrs.name);
                        break;
                    case 'measure':
                        self.widget_config.measures.push(field.attrs.name);
                        break;
                }
            } else {  // old style, kept for backward compatibility
                if ('operator' in field.attrs) {
                    self.widget_config.measures.push(field.attrs.name);
                } else {
                    self.widget_config.row_groupby.push(field.attrs.name);
                }
            }
        });
        if (self.widget_config.measures.length === 0) {
            self.widget_config.measures.push('__count');
        }
    },

    do_search: function (domain, context, group_by) {
        var col_group_by = this.get_col_groupbys_from_searchview();

        if (!this.graph_widget) {
            if (group_by.length) {
                this.widget_config.row_groupby = group_by;
            }
            if (col_group_by.length) {
                this.widget_config.col_groupby = group_by;
            }
            this.graph_widget = new openerp.web_graph.Graph(this, this.model, domain, this.widget_config);
            this.graph_widget.appendTo(this.$el);
            this.graph_widget.on('groupby_changed', this, this.proxy('register_groupby'));
            this.graph_widget.on('groupby_swapped', this, this.proxy('swap_groupby'));
            this.ViewManager.on('switch_mode', this, function (e) { if (e === 'graph') this.graph_widget.reload(); });
            return;
        }

        if (this.swapped) {
            this.swapped = false;
            return;
        }

        this.graph_widget.set(domain, group_by, col_group_by);
    },

    get_col_groupbys_from_searchview: function () {
        var facet = this.search_view.query.findWhere({category:'ColGroupBy'}),
            groupby_list = facet ? facet.values.models : [];
        return _.map(groupby_list, function (g) { return g.attributes.value.attrs.context.col_group_by; });
    },

    do_show: function () {
        this.do_push_state({});
        return this._super();
    },

    // ----------------------------------------------------------------------
    // Search view integration
    // ----------------------------------------------------------------------

    // add groupby to the search view
    register_groupby: function() {
        var query = this.search_view.query;

        if (!_.has(this.search_view, '_s_groupby')) { return; }

        // add row groupbys
        var row_groupby = this.graph_widget.get_row_groupby(),
            row_facet = this.make_row_groupby_facets(row_groupby),
            row_search_facet = query.findWhere({category:'GroupBy'});

        if (row_search_facet) {
            row_search_facet.values.reset(row_facet.values);
        } else {
            if (row_groupby.length) {
                query.add(row_facet);
            }
        }
         // add col groupbys
        var col_groupby = this.graph_widget.get_col_groupby(),
            col_facet = this.make_col_groupby_facets(col_groupby),
            col_search_facet = query.findWhere({category:'ColGroupBy'});

        if (col_search_facet) {
            col_search_facet.values.reset(col_facet.values);
        } else {
            if (col_groupby.length) {
                query.add(col_facet);
            }
        }
    },

    swap_groupby: function () {
        this.swap = true;
        this.register_groupby();
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
            field: this.search_field
        };
    },

    make_groupby_values: function (groupbys, category) {
        return _.map(groupbys, function (groupby) {
            var context = {};
            context[category] = groupby.field;
            return {
                label: groupby.string, 
                value: {attrs:{domain: [], context: context}}
            };
        });
    },

    search_field: {
        get_context: function() {},
        get_domain: function () {},
        get_groupby: function () {},
    },

});

};








