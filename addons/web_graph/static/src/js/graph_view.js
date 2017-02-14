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
            get_context: function() { return { col_group_by: self.graph_widget.get_col_groupbys(),
                measures: self.graph_widget.get_current_measures()};},
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
            //noinspection FallThroughInSwitchStatementJS
            switch (field.attrs.type) {
            case 'measure':
                self.widget_config.measures.push(field_name);
                break;
            case 'col':
                self.widget_config.col_groupby.push(field_name);
                break;
            default:
                if ('operator' in field.attrs) {
                    self.widget_config.measures.push(field_name);
                    break;
                }
            case 'row':
                self.widget_config.row_groupby.push(field_name);
            }
        });
        if (self.widget_config.measures.length === 0) {
            self.widget_config.measures.push('__count');
        }
    },

    do_search: function (domain, context, group_by) {
        if (this.ignore_do_search) {
            this.ignore_do_search = false;
            return;
        }
        var self = this,
            groupbys = this.get_groupbys_from_searchview(),
            col_group_by = groupbys.col_group_by,
            measures = groupbys.measures;
        // Do not forward-port
        if(measures.length === 0 && context.measures) {
            measures = context.measures;
        }

        if (!this.graph_widget) {
            this.widget_config.context = _.clone(context);
            this.widget_config.context.group_by_no_leaf = true;
            if (group_by.length) {
                this.widget_config.row_groupby = group_by;
            }
            if (col_group_by.length) {
                this.widget_config.col_groupby = col_group_by;
            }
            if (measures.length) {
                this.widget_config.measures = measures;
            }
            this.graph_widget = new openerp.web_graph.Graph(this, this.model, domain, this.widget_config);
            this.graph_widget.appendTo(this.$el);
            this.ViewManager.on('switch_mode', this, function (e) {
                if (e === 'graph') {
                    var group_bys = self.get_groupbys_from_searchview();
                    this.graph_widget.set(domain, group_bys.group_by, group_bys.col_group_by, group_bys.measures);
                }
            });
            return;
        }

        this.graph_widget.set(domain, group_by, col_group_by, measures);
    },

    get_groupbys_from_searchview: function () {
        var result = { group_by: [], col_group_by: [], measures: []},
            searchdata = this.search_view.build_search_data();

        _.each(searchdata.groupbys, function (data) {
            data = (_.isString(data)) ? py.eval(data) : data;
            result.group_by = result.group_by.concat(data.group_by);
            if (data.col_group_by) {
                result.col_group_by = result.col_group_by.concat(data.col_group_by);
            }
            if (data.measures) {
                result.measures = result.measures.concat(data.measures);
            }
        });

        if (result.col_group_by.length) {
            return result;
        }
        _.each(searchdata.contexts, function (context) {
            if (context.col_group_by) {
                result.col_group_by = result.col_group_by.concat(context.col_group_by);
            }
            if (context.measures) {
                result.measures = result.measures.concat(context.measures);
            }
        });
        return result;
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
        var query = this.search_view.query,
            groupbys = this.get_groupbys_from_searchview(),
            search_row_groupby = groupbys.group_by,
            search_col_groupby = groupbys.col_group_by,
            search_measures = groupbys.measures,
            row_gb_changed = !_.isEqual(_.pluck(row_groupby, 'field'), search_row_groupby),
            col_gb_changed = !_.isEqual(_.pluck(col_groupby, 'field'), search_col_groupby),
            measures_gb_changed = !_.isEqual(_.pluck(col_groupby, 'field'), search_col_groupby);
        if (!_.has(this.search_view, '_s_groupby')) { return; }

        if (!row_gb_changed && !col_gb_changed) {
            return;
        }

        var custom_groups = this.get_custom_filter_groupbys();
        row_groupby = row_groupby.slice(custom_groups.groupby.length);
        col_groupby = col_groupby.slice(custom_groups.col_groupby.length);

        if (row_gb_changed && col_gb_changed) {
            // when two changes to the search view will be done, the method do_search
            // will be called twice, once with the correct groupby and incorrect col_groupby,
            // and once with correct informations. This flag is necessary to prevent the 
            // incorrect informations to propagate and trigger useless queries
            this.ignore_do_search = true;
        }

        if (row_gb_changed) {
            // add row groupbys
            var row_facet = this.make_row_groupby_facets(row_groupby),
                row_search_facet = query.findWhere({category:'GroupBy'});

            if (row_search_facet) {
                row_search_facet.values.reset(row_facet.values, {focus_input:false});
            } else {
                if (row_groupby.length) {
                    query.add(row_facet);
                }
            }
        }

        if (col_gb_changed) {
            // add col groupbys
            var col_facet = this.make_col_groupby_facets(col_groupby),
                col_search_facet = query.findWhere({category:'ColGroupBy'});

            if (col_search_facet) {
                col_search_facet.values.reset(col_facet.values, {focus_input:false});
            } else {
                if (col_groupby.length) {
                    query.add(col_facet);
                }
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

    get_custom_filter_groupbys: function () {
        var gb = [],
            col_gb = [];

        var facet = this.search_view.query.at(0);
        if (facet) {
            if (facet.get('category') !== 'GroupBy' && facet.get('category') !== 'ColGroupBy') {
                gb = get_groupby(facet);
                col_gb = get_col_groupby(facet);
            }
        }
        return {
            groupby: gb,
            col_groupby: col_gb,
        }
    }

});

function get_groupby(facet) {
    var field = facet.get('field'),
        result = [];
    if ('get_groupby' in field) {
        result = instance.web.pyeval.sync_eval_domains_and_contexts({
            group_by_seq: field.get_groupby(facet)
        }).group_by;
    }
    return result;
}
function get_col_groupby(facet) {
    var field = facet.get('field'),
        result = [];
    if ('get_context' in field) {
        result = instance.web.pyeval.sync_eval_domains_and_contexts({
            contexts: field.get_context(facet)
        }).context.col_group_by || [];
    }
    return result;
}


};
