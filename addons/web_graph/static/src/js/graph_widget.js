
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
            this.$('.graph_main_content').addClass('graph_chart_mode');
        } else {
            this.$('.graph_main_content').addClass('graph_pivot_mode');
        }

        // get search view
        var parent = this.getParent();
        while (!(parent instanceof openerp.web.ViewManager)) {
            parent = parent.getParent();
        }
        this.search_view = parent.searchview;

        openerp.session.rpc('/web_graph/check_xlwt').then(function (result) {
            self.$('.graph_options_selection label').last().toggle(result);
        });

        return this.model.call('fields_get', {
                    context: this.graph_view.dataset.context
                }).then(function (f) {
            self.fields = f;
            self.fields.__count = {field:'__count', type: 'integer', string:_t('Count')};
            self.groupby_fields = self.get_groupby_fields();
            self.measure_list = self.get_measures();
            self.add_measures_to_options();
            self.pivot_options.row_groupby = self.create_field_values(self.pivot_options.row_groupby || []);
            self.pivot_options.col_groupby = self.create_field_values(self.pivot_options.col_groupby || []);
            self.pivot_options.measures = self.create_field_values(self.pivot_options.measures || [{field:'__count', type: 'integer', string:'Count'}]);
            self.pivot = new openerp.web_graph.PivotTable(self.model, self.domain, self.fields, self.pivot_options);
            self.pivot.update_data().then(function () {
                self.display_data();
                if (self.graph_view) {
                    self.graph_view.register_groupby(self.pivot.rows.groupby, self.pivot.cols.groupby);
                }
            });
            openerp.web.bus.on('click', self, function (event) {
                if (self.dropdown) {
                    self.$row_clicked = $(event.target).closest('tr');
                    self.dropdown.remove();
                    self.dropdown = null;
                }
            });
            self.put_measure_checkmarks();
        });
    },

    get_groupby_fields: function () {
        var search_fields = this.get_search_fields(),
            search_field_names = _.pluck(search_fields, 'field'),
            other_fields = [],
            groupable_types = ['many2one', 'char', 'boolean', 'selection', 'date', 'datetime'];

        _.each(this.fields, function (val, key) {
            if (!_.contains(search_field_names, key) && 
                _.contains(groupable_types, val.type) && 
                val.store === true) {
                other_fields.push({
                    field: key,
                    string: val.string,
                });
            }
        });
        return search_fields.concat(other_fields);
    },

    // this method gets the fields that appear in the search view, under the 
    // 'Groupby' heading
    get_search_fields: function () {
        var self = this;

        var groupbygroups = _(this.search_view.drawer.inputs).select(function (g) {
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
            if (((f.type === 'integer') || (f.type === 'float')) && 
                (id !== 'id') &&
                (f.store !== false)) {
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
    set: function (domain, row_groupby, col_groupby, measures_groupby) {
        if (!this.pivot) {
            this.pivot_options.domain = domain;
            this.pivot_options.row_groupby = row_groupby;
            this.pivot_options.col_groupby = col_groupby;
            this.pivot_options.measures_groupby = measures_groupby;
            return;
        }
        var row_gbs = this.create_field_values(row_groupby),
            col_gbs = this.create_field_values(col_groupby),
            measures_gbs = this.create_field_values(measures_groupby),
            dom_changed = !_.isEqual(this.pivot.domain, domain),
            row_gb_changed = !_.isEqual(row_gbs, this.pivot.rows.groupby),
            col_gb_changed = !_.isEqual(col_gbs, this.pivot.cols.groupby),
            measures_gb_changed = !_.isEqual(measures_gbs, this.pivot.measures),
            row_reduced = is_strict_beginning_of(row_gbs, this.pivot.rows.groupby),
            col_reduced = is_strict_beginning_of(col_gbs, this.pivot.cols.groupby),
            measures_reduced = is_strict_beginning_of(measures_gbs, this.pivot.measures);

        if (!dom_changed && row_reduced && !col_gb_changed && !measures_gb_changed) {
            this.pivot.fold_with_depth(this.pivot.rows, row_gbs.length);
            this.display_data();
            return;
        }
        if (!dom_changed && col_reduced && !row_gb_changed && !measures_gb_changed) {
            this.pivot.fold_with_depth(this.pivot.cols, col_gbs.length);
            this.display_data();
            return;
        }

        if (!dom_changed && col_reduced && row_reduced && !measures_gb_changed) {
            this.pivot.fold_with_depth(this.pivot.rows, row_gbs.length);
            this.pivot.fold_with_depth(this.pivot.cols, col_gbs.length);
            this.display_data();
            return;
        }

        if (dom_changed || row_gb_changed || col_gb_changed || measures_gb_changed) {
            this.pivot.set(domain, row_gbs, col_gbs, measures_gbs).then(this.proxy('display_data'));
        }

        if (measures_gb_changed) {
            this.put_measure_checkmarks();
        }
    },

    set_mode: function (mode) {
        this.mode = mode;

        if (mode === 'pivot') {
            this.$('.graph_heatmap label').removeClass('disabled');
            this.$('.graph_main_content').removeClass('graph_chart_mode').addClass('graph_pivot_mode');
        } else {
            this.$('.graph_heatmap label').addClass('disabled');
            this.$('.graph_main_content').removeClass('graph_pivot_mode').addClass('graph_chart_mode');
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
            groupby_field = _.findWhere(this.groupby_fields, {field:field}),
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

    get_current_measures: function () {
        return _.pluck(this.pivot.measures, 'field');
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
            case 'swap_axis':
                this.swap_axis();
                break;
            case 'expand_all':
                this.pivot.expand_all().then(this.proxy('display_data'));
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
            if (header.root === this.pivot.rows) {
                this.fold_row(header, event);
            } else {
                this.fold_col(header);
            }
            return;
        }
        if (header.path.length < header.root.groupby.length) {
            this.$row_clicked = $(event.target).closest('tr');
            this.expand(id);
            return;
        }
        if (!this.groupby_fields.length) {
            return;
        }

        var fields = _.map(this.groupby_fields, function (field) {
                return {id: field.field, value: field.string, type:self.fields[field.field.split(':')[0]].type};
        });
        if (this.dropdown) {
            this.dropdown.remove();
        }
        this.dropdown = $(QWeb.render('field_selection', {fields:fields, header_id:id}));
        $(event.target).after(this.dropdown);
        this.dropdown.css({
            position:'absolute',
            left:event.originalEvent.layerX,
        });
        this.$('.field-selection').next('.dropdown-menu').first().toggle();        
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
            if (header.root === self.pivot.rows) {
                // expanding rows can be done by only inserting in the dom
                // console.log(event.target);
                var rows = self.build_rows(header.children);
                var doc_fragment = $(document.createDocumentFragment());
                rows.map(function (row) {
                    doc_fragment.append(self.draw_row(row, 0));
                });
                self.$row_clicked.after(doc_fragment);
            } else {
                // expanding cols will redraw the full table
                self.display_data();                
            }
            if (update_groupby && self.graph_view) {
                self.graph_view.register_groupby(self.pivot.rows.groupby, self.pivot.cols.groupby);
            }
        });

    },

    fold_row: function (header, event) {
        var rows_before = this.pivot.rows.headers.length,
            update_groupby = this.pivot.fold(header),
            rows_after = this.pivot.rows.headers.length,
            rows_removed = rows_before - rows_after;

        if (rows_after === 1) {
            // probably faster to redraw the unique row instead of removing everything
            this.display_data();
        } else {
            var $row = $(event.target).parent().parent();
            $row.nextAll().slice(0,rows_removed).remove();
        }
        if (update_groupby && this.graph_view) {
            this.graph_view.register_groupby(this.pivot.rows.groupby, this.pivot.cols.groupby);
        }
    },

    fold_col: function (header) {
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
    build_table: function(raw) {
        return {
            headers: this.build_headers(),
            measure_row: this.build_measure_row(),
            rows: this.build_rows(this.pivot.rows.headers,raw),
            nbr_measures: this.pivot.measures.length,
            title: this.title,
        };
    },

    build_headers: function () {
        var pivot = this.pivot,
            nbr_measures = pivot.measures.length,
            height = _.max(_.map(pivot.cols.headers, function(g) {return g.path.length;})) + 1,
            rows = [];

        _.each(pivot.cols.headers, function (col) {
            var cell_width = nbr_measures * (col.expanded ? pivot.get_ancestor_leaves(col).length : 1),
                cell_height = col.expanded ? 1 : height - col.path.length,
                cell = {width: cell_width, height: cell_height, title: col.title, id: col.id, expanded: col.expanded};
            if (rows[col.path.length]) {
                rows[col.path.length].push(cell);
            } else {
                rows[col.path.length] = [cell];
            }
        });

        if (pivot.get_cols_leaves().length > 1) {
            rows[0].push({width: nbr_measures, height: height, title: ' ', id: pivot.main_col().id });
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

    make_cell: function (row, col, value, index, raw) {
        var formatted_value = raw && !_.isUndefined(value) ? value : openerp.web.format_value(value, {type:this.pivot.measures[index].type}),
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

    build_rows: function (headers, raw) {
        var self = this,
            pivot = this.pivot,
            m, i, j, k, cell, row;

        var rows = [];
        var cells, pivot_cells, values;

        var nbr_of_rows = headers.length;
        var col_headers = pivot.get_cols_leaves();

        for (i = 0; i < nbr_of_rows; i++) {
            row = headers[i];
            cells = [];
            pivot_cells = [];
            for (j = 0; j < pivot.cells.length; j++) {
                if (pivot.cells[j].x == row.id || pivot.cells[j].y == row.id) {
                    pivot_cells.push(pivot.cells[j]);
                }              
            }

            for (j = 0; j < col_headers.length; j++) {
                values = undefined;
                for (k = 0; k < pivot_cells.length; k++) {
                    if (pivot_cells[k].x == col_headers[j].id || pivot_cells[k].y == col_headers[j].id) {
                        values = pivot_cells[k].values;
                        break;
                    }               
                }
                if (!values) { values = new Array(pivot.measures.length);}
                for (m = 0; m < pivot.measures.length; m++) {
                    cells.push(self.make_cell(row,col_headers[j],values[m], m, raw));
                }
            }
            if (col_headers.length > 1) {
                var totals = pivot.get_total(row);
                for (m = 0; m < pivot.measures.length; m++) {
                    cell = self.make_cell(row, pivot.cols.headers[0], totals[m], m, raw);
                    cell.is_bold = 'true';
                    cells.push(cell);
                }
            }
            rows.push({
                id: row.id,
                indent: row.path.length,
                title: row.title,
                expanded: row.expanded,
                cells: cells,
            });
        }

        return rows;
    },

    // ----------------------------------------------------------------------
    // Main display method
    // ----------------------------------------------------------------------
    display_data: function () {
        var scroll = $(window).scrollTop();
        this.$('.graph_main_content svg').remove();
        this.$('.graph_main_content div').remove();
        this.table.empty();
        this.table.toggleClass('heatmap', this.heatmap_mode !== 'none');
        this.$('.graph_options_selection label').last().toggleClass('disabled', this.pivot.no_data);
        this.width = this.$el.width();
        this.height = Math.min(Math.max(document.documentElement.clientHeight - 116 - 60, 250), Math.round(0.8*this.$el.width()));

        this.$('.graph_header').toggle(this.visible_ui);
        if (this.pivot.no_data) {
            this.$('.graph_main_content').append($(QWeb.render('graph_no_data')));
        } else {
            if (this.mode === 'pivot') {
                this.draw_table();
                $(window).scrollTop(scroll);
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
        var custom_gbs = this.graph_view.get_custom_filter_groupbys(),
            frozen_rows = custom_gbs.groupby.length,
            frozen_cols = custom_gbs.col_groupby.length;

        var table = this.build_table();
        var doc_fragment = $(document.createDocumentFragment());
        this.draw_headers(table.headers, doc_fragment, frozen_cols);
        this.draw_measure_row(table.measure_row, doc_fragment);
        this.draw_rows(table.rows, doc_fragment, frozen_rows);
        this.table.append(doc_fragment);
    },

    make_header_cell: function (header, frozen) {
        var cell = (_.has(header, 'cells') ? $('<td>') : $('<th>'))
                        .addClass('graph_border')
                        .attr('rowspan', header.height)
                        .attr('colspan', header.width);
        var $content = $('<span>').attr('href','#')
                                 .text(' ' + (header.title || _t('Undefined')))
                                 .css('margin-left', header.indent*30 + 'px')
                                 .attr('data-id', header.id);
        if (_.has(header, 'expanded')) {
            if (('indent' in header) && header.indent >= frozen) {
                $content.addClass(header.expanded ? 'fa fa-minus-square' : 'fa fa-plus-square');
                $content.addClass('web_graph_click');
            }
            if (!('indent' in header) && header.lvl >= frozen) {
                $content.addClass(header.expanded ? 'fa fa-minus-square' : 'fa fa-plus-square');
                $content.addClass('web_graph_click');
            }
        } else {
            $content.css('font-weight', 'bold');
        }
        return cell.append($content);
    },

    draw_headers: function (headers, doc_fragment, frozen_cols) {
        var make_cell = this.make_header_cell,
            $empty_cell = $('<th>').attr('rowspan', headers.length),
            $thead = $('<thead>');

        _.each(headers, function (row, lvl) {
            var $row = $('<tr>');
            _.each(row, function (header) {
                header.lvl = lvl;
                $row.append(make_cell(header, frozen_cols));
            });
            $thead.append($row);
        });
        $thead.children(':first').prepend($empty_cell);
        doc_fragment.append($thead);
        this.$thead = $thead;
    },
    
    draw_measure_row: function (measure_row) {
        var $row = $('<tr>').append('<th>');
        _.each(measure_row, function (cell) {
            var $cell = $('<th>').addClass('measure_row').text(cell.text);
            if (cell.is_bold) {$cell.css('font-weight', 'bold');}
            $row.append($cell);
        });
        this.$thead.append($row);
    },
    
    draw_row: function (row, frozen_rows) {
        var $row = $('<tr>')
            .attr('data-indent', row.indent)
            .append(this.make_header_cell(row, frozen_rows));
        
        var cells_length = row.cells.length;
        var cells_list = [];
        var cell, hcell;

        for (var j = 0; j < cells_length; j++) {
            cell = row.cells[j];
            hcell = '<td';
            if (cell.is_bold || cell.color) {
                hcell += ' style="';
                if (cell.is_bold) hcell += 'font-weight: bold;';
                if (cell.color) hcell += 'background-color:' + $.Color(255, cell.color, cell.color) + ';';
                hcell += '"';
            }
            hcell += '>' + cell.value + '</td>';
            cells_list[j] = hcell;
        }
        return $row.append(cells_list.join(''));
    },

    draw_rows: function (rows, doc_fragment, frozen_rows) {
        var rows_length = rows.length,
            $tbody = $('<tbody>');

        doc_fragment.append($tbody);
        for (var i = 0; i < rows_length; i++) {
            $tbody.append(this.draw_row(rows[i], frozen_rows));
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
            data = [{key: _t('Total'), values:[{
                x: _t('Total'),
                y: this.pivot.get_total()[0],
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
                var value = self.pivot.get_total(pt)[0],
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

        var rows = this.pivot.get_rows_with_depth(dim_x),
            labels = _.pluck(rows, 'title');

        var data = _.map(this.pivot.get_cols_leaves(), function (col) {
            var values = _.map(rows, function (row, index) {
                return {x: index, y: self.pivot.get_values(row.id,col.id)[0] || 0};
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
                .x(function (d,u) { return u; });

            chart.xAxis.tickFormat(function (d,u) {return labels[d];});

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
            return {x: title, y: self.pivot.get_total(row)[0]};
        });

        nv.addGraph(function () {
            var chart = nv.models.pieChart()
                .width(self.width)
                .height(self.height)
                .color(d3.scale.category10().range());

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
            data: {data: JSON.stringify(this.build_table(true))},
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
