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
            arch = fields_view_get.arch,
            measures = [],
            stacked = false;

        this.widget_config = { title: arch.attrs.string };

        debugger;
        if (!_.has(arch.attrs, 'type')) {
            this.widget_config.mode = 'bar_chart';
        } else {
            switch (arch.attrs.type) {
                case 'bar':
                    this.widget_config.mode = 'bar_chart';
                    break;
                case 'pie':
                    this.widget_config.mode = 'pie_chart';
                    break;
                case 'line':
                    this.widget_config.mode = 'line_chart';
                    break;
                case 'pivot':
                case 'heatmap':
                case 'row_heatmap':
                case 'col_heatmap':
                    this.widget_config.mode = arch.attrs.type;
                    break;
            }
        }

        if (arch.attrs.stacked === 'True') {
            this.widget_config.stacked = true;
        }

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
                        measures.push(field.attrs.name);
                        break;
                }
            } else {  // old style, kept for backward compatibility
                if ('operator' in field.attrs) {
                    measures.push(field.attrs.name);
                } else {
                    self.default_row_groupby.push(field.attrs.name);
                }
            }
        });
        if (measures.length === 0) {
            measures.push('__count');
        }
        this.widget_config.row_groupby = self.default_row_groupby;
        this.widget_config.col_groupby = self.default_col_groupby;
        this.widget_config.measures = measures;
        //     measures:measures,
        //     update:false,
        //     title: title,
        //     bar_ui: (stacked) ? 'stack' : 'group'
        // });
    },

    get_context: function (facet) {
        var col_group_by = _.map(facet.values.models, function (model) {
            return model.attributes.value.attrs.context.col_group_by;
        });
        return {col_group_by : col_group_by};
    },

    do_search: function (domain, context, group_by) {
        var col_groupby = context.col_group_by || [],
            options = {domain:domain};

        if (!this.graph_widget) {
            this.graph_widget = new openerp.web_graph.Graph(this, this.model, domain, this.widget_config);
            this.graph_widget.appendTo(this.$el);
            this.graph_widget.on('groupby_changed', this, this.proxy('register_groupby'));
        }
        this.search_view_groupby = group_by;

        if (group_by.length && this.groupby_mode !== 'manual') {
            if (_.isEqual(col_groupby, [])) {
                col_groupby = this.default_col_groupby;
            }
        }
        if (group_by.length || col_groupby.length) {
            this.groupby_mode = 'manual';
        }
        if (!this.graph_widget.enabled) {
            options.update = false;
            options.silent = true;
        }

        if (this.groupby_mode === 'manual') {
            options.row_groupby = group_by;
            options.col_groupby = col_groupby;
        } else {
            options.row_groupby = _.toArray(this.default_row_groupby);
            options.col_groupby = _.toArray(this.default_col_groupby);
        }
        this.graph_widget.set_domain(domain);
        this.graph_widget.set_col_groupby(options.col_groupby);
        this.graph_widget.set_row_groupby(options.row_groupby);

        // this.graph_widget.pivot.config(options);

        if (!this.graph_widget.enabled) {
            this.graph_widget.activate_display();
            this.ViewManager.on('switch_mode', this, function () {this.graph_widget.pivot.update_data(); });
        }
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

// important_fields = [field], field = {field: _,type: _, string: _}
instance.web_graph.Graph = instance.web.Widget.extend(openerp.EventDispatcherMixin, {
    template: 'GraphWidget',

    events: {
        'click .graph_mode_selection li' : 'mode_selection',
        'click .graph_measure_selection li' : 'measure_selection',
        'click .graph_options_selection li' : 'option_selection',
        'click .web_graph_click' : 'header_cell_clicked',
        'click a.field-selection' : 'field_selection',
    },

    init: function(parent, model,  domain, options) {
        var self = this;

        this._super(parent);
        this.model = model;
        this.domain = domain;
        this.mode = options.mode || 'pivot';
        this.title = options.title || 'Graph';
        this.visible_ui = options.visible_ui || true;
        this.pivot_options = options;
    },

    start: function() {
        var self = this;
        this.table = $('<table></table>');
        this.$('.graph_main_content').append(this.table);
        var def1 = this.get_search_fields().then(function (f) {
            self.important_fields = f;
        });

        var def2 = this.get_model_fields().then(function (f) {
            self.fields = f;
            self.measure_list = self.get_measures();
            self.add_measures_to_options();
        });

        $.when(def1, def2).then(function () {
            self.pivot = new openerp.web_graph.PivotTable(self.model, self.domain, self.fields, self.pivot_options);
            self.pivot.on('redraw_required', self, self.proxy('display_data'));
            self.pivot.on('groupby_changed', self, function () { self.trigger('groupby_changed'); });
            instance.web.bus.on('click', self, function () {
                if (self.dropdown) {
                    self.dropdown.remove();
                    self.dropdown = null;
                }
            });
            self.pivot.activate();
        });
    },

    get_search_fields: function () {
        var self = this,
            options = {model:this.model, view_type: 'search'},
            result = [];

        return instance.web.fields_view_get(options).then(function (search_view) {
            var groups = _.select(search_view.arch.children, function (c) {
                return (c.tag === 'group') && (c.attrs.string != 'Display');
            });
            _.each(groups, function(g) {
                _.each(g.children, function (g) {
                    if (g.attrs.context) {
                        var field_id = py.eval(g.attrs.context).group_by;
                        if (field_id) {
                            if (field_id instanceof Array) {
                                result.concat(field_id);
                            } else {
                                result.push(field_id);
                            }
                        }
                    }
                });
            });
            return result;
        });
    },

    get_model_fields: function () {
        return this.model.call('fields_get', []).then(function (fs) {
            return fs;
        });
    },

    get_measures: function(fields) {
        var measures = [];
        _.each(this.fields, function (f, id) {
            if (((f.type === 'integer') || (f.type === 'float')) && (id !== 'id')) {
                measures.push({field:id, type: f.type, string: f.string});
            }
        });
        return measures;
    },

    set_domain: function (domain) {
        if (this.pivot) {
            this.pivot.set_domain(domain);
        } else {
            this.pivot_options.domain = domain;
        }
    },

    set_row_groupby: function (groupby) {
        if (this.pivot) {
            this.pivot.set_row_groupby(groupby);
        } else {
            this.pivot_options.row_groupby = groupby;
        }
    },

    set_col_groupby: function (groupby) {
        if (this.pivot) {
            this.pivot.set_col_groupby(groupby);
        } else {
            this.pivot_options.col_groupby = groupby;
        }
    },

    add_measures_to_options: function() {
        var measure_selection = this.$('.graph_measure_selection');
        _.each(this.measure_list, function (measure) {
            var choice = $('<a></a>').attr('data-choice', measure.field)
                                     .attr('href', '#')
                                     .append(measure.string);
            measure_selection.append($('<li></li>').append(choice));
        });
    },

    //         self.fields = fs;
    //         var temp = _.map(fs, function (field, name) {
    //             return {name:name, type: field.type};
    //         });
    //         temp = _.filter(temp, function (field) {
    //             return (((field.type === 'integer') || (field.type === 'float')) && (field.name !== 'id'));
    //         });
    //         self.measure_list = _.map(temp, function (field) {
    //             return field.name;
    //         });

    //         var measure_selection = self.$('.graph_measure_selection');
    //         _.each(self.measure_list, function (measure) {
    //             var choice = $('<a></a>').attr('data-choice', measure)
    //                                      .attr('href', '#')
    //                                      .append(self.fields[measure].string);
    //             measure_selection.append($('<li></li>').append(choice));
    //         });
    //     });
    // },

    // hide ui/show, stacked/grouped
    // config: function (options) {
        // Possible modes: pivot, heatmap, row_heatmap, col_heatmap,
        //                 bar_chart, pie_chart, line_chart
        // if (_.has(options, 'mode')) { this.mode = mode; }
        // if (_.has(options, 'visible_ui')) {
        //     this.visible_ui = options.visible_ui;
        // }
        // if (_.has(options, 'bar_ui')) {
        //     this.bar_ui = options.bar_ui;
        // }
        // if (_.has(options, 'title')) {
        //     this.title = options.title;
        // }
        // debugger;
        // this.pivot.config(options);
    // },


        // get the most important fields (of the model) by looking at the
        // groupby filters defined in the search view

        // get the fields descriptions and measure list from the model

    //     return $.when(deferred1, deferred2).then(function () {
    //         self.pivot = new openerp.web_graph.PivotTable(self.model, self.fields);
    //         self.activate_display();
    //     });
    // },

    set_mode: function (mode) {

    },

    activate_display: function () {
    },

    display_data: function () {
        this.$('.graph_main_content svg').remove();
        this.$('.graph_main_content div').remove();
        this.table.empty();

        if (this.visible_ui) {
            this.$('.graph_header').css('display', 'block');
        } else {
            this.$('.graph_header').css('display', 'none');
        }
        if (this.pivot.no_data) {
            this.$('.graph_main_content').append($(QWeb.render('graph_no_data')));
        } else {
            var table_modes = ['pivot', 'heatmap', 'row_heatmap', 'col_heatmap'];
            if (_.contains(table_modes, this.mode)) {
                this.draw_table();
            } else {
                this.$('.graph_main_content').append($('<div><svg></svg></div>'));
                this.svg = this.$('.graph_main_content svg')[0];
                this.width = this.$el.width();
                this.height = Math.min(Math.max(document.documentElement.clientHeight - 116 - 60, 250), Math.round(0.8*this.$el.width()));
                this[this.mode]();
            }
        }
    },

    mode_selection: function (event) {
        event.preventDefault();
        var mode = event.target.attributes['data-mode'].nodeValue;
        this.mode = mode;
        this.display_data();
    },

    measure_selection: function (event) {
        event.preventDefault();
        var measure = event.target.attributes['data-choice'].nodeValue;
        this.pivot.toggle_measure(measure);
    },

    option_selection: function (event) {
        event.preventDefault();
        switch (event.target.attributes['data-choice'].nodeValue) {
            case 'bar_grouped':
                this.bar_ui = 'group';
                if (this.mode === 'bar_chart') {
                    this.display_data();
                }
                break;
            case 'bar_stacked':
                this.bar_ui = 'stack';
                if (this.mode === 'bar_chart') {
                    this.display_data();
                }
                break;
            case 'swap_axis':
                this.pivot.swap_axis();
                break;
            case 'expand_all':
                this.pivot.rows.headers = null;
                this.pivot.cols.headers = null;
                this.pivot.update_data();
                break;
            case 'update_values':
                this.pivot.update_data();
                break;
            case 'export_data':
                // Export code...  To do...
                break;
        }
    },

    header_cell_clicked: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var id = event.target.attributes['data-id'].nodeValue,
            header = this.pivot.get_header(id),
            self = this;

        if (header.expanded) {
            this.pivot.fold(header);
        } else {
            if (header.path.length < header.root.groupby.length) {
                this.pivot.expand(id);
            } else {
                if (!this.important_fields.length) {
                    return;
                }
                var fields = _.map(this.important_fields, function (field) {
                        return {id: field, value: self.fields[field].string};
                });
                this.dropdown = $(QWeb.render('field_selection', {fields:fields, header_id:id}));
                $(event.target).after(this.dropdown);
                this.dropdown.css({position:'absolute',
                                   left:event.pageX,
                                   top:event.pageY});
                this.$('.field-selection').next('.dropdown-menu').toggle();
            }
        }
    },

    field_selection: function (event) {
        var id = event.target.attributes['data-id'].nodeValue,
            field_id = event.target.attributes['data-field-id'].nodeValue;
        event.preventDefault();
        this.pivot.expand(id, field_id);
    },

/******************************************************************************
 * Drawing pivot table methods...
 ******************************************************************************/
    draw_table: function () {
        this.pivot.main_row().title = 'Total';
        if (this.pivot.measures.length == 1) {
            this.pivot.main_col().title = this.pivot.measures[0].string;
        } else {
            this.pivot.main_col().title = this.title;
        }
        this.draw_top_headers();
        _.each(this.pivot.rows.headers, this.proxy('draw_row'));
    },

    make_border_cell: function (colspan, rowspan, headercell) {
        var tag = (headercell) ? $('<th></th>') : $('<td></td>');
        return tag.addClass('graph_border')
                             .attr('colspan', (colspan) ? colspan : 1)
                             .attr('rowspan', (rowspan) ? rowspan : 1);
    },

    make_header_title: function (header) {
        return $('<span> </span>')
            .addClass('web_graph_click')
            .attr('href', '#')
            .addClass((header.expanded) ? 'fa fa-minus-square' : 'fa fa-plus-square')
            .append((header.title !== undefined) ? header.title : 'Undefined');
    },

    draw_top_headers: function () {
        var self = this,
            thead = $('<thead></thead>'),
            pivot = this.pivot,
            height = _.max(_.map(pivot.cols.headers, function(g) {return g.path.length;})),
            header_cells = [[this.make_border_cell(1, height, true)]];

        function set_dim (cols) {
            _.each(cols.children, set_dim);
            if (cols.children.length === 0) {
                cols.height = height - cols.path.length + 1;
                cols.width = 1;
            } else {
                cols.height = 1;
                cols.width = _.reduce(cols.children, function (sum,c) { return sum + c.width;}, 0);
            }
        }

        function make_col_header (col) {
            var cell = self.make_border_cell(col.width*pivot.measures.length, col.height, true);
            return cell.append(self.make_header_title(col).attr('data-id', col.id));
        }

        function make_cells (queue, level) {
            var col = queue[0];
            queue = _.rest(queue).concat(col.children);
            if (col.path.length == level) {
                _.last(header_cells).push(make_col_header(col));
            } else {
                level +=1;
                header_cells.push([make_col_header(col)]);
            }
            if (queue.length !== 0) {
                make_cells(queue, level);
            }
        }

        set_dim(pivot.main_col());  // add width and height info to columns headers
        if (pivot.main_col().children.length === 0) {
            make_cells(pivot.cols.headers, 0);
        } else {
            make_cells(pivot.main_col().children, 1);
            if (pivot.get_cols_leaves().length > 1) {
                header_cells[0].push(self.make_border_cell(pivot.measures.length, height, true).append('Total').css('font-weight', 'bold'));
            }
        }

        _.each(header_cells, function (cells) {
            thead.append($('<tr></tr>').append(cells));
        });
        
        if (pivot.measures.length >= 2) {
            thead.append(self.make_measure_row());
        }

        self.table.append(thead);
    },

    make_measure_row: function() {
        var self = this,
            measures = this.pivot.measures,
            cols = this.pivot.cols.headers,
            measure_cells,
            measure_row = $('<tr></tr>');

        measure_row.append($('<th></th>'));

        _.each(cols, function (col) {
            if (!col.children.length) {
                for (var i = 0; i < measures.length; i++) {
                    measure_cells = $('<th></th>').addClass('measure_row');
                    measure_cells.append(measures[i].string);
                    measure_row.append(measure_cells);
                }
            }
        });

        if (this.pivot.get_cols_leaves().length > 1) {
            for (var i = 0; i < measures.length; i++) {
                measure_cells = $('<th></th>').addClass('measure_row');
                measure_cells.append(measures[i].string);
                measure_row.append(measure_cells);
            }
        }
        return measure_row;
    },

    draw_row: function (row) {
        var self = this,
            pivot = this.pivot,
            measure_types = _.pluck(this.pivot.measures, 'type'),
            html_row = $('<tr></tr>'),
            row_header = this.make_border_cell(1,1)
                .append(this.make_header_title(row).attr('data-id', row.id))
                .addClass('graph_border');

        for (var i = 0; i < row.path.length; i++) {
            row_header.prepend($('<span/>', {class:'web_graph_indent'}));
        }

        html_row.append(row_header);

        _.each(pivot.cols.headers, function (col) {
            if (col.children.length === 0) {
                var values = pivot.get_values(row.id, col.id);
                for (var i = 0; i < values.length; i++) {
                    html_row.append(make_cell(values[i], measure_types[i], i, col));
                }
            }
        });

        if (pivot.get_cols_leaves().length > 1) {
            var total_vals = pivot.get_total(row);
            for (var j = 0; j < total_vals.length; j++) {
                var cell = make_cell(total_vals[j], measure_types[j], j, pivot.cols[0]).css('font-weight', 'bold');
                html_row.append(cell);
            }
        }

        this.table.append(html_row);

        function make_cell (value, measure_type, index, col) {
            var color,
                total,
                cell = $('<td></td>');
            if (value === undefined) {
                return cell;
            }
            cell.append(instance.web.format_value(value, {type: measure_type}));
            if (self.mode === 'heatmap') {
                total = pivot.get_total()[index];
                color = Math.floor(90 + 165*(total - Math.abs(value))/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            if (self.mode === 'row_heatmap') {
                total = pivot.get_total(row)[index];
                color = Math.floor(90 + 165*(total - Math.abs(value))/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            if (self.mode === 'col_heatmap') {
                debugger;
                total = pivot.get_total(col)[index];
                color = Math.floor(90 + 165*(total - Math.abs(value))/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            return cell;
        }
    },

/******************************************************************************
 * Drawing charts methods...
 ******************************************************************************/
    bar_chart: function () {
        var self = this,
            dim_x = this.pivot.rows.groupby.length,
            dim_y = this.pivot.cols.groupby.length,
            data;

        // No groupby **************************************************************
        if ((dim_x === 0) && (dim_y === 0)) {
            data = [{key: 'Total', values:[{
                x: 'Total',
                y: this.pivot.get_total(),
            }]}];
        // Only column groupbys ****************************************************
        } else if ((dim_x === 0) && (dim_y >= 1)){
            data =  _.map(this.pivot.get_columns_with_depth(1), function (header) {
                return {
                    key: header.title,
                    values: [{x:header.root[0].title, y: self.pivot.get_total(header)[0]}]
                };
            });
        // Just 1 row groupby ******************************************************
        } else if ((dim_x === 1) && (dim_y === 0))  {
            data = _.map(this.pivot.main_row().children, function (pt) {
                var value = self.pivot.get_total(pt),
                    title = (pt.title !== undefined) ? pt.title : 'Undefined';
                return {x: title, y: value};
            });
            data = [{key: self.pivot.measures[0].string, values:data}];
        // 1 row groupby and some col groupbys**************************************
        } else if ((dim_x === 1) && (dim_y >= 1))  {
            data = _.map(this.pivot.get_cols_with_depth(1), function (colhdr) {
                var values = _.map(self.pivot.get_rows_with_depth(1), function (header) {
                    return {
                        x: header.title || 'Undefined',
                        y: self.pivot.get_values(header.id, colhdr.id, 0)[0]
                    };
                });
                return {key: colhdr.title || 'Undefined', values: values};
            });
        // At least two row groupby*************************************************
        } else {
            var keys = _.uniq(_.map(this.pivot.get_rows_with_depth(2), function (hdr) {
                return hdr.title || 'Undefined';
            }));
            data = _.map(keys, function (key) {
                var values = _.map(self.pivot.get_rows_with_depth(1), function (hdr) {
                    var subhdr = _.find(hdr.children, function (child) {
                        return ((child.title === key) || ((child.title === undefined) && (key === 'Undefined')));
                    });
                    return {
                        x: hdr.title || 'Undefined',
                        y: (subhdr) ? self.pivot.get_total(subhdr)[0] : 0
                    };
                });
                return {key:key, values: values};
            });
        }

        nv.addGraph(function () {
          var chart = nv.models.multiBarChart()
                .width(self.width)
                .height(self.height)
                .reduceXTicks(false)
                .stacked(self.bar_ui === 'stack')
                .showControls(false);

            if (self.width / data[0].values.length < 80) {
                chart.rotateLabels(-15);
                chart.reduceXTicks(true);
                chart.margin({bottom:40});
            }

            d3.select(self.svg)
                .datum(data)
                .attr('width', self.width)
                .attr('height', self.height)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });

    },

    line_chart: function () {
        var self = this,
            dim_x = this.pivot.rows.groupby.length,
            dim_y = this.pivot.cols.groupby.length;

        var data = _.map(this.pivot.get_cols_leaves(), function (col) {
            var values = _.map(self.pivot.get_rows_with_depth(dim_x), function (row) {
                return {x: row.title, y: self.pivot.get_values(row.id,col.id, 0)};
            });
            var title = _.map(col.path, function (p) {
                return p || 'Undefined';
            }).join('/');
            if (dim_y === 0) {
                title = self.pivot.measures[0].string;
            }
            return {values: values, key: title};
        });

        nv.addGraph(function () {
            var chart = nv.models.lineChart()
                .x(function (d,u) { return u; })
                .width(self.width)
                .height(self.height)
                .margin({top: 30, right: 20, bottom: 20, left: 60});

            d3.select(self.svg)
                .attr('width', self.width)
                .attr('height', self.height)
                .datum(data)
                .call(chart);

            return chart;
          });
    },

    pie_chart: function () {
        var self = this,
            dim_x = this.pivot.rows.groupby.length;
        debugger;
        var data = _.map(this.pivot.get_rows_leaves(), function (row) {
            var title = _.map(row.path, function (p) {
                return p || 'Undefined';
            }).join('/');
            if (dim_x === 0) {
                title = self.measure_label;
            }
            return {x: title, y: self.pivot.get_total(row)};
        });

        nv.addGraph(function () {
            var chart = nv.models.pieChart()
                .color(d3.scale.category10().range())
                .width(self.width)
                .height(self.height);

            d3.select(self.svg)
                .datum(data)
                .transition().duration(1200)
                .attr('width', self.width)
                .attr('height', self.height)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    },

});

};








