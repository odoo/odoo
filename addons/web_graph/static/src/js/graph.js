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
  * GraphView view.  It mostly contains a widget (PivotTable), some data, and 
  * calls to charts function.
  */
instance.web_graph.GraphView = instance.web.View.extend({
    template: 'GraphView',
    display_name: _lt('Graph'),
    view_type: 'graph',

    events: {
        'click .graph_mode_selection li' : function (event) {
            event.preventDefault();
            var mode = event.target.attributes['data-mode'].nodeValue;
            this.mode = mode;
            this.display_data();
        },

        'click .graph_measure_selection li' : function (event) {
            event.preventDefault();
            var measure = event.target.attributes['data-choice'].nodeValue;
            this.measure = (measure === '__count') ? null : measure;
            this.pivot_table.set_measure(this.measure)
                .then(this.proxy('display_data'));
        },

        'click .graph_expand_selection li' : function (event) {
            event.preventDefault();
            switch (event.target.attributes['data-choice'].nodeValue) {
                case 'fold_columns':
                    this.pivot_table.fold_cols();
                    this.display_data();
                    break;
                case 'fold_rows':
                    this.pivot_table.fold_rows();
                    this.display_data();
                    break;
                case 'fold_all':
                    this.pivot_table.fold_all();
                    this.display_data();
                    break;
                case 'expand_all':
                    this.pivot_table.expand_all().then(this.proxy('display_data'));
                    break;
            }
        },

        'click .graph_options_selection li' : function (event) {
            event.preventDefault();
            switch (event.target.attributes['data-choice'].nodeValue) {
                case 'swap_axis':
                    this.pivot_table.swap_axis();
                    this.display_data();
                    break;
                case 'update_values':
                    this.pivot_table.update_values().then(this.proxy('display_data'));
                    break;
                case 'export_data':
                    // Export code...  To do...
                    break;
            }
        },

        'click .web_graph_click' : function (event) {
            event.preventDefault();
            event.stopPropagation();
            var id = event.target.attributes['data-id'].nodeValue;
            this.handle_header_event({id:id, event:event});
        },

        'click a.field-selection' : function (event) {
            var id = event.target.attributes['data-id'].nodeValue,
                field_id = event.target.attributes['data-field-id'].nodeValue;
            event.preventDefault();
            this.pivot_table.expand(id, field_id)
                .then(this.proxy('display_data'));
        },
    },

    init: function(parent, dataset, view_id, options) {
        this._super(parent);
        this.dataset = dataset;
        this.set_default_options(options);
        this.dropdown = null;
        this.pivot_table = null;
        this.heat_map_mode = false;
        this.mode = 'pivot';
        this.measure = null;
        this.measure_list = [];
        this.important_fields = [];
    },

    start: function () {
        this.table = $('<table></table>');
        this.$('.graph_main_content').append(this.table);
        instance.web.bus.on('click', this, function (ev) {
            if (this.dropdown) {
                this.dropdown.remove();
                this.dropdown = null;
            }
        });
        return this.load_view();
    },

    view_loading: function (fields_view_get) {
        var self = this,
            model = new instance.web.Model(fields_view_get.model, {group_by_no_leaf: true}),
            row_groupby = [];

        // get the default groupbys and measure defined in the field view
        _.each(fields_view_get.arch.children, function (field) {
            if ('name' in field.attrs) {
                if ('operator' in field.attrs) {
                    self.measure_list.push(field.attrs.name);
                } else {
                    row_groupby.push(field.attrs.name);
                }
            }
        });
        if (this.measure_list.length > 0) {
            this.measure = this.measure_list[0];
        }

        // get the most important fields (of the model) by looking at the
        // groupby filters defined in the search view
        var options = {model:model, view_type: 'search'},
            deferred1 = instance.web.fields_view_get(options).then(function (search_view) {
                var groups = _.select(search_view.arch.children, function (c) {
                    return (c.tag == 'group') && (c.attrs.string != 'Display');
                });
                _.each(groups, function(g) {
                    _.each(g.children, function (g) {
                        if (g.attrs.context) {
                            var field_id = py.eval(g.attrs.context).group_by;
                            self.important_fields.push(field_id);
                        }
                    });
                });
            });

        // get the fields descriptions from the model
        var deferred2 = model.call('fields_get', []).then(function (fs) { 
            self.fields = fs; 
            var measure_selection = self.$('.graph_measure_selection');
            _.each(self.measure_list, function (measure) {
                var choice = $('<a></a>').attr('data-choice', measure)
                                         .attr('href', '#')
                                         .append(self.fields[measure].string);
                measure_selection.append($('<li></li>').append(choice));

            });
        });

        return $.when(deferred1, deferred2).then(function () {
            var data = {
                model: model,
                domain: [],
                measure: self.measure,
                col_groupby: [],
                row_groupby: row_groupby,
            };
            self.pivot_table = new openerp.web_graph.PivotTable(data);
        });
    },

    do_search: function (domain, context, group_by) {
        this.pivot_table.domain = domain;
        if (group_by.length > 0) {
            this.pivot_table.set_groupby(this.pivot_table.rows, group_by)
                    .done(this.proxy('display_data'));
        } else {
            this.pivot_table.update_values().done(this.proxy('display_data'));            
        }
    },

    do_show: function () {
        this.do_push_state({});
        return this._super();
    },

    display_data: function () {
        this.$('.graph_main_content svg').remove();
        this.table.empty();

        if (this.pivot_table.no_data) {
            var msg = 'No data available. Try to remove any filter or add some data.';
            this.table.append($('<tr><td>' + msg + '</td></tr>'));
        } else {
            var table_modes = ['pivot', 'heatmap', 'row_heatmap', 'col_heatmap'];
            if (_.contains(table_modes, this.mode)) {
                this.draw_table();
            } else {
                this.$('.graph_main_content').append($('<div><svg></svg></div>'));
                var svg = this.$('.graph_main_content svg')[0];
                openerp.web_graph.draw_chart(this.mode, this.pivot_table, svg);
            }
        }
    },

    handle_header_event: function (options) {
        var pivot = this.pivot_table,
            id = options.id,
            header = pivot.get_header(id);

        if (header.is_expanded) {
            pivot.fold(header);
            this.display_data();
        } else {
            if (header.path.length < header.root.groupby.length) {
                var field = header.root.groupby[header.path.length];
                pivot.expand(id, field).then(this.proxy('display_data'));
            } else {
                this.display_dropdown({id:header.id,
                                       target: $(options.event.target),
                                       x: options.event.pageX,
                                       y: options.event.pageY});
            }
        }
    },

    display_dropdown: function (options) {
        var self = this,
            pivot = this.pivot_table,
            already_grouped = pivot.rows.groupby.concat(pivot.cols.groupby),
            possible_groups = _.difference(self.important_fields, already_grouped),
            dropdown_options = {
                header_id: options.id,
                fields: _.map(possible_groups, function (field) {
                    return {id: field, value: self.fields[field].string};
            })};

        this.dropdown = $(QWeb.render('field_selection', dropdown_options));
        options.target.after(this.dropdown);
        this.dropdown.css({position:'absolute',
                           left:options.x,
                           top:options.y});
        this.$('.field-selection').next('.dropdown-menu').toggle();
    },

    measure_label: function () {
        return (this.measure) ? this.fields[this.measure].string : 'Quantity';
    },

    draw_table: function () {
        this.pivot_table.rows.main.title = 'Total';
        this.pivot_table.cols.main.title = this.measure_label();
        this.draw_top_headers();
        _.each(this.pivot_table.rows.headers, this.proxy('draw_row'));
    },

    make_border_cell: function (colspan, rowspan) {
        return $('<td></td>').addClass('graph_border')
                             .attr('colspan', colspan)
                             .attr('rowspan', rowspan);
    },

    make_header_title: function (header) {
        return $('<span> </span>')
            .addClass('web_graph_click')
            .attr('href', '#')
            .addClass((header.is_expanded) ? 'icon-minus-sign' : 'icon-plus-sign')
            .append((header.title !== undefined) ? header.title : 'Undefined');
    },

    draw_top_headers: function () {
        var self = this,
            pivot = this.pivot_table,
            height = _.max(_.map(pivot.cols.headers, function(g) {return g.path.length;})),
            header_cells = [[this.make_border_cell(1, height)]];

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
            var cell = self.make_border_cell(col.width, col.height);
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

        set_dim(pivot.cols.main);  // add width and height info to columns headers
        if (pivot.cols.main.children.length === 0) {
            make_cells(pivot.cols.headers, 0);
        } else {
            make_cells(pivot.cols.main.children, 1);
            header_cells[0].push(self.make_border_cell(1, height).append('Total').css('font-weight', 'bold'));
        }

        _.each(header_cells, function (cells) {
            self.table.append($('<tr></tr>').append(cells));
        });
    },

    draw_row: function (row) {
        var self = this,
            pivot = this.pivot_table,
            html_row = $('<tr></tr>'),
            row_header = this.make_border_cell(1,1)
                .append(this.make_header_title(row).attr('data-id', row.id))
                .addClass('graph_border');

        for (var i in _.range(row.path.length)) {
            row_header.prepend($('<span/>', {class:'web_graph_indent'}));
        }

        html_row.append(row_header);

        _.each(pivot.cols.headers, function (col) {
            if (col.children.length === 0) {
                var value = pivot.get_value(row.id, col.id),
                    cell = make_cell(value, col);
                html_row.append(cell);
            }
        });

        if (pivot.cols.main.children.length > 0) {
            var cell = make_cell(pivot.get_total(row), pivot.cols.main)
                            .css('font-weight', 'bold');
            html_row.append(cell);
        }

        this.table.append(html_row);

        function make_cell (value, col) {
            var color,
                total,
                cell = $('<td></td>');
            if ((self.mode === 'pivot') && (row.is_expanded) && (row.path.length <=2)) {
                color = row.path.length * 5 + 240;
                cell.css('background-color', $.Color(color, color, color));
            }
            if (value === undefined) {
                return cell;
            }
            cell.append(value);
            if (self.mode === 'heatmap') {
                total = pivot.get_total();
                color = Math.floor(50 + 205*(total - value)/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            if (self.mode === 'row_heatmap') {
                total = pivot.get_total(row);
                color = Math.floor(50 + 205*(total - value)/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            if (self.mode === 'col_heatmap') {
                total = pivot.get_total(col);
                color = Math.floor(50 + 205*(total - value)/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            return cell;
        }
    },
});

};
