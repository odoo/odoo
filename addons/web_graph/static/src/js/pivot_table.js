
/* jshint undef: false  */

(function () {
'use strict';

var _lt = openerp.web._lt;
var _t = openerp.web._t;

//  PivotTable requires a call to update_data after initialization
openerp.web_graph.PivotTable = openerp.web.Class.extend({

	init: function (model, domain, fields, options) {
		this.cells = [];
		this.domain = domain;
        this.context = options.context;
		this.no_data = true;
		this.updating = false;
		this.model = model;
		this.fields = fields;
        this.fields.__count = {type: 'integer', string:_t('Count')};
        this.measures = options.measures || [];
        this.rows = { groupby: options.row_groupby, headers: null };
        this.cols = { groupby: options.col_groupby, headers: null };
        this.numbering = {};
	},

	// ----------------------------------------------------------------------
	// Configuration methods
	// ----------------------------------------------------------------------
    // this.measures: list of measure [measure], measure = {field: _, string: _, type: _}
    // this.rows.groupby, this.cols.groupby : list of groupbys used for describing rows (...),
    //      a groupby is also {field:_, string:_, type:_}
    //      If its type is date/datetime, field can have the corresponding interval in its description,
    //      for example 'create_date:week'.
	set_measures: function (measures) {
        this.measures = measures;
        return this.update_data();
	},

	toggle_measure: function (measure) {
        var current_measure = _.findWhere(this.measures, measure);
        if (current_measure) {  // remove current_measure
            var index = this.measures.indexOf(current_measure);
            this.measures = _.without(this.measures, current_measure);
            if (this.measures.length === 0) {
                this.no_data = true;
            } else {
                _.each(this.cells, function (cell) {
                    cell.values.splice(index, 1);
                });
            }
            return $.Deferred().resolve();
        } else {  // add a new measure
            this.measures.push(measure);
            return this.update_data();
        }
	},

    set: function (domain, row_groupby, col_groupby, measures_groupby) {
        var self = this;
        if (this.updating) {
            return this.updating.then(function () {
                self.updating = false;
                return self.set(domain, row_groupby, col_groupby, measures_groupby);
            });
        }
        var row_gb_changed = !_.isEqual(row_groupby, this.rows.groupby),
            col_gb_changed = !_.isEqual(col_groupby, this.cols.groupby),
			measures_gb_changed = !_.isEqual(measures_groupby, this.measures);

        this.domain = domain;
        this.rows.groupby = row_groupby;
        this.cols.groupby = col_groupby;

		if (measures_groupby.length) { this.measures = measures_groupby; }

        if (row_gb_changed) { this.rows.headers = null; }
        if (col_gb_changed) { this.cols.headers = null; }
		if (measures_gb_changed && measures_groupby.length) { this.set_measures(measures_groupby); }

        return this.update_data();
    },

	// ----------------------------------------------------------------------
	// Cells manipulation methods
	// ----------------------------------------------------------------------
    // cells are objects {x:_, y:_, values:_} where x < y and values is an array
    //       of values (one for each measure).  The condition x < y might look
    //       unnecessary, but it makes the rest of the code simpler: headers
    //       don't krow if they are rows or cols, they just know their id, so
    //       it is useful that a call get_values(id1, id2) is the same as get_values(id2, id1)
	add_cell : function (id1, id2, values) {
		this.cells.push({x: Math.min(id1, id2), y: Math.max(id1, id2), values: values});
	},

	get_values: function (id1, id2, default_values) {
        var cells = this.cells,
            x = Math.min(id1, id2),
            y = Math.max(id1, id2);
        for (var i = 0; i < cells.length; i++) {
            if (cells[i].x == x && cells[i].y == y) {
                return cells[i].values;
            }
        }
        return (default_values || new Array(this.measures.length));
	},

	// ----------------------------------------------------------------------
	// Headers/Rows/Cols manipulation methods
	// ----------------------------------------------------------------------
    // this.rows.headers, this.cols.headers = [header] describe the tree structure
    //      of rows/cols.  Headers are objects
    //      {
    //          id:_,               (unique id obviously)
    //          path: [...],        (array of all parents title, with its own title at the end)
    //          title:_,            (name of the row/col)
    //          children:[_],       (subrows or sub cols of this row/col)
    //          domain:_,           (domain of data in this row/col)
    //          root:_              (ref to this.rows or this.cols corresponding to the header)
    //          expanded:_          (boolean, true if it has been expanded)
    //      }
	is_row: function (id) {
        return !!_.findWhere(this.rows.headers, {id:id});
    },

	is_col: function (id) {
        return !!_.findWhere(this.cols.headers, {id:id});
	},

	get_header: function (id) {
		return _.findWhere(this.rows.headers.concat(this.cols.headers), {id:id});
	},

    _get_headers_with_depth: function (headers, depth) {
        return _.filter(headers, function (header) {
            return header.path.length === depth;
        });
    },

	// return all columns with a path length of 'depth'
	get_cols_with_depth: function (depth) {
        return this._get_headers_with_depth(this.cols.headers, depth);
	},

	// return all rows with a path length of 'depth'
	get_rows_with_depth: function (depth) {
        return this._get_headers_with_depth(this.rows.headers, depth);
	},

    get_ancestor_leaves: function (header) {
        return _.where(this.get_ancestors_and_self(header), {expanded:false});
    },

	// return all non expanded rows
	get_rows_leaves: function () {
		return _.where(this.rows.headers, {expanded:false});
	},

	// return all non expanded cols
	get_cols_leaves: function () {
		return _.where(this.cols.headers, {expanded:false});
	},

    get_ancestors: function (header) {
        var self = this;
        if (!header.children) return [];
        return  [].concat.apply([], _.map(header.children, function (c) {
            return self.get_ancestors_and_self(c);
        }));
    },

    get_ancestors_and_self: function (header) {
        var self = this;
        return [].concat.apply([header], _.map(header.children, function (c) {
            return self.get_ancestors_and_self(c);
        }));
    },

	get_total: function (header) {
        return (header) ? this.get_values(header.id, this.get_other_root(header).headers[0].id)
                        : this.get_values(this.rows.headers[0].id, this.cols.headers[0].id);
	},

	get_other_root: function (header) {
		return (header.root === this.rows) ? this.cols : this.rows;
	},

    main_row: function () { return this.rows.headers[0]; },

    main_col: function () { return this.cols.headers[0]; },

	// ----------------------------------------------------------------------
	// Table manipulation methods : fold/expand/swap
	// ----------------------------------------------------------------------
	// return true if the folding changed the groupbys, false if not
    fold: function (header) {
		var ancestors = this.get_ancestors(header),
            removed_ids = _.pluck(ancestors, 'id');

		header.root.headers = _.difference(header.root.headers, ancestors);
        header.children = [];
		header.expanded = false;

        this.cells = _.reject(this.cells, function (cell) {
            return (_.contains(removed_ids, cell.x) || _.contains(removed_ids, cell.y));
        });

        var new_groupby_length = _.max(_.pluck(_.pluck(header.root.headers, 'path'), 'length'));
        if (new_groupby_length < header.root.groupby.length) {
			header.root.groupby.splice(new_groupby_length);
            return true;
        }
        return false;
	},

    fold_with_depth: function (root, depth) {
        var self = this;
        _.each(this._get_headers_with_depth(root.headers, depth), function (header) {
            self.fold(header);
        });
    },

    expand_all: function () {
        this.rows.headers = null;
        this.cols.headers = null;
        return this.update_data();
    },

	expand: function (header_id, groupby) {
        var self = this,
            header = this.get_header(header_id),
            other_root = this.get_other_root(header),
            this_gb = [groupby.field],
            other_gbs = _.pluck(other_root.groupby, 'field');

        if (header.path.length === header.root.groupby.length) {
            header.root.groupby.push(groupby);
        }
        return this.perform_requests(this_gb, other_gbs, header.domain).then(function () {
            var data = Array.prototype.slice.call(arguments).slice(other_gbs.length + 1);
            _.each(data, function (data_pt) {
                self.make_headers_and_cell(
                    data_pt, header.root.headers, other_root.headers, 1, header.path, true);
            });
            header.expanded = true;
            header.children.forEach(function (child) {
                child.expanded = false;
                child.root = header.root;
            });
        });
	},

	swap_axis: function () {
		var temp = this.rows;
		this.rows = this.cols;
		this.cols = temp;
	},

	// ----------------------------------------------------------------------
	// Data updating methods
	// ----------------------------------------------------------------------
    // update_data will try to preserve the expand/not expanded status of each
    // column/row.  If you want to expand all, then set this.cols.headers/this.rows.headers
    // to null before calling update_data.
    update_data: function () {
        var self = this;
        this.updating = this.perform_requests().then (function () {
            var data = Array.prototype.slice.call(arguments);
            self.no_data = !data[0].length;
            if (self.no_data) {
                return;
            }
            var row_headers = [],
                col_headers = [];
            self.cells = [];

            var dim_col = self.cols.groupby.length,
                i, j, index;

            for (i = 0; i < self.rows.groupby.length + 1; i++) {
                for (j = 0; j < dim_col + 1; j++) {
                    index = i*(dim_col + 1) + j;
                    self.make_headers_and_cell(data[index], row_headers, col_headers, i);
                }
            }
            self.set_headers(row_headers, self.rows);
            self.set_headers(col_headers, self.cols);
        });
        return this.updating;
    },

    make_headers_and_cell: function (data_pts, row_headers, col_headers, index, prefix, expand) {
        var self = this;
        data_pts.forEach(function (data_pt) {
            var row_value = (prefix || []).concat(data_pt.attributes.value.slice(0,index));
            var col_value = data_pt.attributes.value.slice(index);

            if (expand && !_.find(col_headers, function (hdr) {return self.isEqual(col_value, hdr.path);})) {
                return;
            }
            var row = self.find_or_create_header(row_headers, row_value, data_pt);
            var col = self.find_or_create_header(col_headers, col_value, data_pt);

            var cell_value = _.map(self.measures, function (m) {
                return data_pt.attributes.aggregates[m.field];
            });
            self.cells.push({
                x: Math.min(row.id, col.id),
                y: Math.max(row.id, col.id),
                values: cell_value
            });
        });
    },

    make_header: function (values) {
        return _.extend({
            children: [],
            domain: this.domain,
            expanded: undefined,
            id: _.uniqueId(),
            path: [],
            root: undefined,
            title: undefined
        }, values || {});
    },

    find_or_create_header: function (headers, path, data_pt) {
        var self = this;
        var hdr = _.find(headers, function (header) {
            return self.isEqual(path, header.path);
        });
        if (hdr) {
            return hdr;
        }
        if (!path.length) {
            hdr = this.make_header({title: _t('Total')});
            headers.push(hdr);
            return hdr;
        }
        hdr = this.make_header({
            path:path,
            domain:data_pt.model._domain,
            title: _t(_.last(path))
        });
        var parent = _.find(headers, function (header) {
            return self.isEqual(header.path, _.initial(path, 1));
        });

        var previous = parent.children.length ? _.last(parent.children) : parent;
        headers.splice(headers.indexOf(previous) + 1, 0, hdr);
        parent.children.push(hdr);
        return hdr;
    },

    perform_requests: function (group1, group2, domain) {
        var self = this,
            requests = [],
            row_gbs = _.pluck(this.rows.groupby, 'field'),
            col_gbs = _.pluck(this.cols.groupby, 'field'),
            field_list = row_gbs.concat(col_gbs, _.pluck(this.measures, 'field')),
            fields = field_list.map(function (f) { return self.raw_field(f); });

        group1 = group1 || row_gbs;
        group2 = group2 || col_gbs;

        var i,j, groupbys;
        for (i = 0; i < group1.length + 1; i++) {
            for (j = 0; j < group2.length + 1; j++) {
                groupbys = group1.slice(0,i).concat(group2.slice(0,j));
                requests.push(self.get_groups(groupbys, fields, domain || self.domain));
            }
        }
        return $.when.apply(null, requests);
    },

    // set the 'expanded' status of new_headers more or less like root.headers, with root as root
    set_headers: function(new_headers, root) {
        var self = this;
        if (root.headers) {
            _.each(root.headers, function (header) {
                var corresponding_header = _.find(new_headers, function (h) {
                    return self.isEqual(h.path, header.path);
                });
                if (corresponding_header && header.expanded) {
                    corresponding_header.expanded = true;
                    _.each(corresponding_header.children, function (c) {
                        c.expanded = false;
                    });
                }
                if (corresponding_header && (!header.expanded)) {
                    corresponding_header.expanded = false;
                    corresponding_header.children = [];
                }
            });
            var updated_headers = _.filter(new_headers, function (header) {
                return (header.expanded !== undefined);
            });
            _.each(updated_headers, function (header) {
                header.root = root;
            });
            root.headers = updated_headers;
        } else {
            root.headers = new_headers;
            _.each(root.headers, function (header) {
                header.root = root;
                header.expanded = (header.children.length > 0);
            });
        }
        return new_headers;
    },

    get_groups: function (groupbys, fields, domain) {
        var self = this;
        return this.model.query(_.without(fields, '__count'))
            .filter(domain)
            .context(this.context)
            .lazy(false)
            .group_by(groupbys)
            .then(function (groups) {
                return groups.filter(function (group) {
                    return group.attributes.length > 0;
                }).map(function (group) {
                    var attrs = group.attributes,
                        grouped_on = attrs.grouped_on instanceof Array ? attrs.grouped_on : [attrs.grouped_on],
                        raw_grouped_on = grouped_on.map(function (f) {
                            return self.raw_field(f);
                        });
                    if (grouped_on.length === 1) {
                        attrs.value = [attrs.value];
                    }
                    attrs.value = _.range(grouped_on.length).map(function (i) {
                        var grp = grouped_on[i],
                            field = self.fields[grp];
                        if (attrs.value[i] === false) {
                            return _t('Undefined');
                        } else if (attrs.value[i] instanceof Array) {
                            return self.get_numbered_value(attrs.value[i], grp);
                        } else if (field && field.type === 'selection') {
                            var selected = _.where(field.selection, {0: attrs.value[i]})[0];
                            return selected ? self.get_numbered_value(selected, grp) : attrs.value[i];
                        }
                        return attrs.value[i];
                    });
                    attrs.aggregates.__count = group.attributes.length;
                    attrs.grouped_on = raw_grouped_on;
                    return group;
                });
            });
    },

    get_numbered_value: function(value, grp) {
        var id = value[0];
        var name = value[1]
        this.numbering[grp] = this.numbering[grp] || {};
        this.numbering[grp][name] = this.numbering[grp][name] || {};
        var numbers = this.numbering[grp][name];
        numbers[id] = numbers[id] || _.size(numbers) + 1;
        return name + (numbers[id] > 1 ? "  (" + numbers[id] + ")" : "");
    },

    // if field is a fieldname, returns field, if field is field_id:interval, retuns field_id
    raw_field: function (field) {
        return field.split(':')[0];
    },

    isEqual: function (path1, path2) {
        if (path1.length !== path2.length) { return false; }
        for (var i = 0; i < path1.length; i++) {
            if (path1[i] !== path2[i]) {
                return false;
            }
        }
        return true;
    },

});

})();
