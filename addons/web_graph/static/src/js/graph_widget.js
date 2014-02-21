
/* jshint undef: false  */

(function () {
'use strict';
var QWeb = openerp.web.qweb;
var _lt = openerp.web._lt;
var _t = openerp.web._t;

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
        this.visible_ui = options.visible_ui || true;
        this.bar_ui = options.bar_ui || 'group';
        this.graph_view = options.graph_view || null;
        this.pivot_options = options;
        this.title = options.title || 'Data';
    },

    start: function() {
        var self = this;
        this.table = $('<table>');
        this.$('.graph_main_content').append(this.table);

        var indexes = {'pivot': 0, 'bar': 1, 'line': 2, 'chart': 3};
        this.$('.graph_mode_selection label').eq(indexes[this.mode]).addClass('active');

        if (this.mode !== 'pivot') {
            this.$('.graph_heatmap label').addClass('disabled');
        }

        openerp.session.rpc('/web_graph/check_xlwt').then(function (result) {
            self.$('.graph_options_selection label').toggle(result);
        });

        return this.model.call('fields_get', []).then(function (f) {
            self.fields = f;
            self.fields.__count = {field:'__count', type: 'integer', string:_t('Quantity')};
            self.important_fields = self.get_search_fields();
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
        var self = this,
            parent = this.getParent();

        while (!(parent instanceof openerp.web.ViewManager)) {
            parent = parent.getParent();
        }

        var search_view = parent.searchview;

        var groupbygroups = _(search_view.inputs).select(function (g) {
            return g instanceof openerp.web.search.GroupbyGroup;
        });

        var filters = _.flatten(_.pluck(groupbygroups, 'filters'), true),
            groupbys = _.flatten(_.map(filters, function (filter) {
                var groupby = py.eval(filter.attrs.context).group_by;
                if (!(groupby instanceof Array)) { groupby = [groupby]; }
                return _.map(groupby, function(g) {
                    return {field: g, filter: filter};
                });
            }));

        return _.uniq(_.map(groupbys, function (groupby) {
            var field = groupby.field,
                filter = groupby.filter,
                raw_field = field.split(':')[0],
                string = (field === raw_field) ? filter.attrs.string : self.fields[raw_field].string;
            
            filter = (field === raw_field) ? filter : undefined;

            return { field: raw_field, string: string, filter: filter };
        }), false, function (filter) {return filter.field;});
    },

    // Extracts the integer/float fields which are not 'id'
    get_measures: function() {
        return _.compact(_.map(this.fields, function (f, id) {
            if (((f.type === 'integer') || (f.type === 'float')) && (id !== 'id')) {
                return {field:id, type: f.type, string: f.string};
            }
        }));
    },

    add_measures_to_options: function() {
        this.$('.graph_measure_selection').append(
        _.map(this.measure_list, function (measure) {
            return $('<li>').append($('<a>').attr('data-choice', measure.field)
                                     .attr('href', '#')
                                     .text(measure.string));
        }));
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
        var mode = event.currentTarget.getAttribute('data-mode');
        this.set_mode(mode);
    },

    measure_selection: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var measure_field = event.target.getAttribute('data-choice');
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
        switch (event.currentTarget.getAttribute('data-choice')) {
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
            case 'update_values':
                this.pivot.update_data().then(this.proxy('display_data'));
                break;
            case 'export_data':
                this.export_xls();
                break;
        }
    },

    heatmap_mode_selection: function (event) {
        event.preventDefault();
        var mode = event.currentTarget.getAttribute('data-mode');
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
        var id = event.target.getAttribute('data-id'),
            header = this.pivot.get_header(id),
            self = this;

        if (header.expanded) {
            this.fold(header);
            return;
        } 
        if (header.path.length < header.root.groupby.length) {
            this.expand(id);
            return;
        } 
        if (!this.important_fields.length) {
            return;
        }

        var fields = _.map(this.important_fields, function (field) {
                return {id: field.field, value: field.string, type:self.fields[field.field.split(':')[0]].type};
        });
        if (this.dropdown) {
            this.dropdown.remove();
        }
        this.dropdown = $(QWeb.render('field_selection', {fields:fields, header_id:id}));
        $(event.target).after(this.dropdown);
        this.dropdown.css({position:'absolute',
                           left:event.pageX,
                           top:event.pageY});
        this.$('.field-selection').next('.dropdown-menu').toggle();
        
        
    },

    field_selection: function (event) {
        var id = event.target.getAttribute('data-id'),
            field_id = event.target.getAttribute('data-field-id'),
            interval,
            groupby = this.create_field_value(field_id);
        event.preventDefault();
        if (this.fields[field_id].type === 'date' || this.fields[field_id].type === 'datetime') {
            interval = event.target.getAttribute('data-interval');
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
            update_groupby = !!groupby;
        
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
    // Convert Pivot data structure into table structure :
    //      compute rows, cols, colors, cell width, cell height, ...
    // ----------------------------------------------------------------------
    build_table: function() {
        return {
            headers: this.build_headers(),
            measure_row: this.build_measure_row(),
            rows: this.build_rows(),
            nbr_measures: this.pivot.measures.length,
            title: this.title,
        };
    },

    build_headers: function () {
        var pivot = this.pivot,
            nbr_measures = pivot.measures.length,
            height = _.max(_.map(pivot.cols.headers, function(g) {return g.path.length;})),
            rows = [];

        _.each(pivot.cols.headers, function (col) {
            if (col.path.length === 0) { return;}
            var cell_width = nbr_measures * (col.expanded ? pivot.get_ancestor_leaves(col).length : 1),
                cell_height = col.expanded ? 1 : height - col.path.length + 1,
                cell = {width: cell_width, height: cell_height, title: col.title, id: col.id, expanded: col.expanded};
            if (rows[col.path.length - 1]) {
                rows[col.path.length - 1].push(cell);
            } else {
                rows[col.path.length - 1] = [cell];
            }
        });

        if (pivot.get_cols_leaves().length > 1) {
            rows[0].push({width: nbr_measures, height: height, title: _t('Total'), id: pivot.main_col().id });
        }
        if (pivot.cols.headers.length === 1) {
            rows = [[{width: nbr_measures, height: 1, title: _t('Total'), id: pivot.main_col().id, expanded: false}]];
        }
        return rows;
    },

    build_measure_row: function () {
        var nbr_leaves = this.pivot.get_cols_leaves().length,
            nbr_cols = nbr_leaves + ((nbr_leaves > 1) ? 1 : 0),
            result = [],
            add_total = this.pivot.get_cols_leaves().length > 1,
            i, m;
        for (i = 0; i < nbr_cols; i++) {
            for (m = 0; m < this.pivot.measures.length; m++) {
                result.push({
                    text:this.pivot.measures[m].string,
                    is_bold: add_total && (i === nbr_cols - 1)
                });
            }
        }
        return result;
    },

    make_cell: function (row, col, value, index) {
        var formatted_value = openerp.web.format_value(value, {type:this.pivot.measures[index].type}),
            cell = {value:formatted_value};

        if (this.heatmap_mode === 'none') { return cell; }
        var total = (this.heatmap_mode === 'both') ? this.pivot.get_total()[index]
                  : (this.heatmap_mode === 'row')  ? this.pivot.get_total(row)[index]
                  : this.pivot.get_total(col)[index];
        var color = Math.floor(90 + 165*(total - Math.abs(value))/total);
        if (color < 255) {
            cell.color = color;
        }
        return cell;
    },

    build_rows: function () {
        var self = this,
            pivot = this.pivot,
            m, cell;

        return _.map(pivot.rows.headers, function (row) {
            var cells = [];
            _.each(pivot.get_cols_leaves(), function (col) {
                var values = pivot.get_values(row.id,col.id);
                for (m = 0; m < pivot.measures.length; m++) {
                    cells.push(self.make_cell(row,col,values[m], m));
                }
            });
            if (pivot.get_cols_leaves().length > 1) {
                var totals = pivot.get_total(row);
                for (m = 0; m < pivot.measures.length; m++) {
                    cell = self.make_cell(row, pivot.main_col(), totals[m], m);
                    cell.is_bold = 'true';
                    cells.push(cell);
                }
            }
            return {
                id: row.id,
                indent: row.path.length,
                title: row.title,
                expanded: row.expanded,
                cells: cells,
            };
        });
    },

    // ----------------------------------------------------------------------
    // Main display method
    // ----------------------------------------------------------------------
    display_data: function () {
        this.$('.graph_main_content svg').remove();
        this.$('.graph_main_content div').remove();
        this.table.empty();
        this.table.toggleClass('heatmap', this.heatmap_mode !== 'none');
        this.width = this.$el.width();
        this.height = Math.min(Math.max(document.documentElement.clientHeight - 116 - 60, 250), Math.round(0.8*this.$el.width()));

        this.$('.graph_header').toggle(this.visible_ui);
        if (this.pivot.no_data) {
            this.$('.graph_main_content').append($(QWeb.render('graph_no_data')));
        } else {
            if (this.mode === 'pivot') {
                this.draw_table();
            } else {
                this.$('.graph_main_content').append($('<div><svg>'));
                this.svg = this.$('.graph_main_content svg')[0];
                this[this.mode]();
            }
        }
    },

    // ----------------------------------------------------------------------
    // Drawing the table
    // ----------------------------------------------------------------------
    draw_table: function () {
        var table = this.build_table();
        this.draw_headers(table.headers);
        this.draw_measure_row(table.measure_row);
        this.draw_rows(table.rows);
    },

    make_header_cell: function (header) {
        var cell = (_.has(header, 'cells') ? $('<td>') : $('<th>'))
                        .addClass('graph_border')
                        .attr('rowspan', header.height)
                        .attr('colspan', header.width);
        var content = $('<span>').addClass('web_graph_click')
                                 .attr('href','#')
                                 .text(' ' + (header.title || _t('Undefined')))
                                 .attr('data-id', header.id);
        if (_.has(header, 'expanded')) {
            content.addClass(header.expanded ? 'fa fa-minus-square' : 'fa fa-plus-square');
        } else {
            content.css('font-weight', 'bold');
        }
        if (_.has(header, 'indent')) {
            for (var i = 0; i < header.indent; i++) { cell.prepend($('<span>', {class:'web_graph_indent'})); }
        }
        return cell.append(content);
    },

    draw_headers: function (headers) {
        var make_cell = this.make_header_cell,
            empty_cell = $('<th>').attr('rowspan', headers.length),
            thead = $('<thead>');

        _.each(headers, function (row) {
            var html_row = $('<tr>');
            _.each(row, function (header) {
                html_row.append(make_cell(header));
            });
            thead.append(html_row);
        });
        thead.children(':first').prepend(empty_cell);
        this.table.append(thead);
    },
    
    draw_measure_row: function (measure_row) {
        if (this.pivot.measures.length === 1) { return; }
        var html_row = $('<tr>').append('<th>');
        _.each(measure_row, function (cell) {
            var measure_cell = $('<th>').addClass('measure_row').text(cell.text);
            if (cell.is_bold) {measure_cell.css('font-weight', 'bold');}
            html_row.append(measure_cell);
        });
        this.$('thead').append(html_row);
    },
    
    draw_rows: function (rows) {
        var table = this.table,
            make_cell = this.make_header_cell;

        _.each(rows, function (row) {
            var html_row = $('<tr>').append(make_cell(row));
            _.each(row.cells, function (cell) {
                var html_cell = $('<td>').text(cell.value);
                if (_.has(cell, 'color')) {
                    html_cell.css('background-color', $.Color(255, cell.color, cell.color));
                }
                if (cell.is_bold) { html_cell.css('font-weight', 'bold'); }
                html_row.append(html_cell);
            });
            table.append(html_row);
        });
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
            data = [{key: _t('Total'), values:[{
                x: _t('Total'),
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
                    title = (pt.title !== undefined) ? pt.title : _t('Undefined');
                return {x: title, y: value};
            });
            data = [{key: self.pivot.measures[0].string, values:data}];
        // 1 row groupby and some col groupbys
        } else if ((dim_x === 1) && (dim_y >= 1))  {
            data = _.map(this.pivot.get_cols_with_depth(1), function (colhdr) {
                var values = _.map(self.pivot.get_rows_with_depth(1), function (header) {
                    return {
                        x: header.title || _t('Undefined'),
                        y: self.pivot.get_values(header.id, colhdr.id)[0] || 0
                    };
                });
                return {key: colhdr.title || _t('Undefined'), values: values};
            });
        // At least two row groupby
        } else {
            var keys = _.uniq(_.map(this.pivot.get_rows_with_depth(2), function (hdr) {
                return hdr.title || _t('Undefined');
            }));
            data = _.map(keys, function (key) {
                var values = _.map(self.pivot.get_rows_with_depth(1), function (hdr) {
                    var subhdr = _.find(hdr.children, function (child) {
                        return ((child.title === key) || ((child.title === undefined) && (key === _t('Undefined'))));
                    });
                    return {
                        x: hdr.title || _t('Undefined'),
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
                return {x: row.title, y: self.pivot.get_values(row.id,col.id)[0] || 0};
            });
            var title = _.map(col.path, function (p) {
                return p || _t('Undefined');
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
                return p || _t('Undefined');
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

    // ----------------------------------------------------------------------
    // Controller stuff...
    // ----------------------------------------------------------------------
    export_xls: function() {
        var c = openerp.webclient.crashmanager;
        openerp.web.blockUI();
        this.session.get_file({
            url: '/web_graph/export_xls',
            data: {data: JSON.stringify(this.build_table())},
            complete: openerp.web.unblockUI,
            error: c.rpc_error.bind(c)
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
