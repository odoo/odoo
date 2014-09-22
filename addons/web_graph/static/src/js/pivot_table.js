
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
		this.model = model;
		this.fields = fields;
        this.fields.__count = {type: 'integer', string:_t('Quantity')};
        this.measures = options.measures || [];
        this.rows = { groupby: options.row_groupby, headers: null };
        this.cols = { groupby: options.col_groupby, headers: null };
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

    set: function (domain, row_groupby, col_groupby) {
        var row_gb_changed = !_.isEqual(row_groupby, this.rows.groupby),
            col_gb_changed = !_.isEqual(col_groupby, this.cols.groupby);
        
        this.domain = domain;
        this.rows.groupby = row_groupby;
        this.cols.groupby = col_groupby;

        if (row_gb_changed) { this.rows.headers = null; }
        if (col_gb_changed) { this.cols.headers = null; }

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
		var cell = _.findWhere(this.cells, {x: Math.min(id1, id2), y: Math.max(id1, id2)});
		return (cell !== undefined) ? cell.values : (default_values || new Array(this.measures.length));
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
        return  [].concat.apply([], _.map(header.children, function (c) {return self.get_ancestors_and_self(c); }));
    },

    get_ancestors_and_self: function (header) {
        var self = this;
        return [].concat.apply([header], _.map(header.children, function (c) { return self.get_ancestors_and_self(c); }));
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
			otherRoot = this.get_other_root(header),
			fields = otherRoot.groupby.concat(this.measures);

        if (header.path.length === header.root.groupby.length) {
            header.root.groupby.push(groupby);
        }
        groupby = [groupby].concat(otherRoot.groupby);

        return this.get_groups(groupby, fields, header.domain).then(function (groups) {
            _.each(groups.reverse(), function (group) {
                // make header
                var child = self.make_header(group, header);
                child.expanded = false;
                header.children.splice(0,0, child);
                header.root.headers.splice(header.root.headers.indexOf(header) + 1, 0, child);
                // make cells
                _.each(self.get_ancestors_and_self(group), function (data) {
                    var values = _.map(self.measures, function (m) {
                        return data.attributes.aggregates[m.field];
                    });
                    var other = _.find(otherRoot.headers, function (h) {
                        if (header.root === self.cols) {
                            return _.isEqual(data.path.slice(1), h.path);
                        } else {
                            return _.isEqual(_.rest(data.path), h.path);
                            }
                        });
                    if (other) {
                        self.add_cell(child.id, other.id, values);
                    }
                });
            });
            header.expanded = true;
        });
	},

	make_header: function (group, parent) {
		var title = parent ? group.attributes.value : _t('Total');
        return {
			id: _.uniqueId(),
			path: parent ? parent.path.concat(title) : [],
			title: title,
			children: [],
			domain: parent ? group.model._domain : this.domain,
			root: parent ? parent.root : undefined,
		};
	},

	swap_axis: function () {
		var temp = this.rows;
		this.rows = this.cols;
		this.cols = temp;
	},

	// ----------------------------------------------------------------------
	// Data updating methods
	// ----------------------------------------------------------------------
    // Load the data from the db, using the method this.load_data
    // update_data will try to preserve the expand/not expanded status of each
    // column/row.  If you want to expand all, then set this.cols.headers/this.rows.headers 
    // to null before calling update_data.
	update_data: function () {
		var self = this;

		return this.load_data().then (function (result) {
			if (result) {
				self.no_data = false;
				self[self.cols.headers ? 'update_headers' : 'expand_headers'](self.cols, result.col_headers);
				self[self.rows.headers ? 'update_headers' : 'expand_headers'](self.rows, result.row_headers);
			} else {
				self.no_data = true;
			}
		});
	},

	expand_headers: function (root, new_headers) {
		root.headers = new_headers;
		_.each(root.headers, function (header) {
			header.root = root;
			header.expanded = (header.children.length > 0);
		});
	},

	update_headers: function (root, new_headers) {
		_.each(root.headers, function (header) {
			var corresponding_header = _.find(new_headers, function (h) {
				return _.isEqual(h.path, header.path);
			});
			if (corresponding_header && header.expanded) {
				corresponding_header.expanded = true;
				_.each(corresponding_header.children, function (c) {
					c.expanded = false;
				});
			}
			if (corresponding_header && (!header.expanded)) {
				corresponding_header.expanded = false;
			}
		});
		var updated_headers = _.filter(new_headers, function (header) {
			return (header.expanded !== undefined);
		});
		_.each(updated_headers, function (header) {
			if (!header.expanded) {
				header.children = [];
			}
			header.root = root;
		});
		root.headers = updated_headers;
	},

    // ----------------------------------------------------------------------
    // Data loading methods
    // ----------------------------------------------------------------------

    // To obtain all the values required to draw the full table, we have to do 
    // at least      2 + min(row.groupby.length, col.groupby.length)
    // calls to readgroup. To simplify the code, we will always do 
    // 2 + row.groupby.length calls. For example, if row.groupby = [r1, r2, r3] 
    // and col.groupby = [c1, c2], then we will make the call with the following 
    // groupbys: [r1,r2,r3], [c1,r1,r2,r3], [c1,c2,r1,r2,r3], [].
    load_data: function () {
        var self = this,
            cols = this.cols.groupby,
            rows = this.rows.groupby,
            visible_fields = rows.concat(cols, self.measures);

        if (this.measures.length === 0) {
            return $.Deferred.resolve().promise();
        }

        var groupbys = _.map(_.range(cols.length + 1), function (i) {
            return cols.slice(0, i).concat(rows);
        });
        groupbys.push([]);

        var get_data_requests = _.map(groupbys, function (groupby) {
            return self.get_groups(groupby, visible_fields, self.domain);
        });

        return $.when.apply(null, get_data_requests).then(function () {
            var data = Array.prototype.slice.call(arguments),
                row_data = data[0],
                col_data = (cols.length !== 0) ? data[data.length - 2] : [],
                has_data = data[data.length - 1][0];

            return has_data && self.format_data(col_data, row_data, data);
        });
    },

	get_groups: function (groupbys, fields, domain, path) {
		var self = this,
            groupby = (groupbys.length) ? groupbys[0] : [];
        path = path || [];

		return this._query_db(groupby, fields, domain, path).then(function (groups) {
            if (groupbys.length > 1) {
                var get_subgroups = $.when.apply(null, _.map(groups, function (group) {
                    return self.get_groups(_.rest(groupbys), fields, group.model._domain, path.concat(group.attributes.value)).then(function (subgroups) {
                        group.children = subgroups;
                    });
                }));
                 return get_subgroups.then(function () {
                     return groups;
                 });
            } else {
                return groups;
            }
		});

	},

	_query_db: function (groupby, fields, domain, path) {
		var self = this,
            field_ids = _.without(_.pluck(fields, 'field'), '__count'),
            fields = _.map(field_ids, function(f) { return self.raw_field(f); });

		return this.model.query(field_ids)
			.filter(domain)
            .context(this.context)
			.group_by(groupby.field)
			.then(function (results) {
				var groups = _.filter(results, function (group) {
					return group.attributes.length > 0;
				});
				return _.map(groups, function (g) { return self.format_group(g, path); });
			});
	},

    // if field is a fieldname, returns field, if field is field_id:interval, retuns field_id
    raw_field: function (field) {
        return field.split(':')[0];
    },

    // add the path to the group and sanitize the value...
    format_group: function (group, current_path) {
        var attrs = group.attributes,
            value = attrs.value,
            grouped_on = attrs.grouped_on ? this.raw_field(attrs.grouped_on) : false;

        if (value === false) {
            group.attributes.value = _t('Undefined');
        } else if (grouped_on && this.fields[grouped_on].type === 'selection') {
            var selection = this.fields[grouped_on].selection,
                value_lookup = _.where(selection, {0:value}); 
            group.attributes.value = !_.isEmpty(value_lookup) ? value_lookup[0][1] : _t('Undefined');
        } else if (value instanceof Array) {
            group.attributes.value = value[1];
        }

        group.path = (value !== undefined) ? (current_path || []).concat(group.attributes.value) : [];
        group.attributes.aggregates.__count = group.attributes.length;

        return group;
    },

	format_data: function (col_data, row_data, cell_data) {
		var self = this,
			dim_row = this.rows.groupby.length,
			dim_col = this.cols.groupby.length,
            col_headers = this.get_ancestors_and_self(this.make_headers(col_data, dim_col)),
            row_headers = this.get_ancestors_and_self(this.make_headers(row_data, dim_row));

        this.cells = [];
		_.each(cell_data, function (data, index) {
			self.make_cells(data, index, [], row_headers, col_headers);
		}); // not pretty. make it more functional?

		return {col_headers: col_headers, row_headers: row_headers};
	},

	make_headers: function (data, depth, parent) {
		var self = this,
            main = this.make_header(data, parent);

		if (main.path.length < depth) {
			main.children = _.map(data.children || data, function (data_pt) {
				return self.make_headers (data_pt, depth, main);
			});
		}
		return main;
	},

	make_cells: function (data, index, current_path, rows, cols) {
		var self = this;
		_.each(data, function (group) {
			var attr = group.attributes,
				path = attr.grouped_on ? current_path.concat(attr.value) : current_path,
				values = _.map(self.measures, function (measure) { return attr.aggregates[measure.field]; }),
                row = _.find(rows, function (header) { return _.isEqual(header.path, path.slice(index)); }),
                col = _.find(cols, function (header) { return _.isEqual(header.path, path.slice(0, index)); });

			self.add_cell(row.id, col.id, values);
			if (group.children) {
				self.make_cells (group.children, index, path, rows, cols);
			}
		});
	},

});

})();


