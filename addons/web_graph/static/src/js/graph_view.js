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
                    self.widet_config.row_groupby.push(field.attrs.name);
                }
            }
        });
        if (self.widget_config.measures.length === 0) {
            self.widget_config.measures.push('__count');
        }
    },

    do_search: function (domain, context, group_by) {
        if (!this.graph_widget) {
            if (group_by.length) {
                this.widget_config.row_groupby = group_by;
            }
            this.graph_widget = new openerp.web_graph.Graph(this, this.model, domain, this.widget_config);
            this.graph_widget.appendTo(this.$el);
            this.graph_widget.on('groupby_changed', this, this.proxy('register_groupby'));
            this.ViewManager.on('switch_mode', this, function (e) { if (e === 'graph') this.graph_widget.reload(); });
            return;
        }

        this.graph_widget.set(domain, group_by, this.graph_widget.get_col_groupby());
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

        var row_groupby = this.graph_widget.get_row_groupby();
        var gb_facet = this.make_groupby_facets(row_groupby);
        var search_facet = query.findWhere({category:'GroupBy'});

        if (search_facet) {
            search_facet.values.reset(gb_facet.values);
        } else {
            if (row_groupby.length) {
                query.add(gb_facet);
            }
        }
    },

    make_groupby_facets: function(fields) {
        var self = this,
            values =  _.map(fields, function (field) {
                    return {
                        label: self.graph_widget.fields[field].string, 
                        value: {attrs:{domain: [], context: {group_by: field}}}
                    };
                });
        return {category:'GroupBy', values: values, icon:'w', field: self.search_view._s_groupby};
    },

    search_field: {
        get_context: function() {},
        get_domain: function () {},
        get_groupby: function () { },
    },

});


};








