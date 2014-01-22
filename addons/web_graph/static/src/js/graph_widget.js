
/* jshint undef: false  */

(function () {
'use strict';
var QWeb = openerp.web.qweb;
nv.dev = false;  // sets nvd3 library in production mode

openerp.web_graph.Graph = openerp.web.Widget.extend({
    template: 'GraphWidget',

    // ----------------------------------------------------------------------
    // Init stuff
    // ----------------------------------------------------------------------
    init: function(parent, model,  domain, options) {
        this._super(parent);
        this.model = model;
        this.domain = domain;
        this.mode = options.mode || 'pivot';  // pivot, bar, pie, line
        this.heatmap_mode = options.heatmap_mode || 'none';
        this.title = options.title || 'Graph';
        this.visible_ui = options.visible_ui || true;
        this.bar_ui = options.bar_ui || 'group';
        this.graph_view = options.graph_view || null;
        this.pivot_options = options;
        this.important_fields = this.get_search_fields();
    },

    start: function() {
        var self = this;
        this.table = $('<table></table>');
        this.$('.graph_main_content').append(this.table);

        var index = 0;
        if (this.mode === 'bar') { index = 1; }
        if (this.mode === 'line') { index = 2; }
        if (this.mode === 'chart') { index = 3; }
        this.$('.graph_mode_selection label').eq(index).addClass('active');

        if (this.mode !== 'pivot') {
            this.$('.graph_heatmap label').addClass('disabled');
        }

        return this.model.call('fields_get', []).then(function (f) {
            self.fields = f;
            self.measure_list = self.get_measures();
            self.add_measures_to_options();
            self.pivot_options.row_groupby = self.create_field_values(self.pivot_options.row_groupby || []);
            self.pivot_options.col_groupby = self.create_field_values(self.pivot_options.col_groupby || []);
            self.pivot_options.measures = self.create_field_values(self.pivot_options.measures || [{field:'__count', type: 'integer', string:'Quantity'}]);
            self.pivot = new openerp.web_graph.PivotTable(self.model, self.domain, self.fields, self.pivot_options);
            self.pivot.update_data().then(function () {
                self.display_data();
                if (self.graph_view) {
                    self.graph_view.register_groupby(self.pivot.rows.groupby, self.pivot.cols.groupby);
                }
            });
            openerp.web.bus.on('click', self, function () {
                if (self.dropdown) {
                    self.dropdown.remove();
                    self.dropdown = null;
                }
            });
            self.put_measure_checkmarks();
        });
    },

    // this method gets the fields that appear in the search view, under the 
    // 'Groupby' heading
    get_search_fields: function () {
        var search_view = openerp.client.action_manager.inner_widget.searchview;

        var groupbygroups = _(search_view.inputs).select(function (g) {
            return g instanceof openerp.web.search.GroupbyGroup;
        });

        var filters = [].concat.apply([], _.pluck(groupbygroups, 'filters'));

        return _.map(filters, function (filter) {
            return {
                field: py.eval(filter.attrs.context).group_by,
                string: filter.attrs.string,
                filter: filter
            };
        });
    },

    // Extracts the integer/float fields which are not 'id'
    get_measures: function() {
        var measures = [{field:'__count', type: 'integer', string:'Quantity'}];
        _.each(this.fields, function (f, id) {
            if (((f.type === 'integer') || (f.type === 'float')) && (id !== 'id')) {
                measures.push({field:id, type: f.type, string: f.string});
            }
        });
        return measures;
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

    // ----------------------------------------------------------------------
    // Configuration methods
    // ----------------------------------------------------------------------
    set: function (domain, row_groupby, col_groupby) {
        if (!this.pivot) {
            this.pivot_options.domain = domain;
            this.pivot_options.row_groupby = row_groupby;
            this.pivot_options.col_groupby = col_groupby;
            return;
        }
        var row_gbs = this.create_field_values(row_groupby),
            col_gbs = this.create_field_values(col_groupby),
            dom_changed = !_.isEqual(this.pivot.domain, domain),
            row_gb_changed = !_.isEqual(row_gbs, this.pivot.rows.groupby),
            col_gb_changed = !_.isEqual(col_gbs, this.pivot.cols.groupby),
            row_reduced = is_strict_beginning_of(row_gbs, this.pivot.rows.groupby),
            col_reduced = is_strict_beginning_of(col_gbs, this.pivot.cols.groupby);

        if (!dom_changed && row_reduced && !col_gb_changed) {
            this.pivot.fold_with_depth(this.pivot.rows, row_gbs.length);
            this.display_data();
            return;
        }
        if (!dom_changed && col_reduced && !row_gb_changed) {
            this.pivot.fold_with_depth(this.pivot.cols, col_gbs.length);
            this.display_data();
            return;
        }

        if (dom_changed || row_gb_changed || col_gb_changed) {
            this.pivot.set(domain, row_gbs, col_gbs).then(this.proxy('display_data'));
        }
    },

    set_mode: function (mode) {
        this.mode = mode;

        if (mode === 'pivot') {
            this.$('.graph_heatmap label').removeClass('disabled');
        } else {
            this.$('.graph_heatmap label').addClass('disabled');
        }
        this.display_data();
    },

    set_heatmap_mode: function (mode) { // none, row, col, all
        this.heatmap_mode = mode;
        if (mode === 'none') {
            this.$('.graph_heatmap label').removeClass('disabled');
            this.$('.graph_heatmap label').removeClass('active');
        }
        this.display_data();
    },

    create_field_value: function (f) {
        var field = (_.contains(f, ':')) ? f.split(':')[0] : f,
            groupby_field = _.findWhere(this.important_fields, {field:field}),
            string = groupby_field ? groupby_field.string : this.fields[field].string,
            result =  {field: f, string: string, type: this.fields[field].type };

        if (groupby_field) {
            result.filter = groupby_field.filter;
        }

        return result;
    },

    create_field_values: function (field_ids) {
        return _.map(field_ids, this.proxy('create_field_value'));
    },


    get_col_groupbys: function () {
        return _.pluck(this.pivot.cols.groupby, 'field');
    },

    // ----------------------------------------------------------------------
    // UI code
    // ----------------------------------------------------------------------
    events: {
        'click .graph_mode_selection label' : 'mode_selection',
        'click .graph_measure_selection li' : 'measure_selection',
        'click .graph_options_selection label' : 'option_selection',
        'click .graph_heatmap label' : 'heatmap_mode_selection',
        'click .web_graph_click' : 'header_cell_clicked',
        'click a.field-selection' : 'field_selection',
    },

    mode_selection: function (event) {
        event.preventDefault();
        var mode = event.currentTarget.attributes['data-mode'].nodeValue;
        this.set_mode(mode);
    },

    measure_selection: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var measure_field = event.target.attributes['data-choice'].nodeValue;
        var measure = {
            field: measure_field,
            type: this.fields[measure_field].type,
            string: this.fields[measure_field].string
        };

        this.pivot.toggle_measure(measure).then(this.proxy('display_data'));
        this.put_measure_checkmarks();
    },

    put_measure_checkmarks: function () {
        var self = this,
            measures_li = this.$('.graph_measure_selection a');
        measures_li.removeClass('oe_selected');
        _.each(this.measure_list, function (measure, index) {
            if (_.findWhere(self.pivot.measures, measure)) {
                measures_li.eq(index).addClass('oe_selected');
            }
        });

    },

    option_selection: function (event) {
        event.preventDefault();
        switch (event.currentTarget.attributes['data-choice'].nodeValue) {
            case 'bar_grouped':
                this.bar_ui = 'group';
                if (this.mode === 'bar') {
                    this.display_data();
                }
                break;
            case 'bar_stacked':
                this.bar_ui = 'stack';
                if (this.mode === 'bar') {
                    this.display_data();
                }
                break;
            case 'swap_axis':
                this.swap_axis();
                break;
            case 'expand_all':
                this.pivot.expand_all().then(this.proxy('display_data'));
                break;
            case 'update_values':
                this.pivot.update_data().then(this.proxy('display_data'));
                break;
        }
    },

    heatmap_mode_selection: function (event) {
        event.preventDefault();
        var mode = event.currentTarget.attributes['data-mode'].nodeValue;
        if (this.heatmap_mode === mode) {
            event.stopPropagation();
            this.set_heatmap_mode('none');
        } else {
            this.set_heatmap_mode(mode);
        }
    },

    header_cell_clicked: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var id = event.target.attributes['data-id'].nodeValue,
            header = this.pivot.get_header(id),
            self = this;

        if (header.expanded) {
            this.fold(header);
        } else {
            if (header.path.length < header.root.groupby.length) {
                this.expand(id);
            } else {
                if (!this.important_fields.length) {
                    return;
                }
                var fields = _.map(this.important_fields, function (field) {
                        return {id: field.field, value: field.string, type:self.fields[field.field].type};
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
            field_id = event.target.attributes['data-field-id'].nodeValue,
            interval,
            groupby = this.create_field_value(field_id);
        event.preventDefault();
        if (this.fields[field_id].type === 'date' || this.fields[field_id].type === 'datetime') {
            interval = event.target.attributes['data-interval'].nodeValue;
            groupby.field =  groupby.field + ':' + interval;
        }
        this.expand(id, groupby);
    },

    // ----------------------------------------------------------------------
    // Pivot Table integration
    // ----------------------------------------------------------------------
    expand: function (header_id, groupby) {
        var self = this,
            header = this.pivot.get_header(header_id),
            update_groupby = !!groupby,
            groupby = groupby || header.root.groupby[header.path.length];

        this.pivot.expand(header_id, groupby).then(function () {
            if (update_groupby && self.graph_view) {
                self.graph_view.register_groupby(self.pivot.rows.groupby, self.pivot.cols.groupby);
            }
            self.display_data();
        });

    },

    fold: function (header) {
        var update_groupby = this.pivot.fold(header);

        this.display_data();
        if (update_groupby && this.graph_view) {
            this.graph_view.register_groupby(this.pivot.rows.groupby, this.pivot.cols.groupby);
        }
    },

    swap_axis: function () {
        this.pivot.swap_axis();
        this.display_data();
        this.graph_view.register_groupby(this.pivot.rows.groupby, this.pivot.cols.groupby);
    },

    // ----------------------------------------------------------------------
    // Main display method
    // ----------------------------------------------------------------------
    display_data: function () {
        this.$('.graph_main_content svg').remove();
        this.$('.graph_main_content div').remove();
        this.table.empty();
        this.width = this.$el.width();
        this.height = Math.min(Math.max(document.documentElement.clientHeight - 116 - 60, 250), Math.round(0.8*this.$el.width()));

        if (this.visible_ui) {
            this.$('.graph_header').css('display', 'block');
        } else {
            this.$('.graph_header').css('display', 'none');
        }
        if (this.pivot.no_data) {
            this.$('.graph_main_content').append($(QWeb.render('graph_no_data')));
        } else {
            if (this.mode === 'pivot') {
                this.draw_table();
            } else {
                this.$('.graph_main_content').append($('<div><svg></svg></div>'));
                this.svg = this.$('.graph_main_content svg')[0];
                this[this.mode]();
            }
        }
    },

    // ----------------------------------------------------------------------
    // Drawing the table
    // ----------------------------------------------------------------------
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
        var measures = this.pivot.measures,
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
            cell.append(openerp.web.format_value(value, {type: measure_type}));
            if (self.heatmap_mode === 'both') {
                total = pivot.get_total()[index];
                color = Math.floor(90 + 165*(total - Math.abs(value))/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            if (self.heatmap_mode === 'row') {
                total = pivot.get_total(row)[index];
                color = Math.floor(90 + 165*(total - Math.abs(value))/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            if (self.heatmap_mode === 'col') {
                total = pivot.get_total(col)[index];
                color = Math.floor(90 + 165*(total - Math.abs(value))/total);
                cell.css('background-color', $.Color(255, color, color));
            }
            return cell;
        }
    },

    // ----------------------------------------------------------------------
    // Drawing charts code
    // ----------------------------------------------------------------------
    bar: function () {
        var self = this,
            dim_x = this.pivot.rows.groupby.length,
            dim_y = this.pivot.cols.groupby.length,
            show_controls = (this.width > 400 && this.height > 300 && dim_x + dim_y >=2),
            data;

        // No groupby 
        if ((dim_x === 0) && (dim_y === 0)) {
            data = [{key: 'Total', values:[{
                x: 'Total',
                y: this.pivot.get_total(),
            }]}];
        // Only column groupbys 
        } else if ((dim_x === 0) && (dim_y >= 1)){
            data =  _.map(this.pivot.get_cols_with_depth(1), function (header) {
                return {
                    key: header.title,
                    values: [{x:header.title, y: self.pivot.get_total(header)[0]}]
                };
            });
        // Just 1 row groupby 
        } else if ((dim_x === 1) && (dim_y === 0))  {
            data = _.map(this.pivot.main_row().children, function (pt) {
                var value = self.pivot.get_total(pt),
                    title = (pt.title !== undefined) ? pt.title : 'Undefined';
                return {x: title, y: value};
            });
            data = [{key: self.pivot.measures[0].string, values:data}];
        // 1 row groupby and some col groupbys
        } else if ((dim_x === 1) && (dim_y >= 1))  {
            data = _.map(this.pivot.get_cols_with_depth(1), function (colhdr) {
                var values = _.map(self.pivot.get_rows_with_depth(1), function (header) {
                    return {
                        x: header.title || 'Undefined',
                        y: self.pivot.get_values(header.id, colhdr.id)[0] || 0
                    };
                });
                return {key: colhdr.title || 'Undefined', values: values};
            });
        // At least two row groupby
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
                .showControls(show_controls);

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

    line: function () {
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

    pie: function () {
        var self = this,
            dim_x = this.pivot.rows.groupby.length;
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

// Utility function: returns true if the beginning of array2 is array1 and
// if array1 is not array2
function is_strict_beginning_of (array1, array2) {
    if (array1.length >= array2.length) { return false; }
    var result = true;
    for (var i = 0; i < array1.length; i++) {
        if (!_.isEqual(array1[i], array2[i])) { return false;} 
    }
    return result;
}

})();
