/*---------------------------------------------------------
 * Odoo Pivot Table view
 *---------------------------------------------------------*/

(function () {
'use strict';

var instance = openerp,
    _lt = instance.web._lt,
    _t = instance.web._t,
    QWeb = instance.web.qweb,
    format_value = instance.web.format_value,
    total = _t("Total");

instance.web.views.add('pivot', 'instance.web.PivotView');

instance.web.PivotView = instance.web.View.extend({
    template: 'PivotView',
    display_name: _lt('Pivot'),
    view_type: 'pivot',
    events: {
        'click .oe-opened': 'on_open_header_click',
        'click .oe-closed': 'on_closed_header_click',
        'click .o-field-menu': 'on_field_menu_selection',
        'click td': 'on_cell_click',
        'click .measure-row': 'on_measure_row_click',
    },

    init: function(parent, dataset, view_id, options) {
        this._super(parent, dataset, view_id, options);
        this.model = new instance.web.Model(dataset.model, {group_by_no_leaf: true});

        this.$sidebar = options.$sidebar;
        this.fields = {};
        this.measures = {};
        this.groupable_fields = {};
        this.ready = false; // will be ready after the first do_search
        this.data_loaded = $.Deferred();
        this.title = options.title;

        this.main_row = {
            root: undefined,
            groupbys: [],
        };
        this.main_col = {
            root: undefined,
            groupbys: [],
        };
        this.initial_col_groupby = [];
        this.initial_row_groupby = [];

        this.active_measures = [];
        this.headers = {};
        this.cells = {};
        this.has_data = false;

        this.last_header_selected = null;
        this.sorted_column = {};
    },
    start: function () {
        var self = this;
        this.$table_container = this.$('.o-pivot-table');

        var load_fields = this.model.call('fields_get', [])
                .then(this.prepare_fields.bind(this));

        if (this.$sidebar) {
            openerp.session.rpc('/web/pivot/check_xlwt').then(function (result) {
                if (result) {
                    self.sidebar = new instance.web.Sidebar(self);
                    self.sidebar.appendTo(self.$sidebar);
                    self.sidebar.add_items('other', [{
                        label: _t("Download xls"),
                        callback: self.dowload_table.bind(self)
                    }]);
                }
            });
        }
        return $.when(this._super(), load_fields).then(this.render_buttons.bind(this));
    },
    render_buttons: function () {
        var self = this;
        var context = {measures: _.pairs(_.omit(this.measures, '__count__'))};
        this.$buttons.html(QWeb.render('PivotView.buttons', context));
        this.$buttons.click(this.on_button_click.bind(this));
        this.active_measures.forEach(function (measure) {
            self.$buttons.find('li[data-field="' + measure + '"]').addClass('selected');
        });

        var another_ctx = {fields: _.chain(this.groupable_fields).pairs().sortBy(function(f){return f[1].string;}).value()};
        this.$field_selection = this.$('.o-field-selection');
        this.$field_selection.html(QWeb.render('PivotView.FieldSelection', another_ctx));
        openerp.web.bus.on('click', self, function () {
            self.$field_selection.find('ul').first().hide();
        });
        this.$buttons.find('button').tooltip();
    },
    view_loading: function (fvg) {
        var self = this;
        this.title = this.title || fvg.arch.attrs.string;
        this.enable_linking = !fvg.arch.attrs.disable_linking;
        this.$el.toggleClass('oe-enable-linking', this.enable_linking);
        fvg.arch.children.forEach(function (field) {
            var name = field.attrs.name;
            if (field.attrs.interval) {
                name += ':' + field.attrs.interval;
            }
            //noinspection FallThroughInSwitchStatementJS
            switch (field.attrs.type) {
            case 'measure':
                self.active_measures.push(name);
                break;
            case 'col':
                self.initial_col_groupby.push(name);
                break;
            default:
                if ('operator' in field.attrs) {
                    self.active_measures.push(name);
                    break;
                }
            case 'row':
                self.initial_row_groupby.push(name);
            }
        });
        if ((!self.active_measures.length) || fvg.arch.attrs.display_quantity){
            self.active_measures.push('__count__');
        }
    },
    prepare_fields: function (fields) {
        var self = this,
            groupable_types = ['many2one', 'char', 'boolean', 
                               'selection', 'date', 'datetime'];
        this.fields = fields;
        _.each(fields, function (field, name) {
            if ((name !== 'id') && (field.store === true)) {
                if (field.type === 'integer' || field.type === 'float') {
                    self.measures[name] = field;
                }
                if (_.contains(groupable_types, field.type)) {
                    self.groupable_fields[name] = field;
                }
            }
        });
        this.measures.__count__ = {string: "Quantity", type: "integer"};
    },
    do_search: function (domain, context, group_by) {
        if (!this.ready) {
            this.initial_row_groupby = context.pivot_row_groupby || this.initial_row_groupby;
            this.initial_col_groupby = context.pivot_col_groupby || this.initial_col_groupby;
        }
        this.main_row.groupbys = group_by.length ? group_by : this.initial_row_groupby.slice(0);
        this.main_col.groupbys = context.pivot_column_groupby || this.initial_col_groupby.slice(0);
        this.active_measures = context.pivot_measures || this.active_measures;

        this.domain = domain;
        this.context = context;
        if (!this.ready) {
            this.data_loaded = this.load_data(true);
            this.ready = true;
            return;
        }
        this.data_loaded = this.load_data(false);
        return this.do_show();
    },
    do_show: function () {
        var self = this;
        if (this.sidebar) {
            this.sidebar.$el.show();
        }
        this.do_push_state({});
        this.data_loaded.done(function () {
            self.display_table(); 
            self.$el.show();
        });
        return this._super();
    },
    do_hide: function () {
        if (this.sidebar) {
            this.sidebar.$el.hide();
        }
        this._super();
    },
    get_context: function () {
        return !this.ready ? {} : {
            pivot_measures: this.active_measures,
            pivot_column_groupby: this.main_col.groupbys,
            pivot_row_groupby: this.main_row.groupbys,
        };
    },
    on_button_click: function (event) {
        var $target = $(event.target);
        if ($target.hasClass('oe-pivot-flip')) { return this.flip();}
        if ($target.hasClass('oe-pivot-expand-all')) {return this.expand_all();}
        if ($target.parents('.oe-measure-list').length) {
            var parent = $target.parent(),
                field = parent.data('field');
            parent.toggleClass('selected');
            event.stopPropagation();
            return this.toggle_measure(field);
        }
        if ($target.hasClass('oe-pivot-download')) {
            return this.dowload_table();
        }
    },
    on_open_header_click: function (event) {
        var id = $(event.target).data('id'),
            header = this.headers[id];
        header.expanded = false;        
        header.children = [];
        var new_groupby_length = this.get_header_depth(header.root) - 1;
        header.root.groupbys.splice(new_groupby_length);
        this.display_table();
    },
    on_closed_header_click: function (event) {
        var id = $(event.target).data('id'),
            header = this.headers[id],
            groupbys = header.root.groupbys;
        if (header.path.length - 1 < groupbys.length) {
            this.expand_header(header, groupbys[header.path.length - 1])
                .then(this.proxy('display_table'));
        } else {
            var $test = $(event.target);
            var pos = $test.position();
            this.last_header_selected = id;
            var $menu = this.$field_selection.find('ul').first();
            $menu.css('top', pos.top + $test.parent().height() - 2);
            $menu.css('left', pos.left + event.offsetX);
            $menu.show();
            event.stopPropagation();            
        }
    },
    on_cell_click: function (event) {
        var $target = $(event.target);
        if ($target.hasClass('oe-closed') 
            || $target.hasClass('oe-opened') 
            || $target.hasClass('oe-empty')
            || !this.enable_linking) {
            return;
        }
        var row_id = $target.data('id'),
            col_id = $target.data('col_id'),
            row_domain = this.headers[row_id].domain,
            col_domain = this.headers[col_id].domain,
            context = _.omit(_.clone(this.context), 'group_by');

        return this.do_action({
            type: 'ir.actions.act_window',
            name: this.title,
            res_model: this.model.name,
            views: [[false, 'list'], [false, 'form']],
            view_type : "list",
            view_mode : "list",
            target: 'current',
            context: context,
            domain: this.domain.concat(row_domain, col_domain),
        });
    },
    on_measure_row_click: function (event) {
        var $target = $(event.target),
            col_id = $target.data('id'),
            measure = $target.data('measure');

        this.sort_rows(col_id, measure, $target.hasClass('o-sorted-asc'));
        this.display_table();
    },
    sort_rows: function (col_id, measure, descending) {
        console.log('order', descending);
        var self = this;
        traverse_tree(this.main_row.root, function (header) { 
            header.children.sort(compare);
        });
        this.sorted_column = {
            id: col_id,
            measure: measure,
            order: descending ? 'desc' : 'asc',
        };

        function compare (row1, row2) {
            var values1 = self.get_value(row1.id, col_id),
                values2 = self.get_value(row2.id, col_id),
                value1 = values1 ? values1[measure] : 0,
                value2 = values2 ? values2[measure] : 0;
            return descending ? value1 - value2 : value2 - value1;
        }
    },
    on_field_menu_selection: function (event) {
        var self = this;
        var field = $(event.target).parent().data('field'),
            interval = $(event.target).data('interval'),
            header = this.headers[this.last_header_selected];
        if (interval) field = field + ':' + interval;
        this.expand_header(header, field)
            .then(function () {
                header.root.groupbys.push(field);
            })
            .then(this.proxy('display_table'));
    },
    expand_header: function (header, field) {
        var self = this;

        var other_root = header.root.other_root,
            this_groupbys = header.root.groupbys,
            other_groupbys = header.root.other_root.groupbys,
            fields = [].concat(field, other_groupbys, this.active_measures),
            groupbys = [];

        for (var i = 0; i <= other_groupbys.length; i++) {
            groupbys.push([field].concat(other_groupbys.slice(0,i)));
        }
        return $.when.apply(null, groupbys.map(function (groupby) {
            return self.model.query(fields)
                .filter(header.domain.length ? header.domain : self.domain)
                .context(self.context)
                .lazy(false)
                .group_by(groupby);
        })).then(function () {
            var data = Array.prototype.slice.call(arguments),
                datapt, attrs, j, k, l, row, col, cell_value, field_name;
            for (i = 0; i < data.length; i++) {
                for (j = 0; j < data[i].length; j++){
                    datapt = data[i][j];
                    attrs = datapt.attributes;
                    if (i === 0) attrs.value = [attrs.value];
                    for (k = 0; k < attrs.value.length; k++) {
                        if (k < 1) field_name = field;
                        else field_name = other_groupbys[k - 1];
                        attrs.value[k] = self.sanitize_value(attrs.value[k], field_name);
                    }
                    if (i === 0) {
                        row = self.make_header(datapt, header.root, 0, 1, header);
                    } else {
                        row = self.get_header(datapt, header.root, 0, 1, header);
                    }
                    col = self.get_header(datapt, other_root, 1, i + 1);
                    if (!col) continue;
                    for (cell_value = {}, l=0; l < self.active_measures.length; l++) {
                        cell_value[self.active_measures[l]] = attrs.aggregates[self.active_measures[l]];
                    }
                    cell_value.__count__ = attrs.length;
                    if (!self.cells[row.id]) self.cells[row.id] = [];
                    self.cells[row.id][col.id] = cell_value;
                }
            }
        });
    },
    expand_all: function () {
        this.load_data(false).then(this.proxy('display_table'));
    },
    // returns a deferred that resolve when the data is loaded.
    load_data: function (update) {
        var should_update = (update && this.main_row.root && this.main_col.root);
        var self = this,
            i, j, 
            groupbys = [],
            row_gbs = this.main_row.groupbys,
            col_gbs = this.main_col.groupbys,
            fields = [].concat(row_gbs, col_gbs, this.active_measures);
        for (i = 0; i < row_gbs.length + 1; i++) {
            for (j = 0; j < col_gbs.length + 1; j++) {
                groupbys.push(row_gbs.slice(0,i).concat(col_gbs.slice(0,j)));
            }
        }
        return $.when.apply(null, groupbys.map(function (groupby) {
            return self.model.query(fields)
                .filter(self.domain)
                .context(self.context)
                .lazy(false)
                // .order_by(['probable_revenue'])
                .group_by(groupby);
        })).then(function () {
            var data = Array.prototype.slice.call(arguments);
            self.prepare_data(data, should_update);
        });
    },
    prepare_data: function (data, should_update) {
        var i, j, k, l, m,
            index = 0,
            row_gbs = this.main_row.groupbys,
            col_gbs = this.main_col.groupbys,
            main_row_header, main_col_header,
            row, col, attrs, datapt, cell_value,
            field;

        for (i = 0; i < row_gbs.length + 1; i++) {
            for (j = 0; j < col_gbs.length + 1; j++) {
                for (k = 0; k < data[index].length; k++) {
                    datapt = data[index][k];
                    attrs = datapt.attributes;
                    if (i + j === 1) {
                        attrs.value = [attrs.value];
                    }
                    for (l = 0; l < attrs.value.length; l++) {
                        if (l < i) field = row_gbs[l];
                        else field = col_gbs[l - i];
                        attrs.value[l] = this.sanitize_value(attrs.value[l], field);
                    }
                    if (j === 0) {
                        row = this.make_header(datapt, main_row_header, 0, i);
                    } else {
                        row = this.get_header(datapt, main_row_header, 0, i);
                    }
                    if (i === 0) {
                        col = this.make_header(datapt, main_col_header, i, i+j);
                    } else {
                        col = this.get_header(datapt, main_col_header, i, i+j);
                    }
                    if (i + j === 0) {
                        this.has_data = attrs.length > 0;
                        main_row_header = row;
                        main_col_header = col;
                    }
                    if (!this.cells[row.id]) this.cells[row.id] = [];
                    for (cell_value = {}, m=0; m < this.active_measures.length; m++) {
                        cell_value[this.active_measures[m]] = attrs.aggregates[this.active_measures[m]];
                    }
                    cell_value.__count__ = attrs.length;
                    this.cells[row.id][col.id] = cell_value;
                }
                index++;
            }
        }
        if (should_update) {
            this.update_tree(this.main_row.root, main_row_header);
            var new_groupby_length = this.get_header_depth(main_row_header) - 1;
            main_row_header.groupbys = this.main_row.root.groupbys.slice(0, new_groupby_length);
            this.update_tree(this.main_col.root, main_col_header);
            new_groupby_length = this.get_header_depth(main_col_header) - 1;
            main_col_header.groupbys = this.main_col.root.groupbys.slice(0, new_groupby_length);
        } else {
            main_row_header.groupbys = this.main_row.groupbys;
            main_col_header.groupbys = this.main_col.groupbys;
        }
        main_row_header.other_root = main_col_header;
        main_col_header.other_root = main_row_header;
        this.main_row.root = main_row_header;
        this.main_col.root = main_col_header;
    },
    update_tree: function (old_tree, new_tree) {
        if (!old_tree.expanded) {
            new_tree.expanded = false;
            new_tree.children = [];
            return;
        }
        var tree, j, old_title, new_title;
        for (var i = 0; i < new_tree.children.length; i++) {
            tree = undefined;
            new_title = new_tree.children[i].path[new_tree.children[i].path.length - 1];
            for (j = 0; j < old_tree.children.length; j++) {
                old_title = old_tree.children[j].path[old_tree.children[j].path.length - 1];
                if (old_title === new_title) {
                    tree = old_tree.children[j];
                    break;
                }
            }
            if (tree) this.update_tree(tree, new_tree.children[i]);
            else {
                new_tree.children[i].expanded = false;
                new_tree.children[i].children = [];
            }
        }
    },
    sanitize_value: function (value, field) {
        if (value === false) return _t("Undefined");
        if (value instanceof Array) return value[1];
        if (field && this.fields[field] && (this.fields[field].type === 'selection')) {
            var selected = _.where(this.fields[field].selection, {0: value})[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
    make_header: function (data_pt, root, i, j, parent_header) {
        var attrs = data_pt.attributes,
            value = attrs.value,
            title = value.length ? value[value.length - 1] : total;
        var path, parent;
        if (parent_header) {
            path = parent_header.path.concat(title);
            parent = parent_header;
        } else {
            path = [total].concat(value.slice(i,j-1));
            parent = value.length ? find_path_in_tree(root, path) : null;
        } 
        var header = {
            id: generate_id(),
            expanded: false,
            domain: data_pt.model._domain,
            children: [],
            path: value.length ? parent.path.concat(title) : [title]
        };
        this.headers[header.id] = header;
        header.root = root || header;
        if (parent) {
            parent.children.push(header);
            parent.expanded = true;
        }
        return header;
    },
    get_header: function (data_pt, root, i, j, parent) {
        var path;
        if (parent) {
            path = parent.path.concat(data_pt.attributes.value.slice(i,j));
        } else {
            path = [total].concat(data_pt.attributes.value.slice(i,j));
        }
        return find_path_in_tree(root, path);
    },
    display_table: function () {
        if (!this.active_measures.length || !this.has_data) {
            return this.$table_container.empty().append(QWeb.render('PivotView.nodata'));
        }
        var $fragment = $(document.createDocumentFragment()),
            $table = $('<table>')
                .addClass('table table-hover table-condensed')
                .appendTo($fragment),
            $thead = $('<thead>').appendTo($table),
            $tbody = $('<tbody>').appendTo($table),
            headers = this.compute_headers(),
            rows = this.compute_rows(),
            nbr_measures = this.active_measures.length,
            nbr_cols = (this.main_col.width === 1) ? nbr_measures : (this.main_col.width + 1)*nbr_measures;
        for (var i=0; i < nbr_cols + 1; i++) {
            $table.prepend($('<col>'));
        }
        this.draw_headers($thead, headers);
        this.draw_rows($tbody, rows);
        $table.on('hover', 'td', function () {
            $table.find('col:eq(' + $(this).index()+')').toggleClass('hover');
        });
        this.$table_container.empty().append($fragment);
        this.$table_container.find('.oe-opened,.oe-closed').tooltip();
    },
    draw_headers: function ($thead, headers) {
        var self = this,
            i, j, cell, $row, $cell,
            display_total = this.main_col.width > 1;

        var groupby_labels = _.map(this.main_col.groupbys, function (gb) {
            return self.groupable_fields[gb.split(':')[0]].string;
        });

        for (i = 0; i < headers.length; i++) {
            $row = $('<tr>');
            for (j = 0; j < headers[i].length; j++) {
                cell = headers[i][j];
                $cell = $('<th>')
                    .text(cell.title)
                    .attr('rowspan', cell.height)
                    .attr('colspan', cell.width);
                if (cell.total) {
                    $cell.addClass('oe-total');
                }
                if (i > 0) {
                    $cell.attr('title', groupby_labels[i-1]);
                }
                if (cell.expanded !== undefined) {
                    $cell.addClass(cell.expanded ? 'oe-opened' : 'oe-closed');
                    $cell.data('id', cell.id);
                }
                if (cell.measure) {
                    $cell.addClass('measure-row text-muted')
                        .text(this.measures[cell.measure].string)
                        .toggleClass('oe-total', cell.is_bold);
                    $cell.data('id', cell.id).data('measure', cell.measure);
                    if (cell.id === this.sorted_column.id && cell.measure === this.sorted_column.measure) {
                        $cell.addClass('o-sorted o-sorted-' + this.sorted_column.order);
                    }
                }
                $row.append($cell);
            }
            $thead.append($row);
        }
    },
    draw_rows: function ($tbody, rows) {
        var self = this,
            i, j, value, $row, $cell, $header,
            nbr_measures = this.active_measures.length,
            length = rows[0].values.length,
            display_total = this.main_col.width > 1;

        var groupby_labels = _.map(this.main_row.groupbys, function (gb) {
            return self.groupable_fields[gb.split(':')[0]].string;
        });
        var measure_types = this.active_measures.map(function (name) {
            return self.measures[name].type;
        });
        for (i = 0; i < rows.length; i++) {
            $row = $('<tr>');
            $header = $('<td>')
                .text(rows[i].title)
                .data('id', rows[i].id)
                .css('padding-left', (5 + rows[i].indent * 30) + 'px')
                .addClass(rows[i].expanded ? 'oe-opened' : 'oe-closed');
            if (rows[i].indent > 0) $header.attr('title', groupby_labels[rows[i].indent - 1]);
            $header.appendTo($row);
            for (j = 0; j < length; j++) {
                value = format_value(rows[i].values[j], {type: measure_types[j % nbr_measures]});
                $cell = $('<td>')
                            .data('id', rows[i].id)
                            .data('col_id', rows[i].col_ids[Math.floor(j / nbr_measures)])
                            .toggleClass('oe-empty', !value)
                            .text(value);
                if (((j >= length - this.active_measures.length) && display_total) || i === 0){
                    $cell.css('font-weight', 'bold');
                }
                $row.append($cell);
            }
            $tbody.append($row);
        }
    },
    compute_headers: function () {
        var self = this,
            main_col_dims = this.get_header_width_depth(this.main_col.root),
            depth = main_col_dims.depth,
            width = main_col_dims.width,
            nbr_measures = this.active_measures.length,
            result = [[{width:1, height: depth + 1}]],
            col_ids = [];
        this.main_col.width = width;
        traverse_tree(this.main_col.root, function (header) {
            var index = header.path.length - 1,
                cell = {
                    width: self.get_header_width(header) * nbr_measures,
                    height: header.expanded ? 1 : depth - index,
                    title: header.path[header.path.length-1],
                    id: header.id,
                    expanded: header.expanded,
                };
            if (!header.expanded) col_ids.push(header.id);
            if (result[index]) result[index].push(cell);
            else result[index] = [cell];
        });
        col_ids.push(this.main_col.root.id);
        this.main_col.width = width;
        if (width > 1) {
            var total_cell = {width:nbr_measures, height: depth, title:""};
            if (nbr_measures === 1) {
                total_cell.title = this.measures[this.active_measures[0]].string;
                total_cell.total = true;
            }
            result[0].push(total_cell);
        }
        var nbr_cols = width === 1 ? nbr_measures : (width + 1)*nbr_measures;
        for (var i = 0, measure_row = [], measure; i < nbr_cols; i++) {
            measure = this.active_measures[i % nbr_measures];
            measure_row.push({
                measure: measure,
                is_bold: (width > 1) && (i >= nbr_measures*width),
                id: col_ids[Math.floor(i / nbr_measures)],
            });
        }
        result.push(measure_row);
        return result;
    },
    get_header_width: function (header) {
        var self = this;
        if (!header.children.length) return 1;
        if (!header.expanded) return 1;
        return header.children.reduce(function (s, c) {
            return s + self.get_header_width(c);
        }, 0);
    },
    get_header_width_depth: function (header) {
        var depth = 1,
            width = 0;
        traverse_tree (header, function (hdr) {
            depth = Math.max(depth, hdr.path.length);
            if (!hdr.expanded) width++;
        });
        return {width: width, depth: depth};
    },
    get_header_depth: function (header) {
        var depth = 1;
        traverse_tree(header, function (hdr) {
            depth = Math.max(depth, hdr.path.length);
        });
        return depth;
    },
    compute_rows: function () {
        var self = this,
            aggregates, i,
            result = [],
            nbr_measures = this.active_measures.length;
        traverse_tree(this.main_row.root, function (header) {
            var values = [],
                col_ids = [];
            result.push({
                id: header.id,
                col_ids: col_ids,
                indent: header.path.length - 1,
                title: header.path[header.path.length-1],
                expanded: header.expanded,
                values: values,              
            });
            traverse_tree(self.main_col.root, add_cells, header.id, values, col_ids);
            if (self.main_col.width > 1) {
                aggregates = self.get_value(header.id, self.main_col.root.id);
                for (i = 0; i < self.active_measures.length; i++) {
                    values.push(aggregates && aggregates[self.active_measures[i]]);
                }
                col_ids.push( self.main_col.root.id);
            }
        });
        return result;
        function add_cells (col_hdr, row_id, values, col_ids) {
            if (col_hdr.expanded) return;
            col_ids.push(col_hdr.id);
            aggregates = self.get_value(row_id, col_hdr.id);
            for (i = 0; i < self.active_measures.length; i++) {
                values.push(aggregates && aggregates[self.active_measures[i]]);
            }
        }
    },
    get_value: function (id1, id2) {
        if ((id1 in this.cells) && (id2 in this.cells[id1])) {
            return this.cells[id1][id2];
        }
        if (id2 in this.cells) return this.cells[id2][id1];
    },
    flip: function () {
        var temp = this.main_col;
        this.main_col = this.main_row;
        this.main_row = temp;
        this.display_table();
    },
    toggle_measure: function (field) {
        if (_.contains(this.active_measures, field)) {
            this.active_measures = _.without(this.active_measures, field);
            this.display_table();
        } else {
            this.active_measures.push(field);            
            this.load_data().then(this.display_table.bind(this));
        }
    },
    dowload_table: function () {
        openerp.web.blockUI();
        var nbr_measures = this.active_measures.length,
            headers = this.compute_headers(),
            measure_row = nbr_measures > 1 ? _.last(headers) : [],
            rows = this.compute_rows(),
            i, j, value;
        headers[0].splice(0,1);
        // process measure_row
        for (i = 0; i < measure_row.length; i++) {
            measure_row[i].measure = this.measures[measure_row[i].measure].string;
        }
        // process all rows
        for (i =0, j, value; i < rows.length; i++) {
            for (j = 0; j < rows[i].values.length; j++) {
                value = rows[i].values[j];
                rows[i].values[j] = {
                    is_bold: (i === 0) || ((this.main_col.width > 1) && (j >= rows[i].values.length - nbr_measures)),
                    value:  (value === undefined) ? "" : value,
                };
            }
        }
        var table = {
            headers: nbr_measures > 1 ? _.initial(headers) : headers,
            measure_row: measure_row,
            rows: rows,
            nbr_measures: nbr_measures,
            title: this.title,
        };
        var c = openerp.webclient.crashmanager;
        this.session.get_file({
            url: '/web/pivot/export_xls',
            data: {data: JSON.stringify(table)},
            complete: openerp.web.unblockUI,
            error: c.rpc_error.bind(c)
        });    
    },
});

// helpers
var id = -1;

function generate_id () {
    return ++id;
}

function traverse_tree(root, f, arg1, arg2, arg3) {
    f(root, arg1, arg2, arg3);
    if (!root.expanded) return;
    for (var i = 0; i < root.children.length; i++) {
        traverse_tree(root.children[i], f, arg1, arg2, arg3);
    }
}

function find_path_in_tree(root, path) {
    var i,
        l = root.path.length;
    if (l === path.length) {
        return (root.path[l-1] === path[l - 1]) ? root : null;
    }
    for (i = 0; i < root.children.length; i++) {
        if (root.children[i].path[l] === path[l]) {
            return find_path_in_tree(root.children[i], path);
        }
    }
    return null;
}

})();
