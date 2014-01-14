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

    init: function(parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
        this.dataset = dataset;
        this.model = new instance.web.Model(dataset.model, {group_by_no_leaf: true});
        this.search_view = parent.searchview;
        this.search_view_groupby = [];
        this.groupby_mode = 'default';  // 'default' or 'manual'
        this.default_row_groupby = [];
        this.default_col_groupby = [];
        this.search_field = {
            get_context: this.proxy('get_context'),
            get_domain: function () {},
            get_groupby: function () { },
        };
    },

    view_loading: function (fields_view_get) {
        var self = this,
            arch = fields_view_get.arch;

        this.widget_config = { 
            title: arch.attrs.string,
            stacked : (arch.attrs.stacked === 'True'),
            mode: (arch.attrs.type) ? arch.attrs.type : 'bar',
            measures: [],
        };

        _.each(arch.children, function (field) {
            if (_.has(field.attrs, 'type')) {
                switch (field.attrs.type) {
                    case 'row':
                        self.default_row_groupby.push(field.attrs.name);
                        break;
                    case 'col':
                        self.default_col_groupby.push(field.attrs.name);
                        break;
                    case 'measure':
                        self.widget_config.measures.push(field.attrs.name);
                        break;
                }
            } else {  // old style, kept for backward compatibility
                if ('operator' in field.attrs) {
                    self.widget_config.measures.push(field.attrs.name);
                } else {
                    self.default_row_groupby.push(field.attrs.name);
                }
            }
        });
        if (self.widget_config.measures.length === 0) {
            self.widget_config.measures.push('__count');
        }
        this.widget_config.row_groupby = self.default_row_groupby;
        this.widget_config.col_groupby = self.default_col_groupby;
    },

    get_context: function (facet) {
        var col_group_by = _.map(facet.values.models, function (model) {
            return model.attributes.value.attrs.context.col_group_by;
        });
        return {col_group_by : col_group_by};
    },

    do_search: function (domain, context, group_by) {
        // var col_groupby = context.col_group_by || [],
        //     options = {domain:domain};

        if (!this.graph_widget) {
            this.graph_widget = new openerp.web_graph.Graph(this, this.model, domain, this.widget_config);
            this.graph_widget.appendTo(this.$el);
            this.graph_widget.on('groupby_changed', this, this.proxy('register_groupby'));
            this.ViewManager.on('switch_mode', this, function (e) { if (e === 'graph') this.graph_widget.reload(); });
        }
        // this.search_view_groupby = group_by;

        // if (group_by.length && this.groupby_mode !== 'manual') {
        //     if (_.isEqual(col_groupby, [])) {
        //         col_groupby = this.default_col_groupby;
        //     }
        // }
        // if (group_by.length || col_groupby.length) {
        //     this.groupby_mode = 'manual';
        // }
        // if (!this.graph_widget.enabled) {
        //     options.update = false;
        //     options.silent = true;
        // }

        // if (this.groupby_mode === 'manual') {
        //     options.row_groupby = group_by;
        //     options.col_groupby = col_groupby;
        // } else {
        //     options.row_groupby = _.toArray(this.default_row_groupby);
        //     options.col_groupby = _.toArray(this.default_col_groupby);
        // }
        // this.graph_widget.set(domain, options.row_groupby, options.col_groupby);
        // this.graph_widget.set_domain(domain);
        // this.graph_widget.set_col_groupby(options.col_groupby);
        // this.graph_widget.set_row_groupby(options.row_groupby);

    },

    do_show: function () {
        this.do_push_state({});
        return this._super();
    },

    register_groupby: function() {
        // var self = this,
        //     query = this.search_view.query;

        // this.groupby_mode = 'manual';
        // if (_.isEqual(this.search_view_groupby, this.graph_widget.pivot.rows.groupby) ||
        //     (!_.has(this.search_view, '_s_groupby'))) {
        //     return;
        // }
        // var rows = _.map(this.graph_widget.pivot.rows.groupby, function (group) {
        //     return make_facet('GroupBy', group);
        // });
        // var cols = _.map(this.graph_widget.pivot.cols.groupby, function (group) {
        //     return make_facet('ColGroupBy', group);
        // });

        // query.reset(rows.concat(cols));

        // function make_facet (category, fields) {
        //     var values,
        //         icon,
        //         backbone_field,
        //         cat_name;
        //     if (!(fields instanceof Array)) { fields = [fields]; }
        //     if (category === 'GroupBy') {
        //         cat_name = 'group_by';
        //         icon = 'w';
        //         backbone_field = self.search_view._s_groupby;
        //     } else {
        //         cat_name = 'col_group_by';
        //         icon = 'f';
        //         backbone_field = self.search_field;
        //     }
        //     values =  _.map(fields, function (field) {
        //         var context = {};
        //         context[cat_name] = field;
        //         return {label: self.graph_widget.fields[field].string, value: {attrs:{domain: [], context: context}}};
        //     });
        //     return {category:category, values: values, icon:icon, field: backbone_field};
        // }
    },
});


};








