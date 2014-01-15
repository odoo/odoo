
/* jshint undef: false  */

(function () {
'use strict';

//  Pivot Table emits the events 'groupby_changed' and 'redraw_required' when necessary.
//  PivotTable is initialized by default 'inactive', and require a call to activate() 
//  after init to load initial data and start triggering events.
openerp.web_graph.PivotTable = openerp.web.Class.extend(openerp.EventDispatcherMixin, {

	init: function (model, domain, fields, options) {
        openerp.EventDispatcherMixin.init.call(this);
		this.cells = [];
		this.domain = domain;
		this.no_data = true;
		this.model = model;
		this.fields = fields;
        this.fields.__count = {type: 'integer', string:'Quantity'};
        this.measures = [{field:'__count', type: this.fields.type, string:this.fields.string}];
		this.active = false;
        this.rows = { groupby: this.create_field_values(options.row_groupby || []), headers: null };
        this.cols = { groupby: this.create_field_values(options.col_groupby || []), headers: null };
		if (options.measures) { this.set_measures(options.measures); }
	},

	// ----------------------------------------------------------------------
	// Configuration methods
	// ----------------------------------------------------------------------
    // this.measures: list of measure [measure], measure = {field: _, string: _, type: _}
    // this.rows.groupby, this.cols.groupby : list of groupbys used for describing rows (...),
    //      a groupby is also {field:_, string:_, type:_} but it also has a interval
    //      attribute if its type is date/datetime.
    // this.active: If PivotTable is active then it triggers events and updates 
    //      its values when necessary
	activate: function() {
		this.active = true;
		this.update_data();
	},

	set_measures: function (measures) {
        var self = this;
		if (!_.isEqual(measures, this.measures)) {
			this.measures = [];
            _.each(measures, function (m) { self._add_measure(m); });
			if (this.active) { this.update_data(); }
		}
	},

	_add_measure: function (measure) {
		if (measure.field && measure.string && measure.type) {
			this.measures.push(measure);
		} else {
			this.measures.push({
				field: measure,
				string: this.fields[measure].string,
				type: this.fields[measure].type,
			});
		}
	},

	toggle_measure: function (field_id) {
        var current_measure = _.findWhere(this.measures, {field:field_id});
        if (current_measure) {
            this.measures = _.without(this.measures, current_measure);
        } else {
            this.measures.push({
                field: field_id,
                type: this.fields[field_id].type,
                string: this.fields[field_id].string
            });
        }
        if (this.active) { this.update_data(); }
	},

    set: function (domain, row_groupby, col_groupby) {
        var row_gbs = this.create_field_values(row_groupby),
            col_gbs = this.create_field_values(col_groupby),
            dom_changed = !_.isEqual(this.domain, domain),
            row_gb_changed = !_.isEqual(row_gbs, this.rows.groupby),
            col_gb_changed = !_.isEqual(col_gbs, this.cols.groupby);

        if (dom_changed) {
            this.domain = domain;
        }
        if (row_gb_changed || col_gb_changed) {
            this.cols.groupby = col_gbs;
            this.rows.groupby = row_gbs;
            if (row_gb_changed) {this.rows.headers = null; }
            if (col_gb_changed) {this.cols.headers = null; }
            if (this.active) { this.trigger('groupby_changed'); }
        }
        if (this.active && (row_gb_changed || col_gb_changed || dom_changed)) {
            this.update_data();
        }
    },

    create_field_value: function (f) {
        if (f.field && f.interval) {
            return { field:f.field,
                     string: this.fields[f.field].string,
                     type:this.fields[f.field].type,
                     interval: f.interval };
        }
        return (f.field && f.string && f.type) ? f : { field: f,
                                                       string: this.fields[f].string,
                                                       type: this.fields[f].type };
    },

    create_field_values: function (field_ids) {
        var self = this;
        return _.map(field_ids, function (f) { return self.create_field_value(f); });
    },

	_add_groupby: function(groupby_list, groupby) {
        groupby_list.push(this.create_field_value(groupby));
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
		var cell = _.find(this.cells, function (c) {
					return ((c.x == Math.min(id1, id2)) && (c.y == Math.max(id1, id2)));
				});
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
		return !!_.find(this.rows.headers, function (header) {
			return header.id === id;
		});
	},

	is_col: function (id) {
		return !!_.find(this.cols.headers, function (header) {
			return header.id === id;
		});
	},

	get_header: function (id) {
		return _.find(this.rows.headers.concat(this.cols.headers), function (header) {
			return header.id === id;
		});
	},

	// return all columns with a path length of 'depth'
	get_cols_with_depth: function (depth) {
		return _.filter(this.cols.headers, function (header) {
			return header.path.length === depth;
		});
	},

	// return all rows with a path length of 'depth'
	get_rows_with_depth: function (depth) {
		return _.filter(this.rows.headers, function (header) {
			return header.path.length === depth;
		});
	},

	// return all non expanded rows
	get_rows_leaves: function () {
		return _.filter(this.rows.headers, function (header) {
			return !header.expanded;
		});
	},
	
	// return all non expanded cols
	get_cols_leaves: function () {
		return _.filter(this.cols.headers, function (header) {
			return !header.expanded;
		});
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
		if (header) {
			return this.get_values(header.id, this.get_other_root(header).headers[0].id);
		}
		return this.get_values(this.rows.headers[0].id, this.cols.headers[0].id);
	},

	get_other_root: function (header) {
		return (header.root === this.rows) ? this.cols : this.rows;
	},

    main_row: function () { return this.rows.headers[0]; },
    
    main_col: function () { return this.cols.headers[0]; },

	// ----------------------------------------------------------------------
	// Table manipulation methods : fold/expand/swap
	// ----------------------------------------------------------------------
	fold: function (header) {
		var ancestors = this.get_ancestors(header),
            removed_ids = _.pluck(ancestors, 'id');

		header.root.headers = _.difference(header.root.headers, ancestors);
        header.children = [];
		header.expanded = false;

        this.cells = _.reject(this.cells, function (cell) {
            return (_.contains(removed_ids, cell.x) || _.contains(removed_ids, cell.y));
        });

        var new_groupby_length = _.max(_.map(header.root.headers, function(g) {return g.path.length;}));
        if (new_groupby_length < header.root.groupby.length) {
			header.root.groupby.splice(new_groupby_length);
			this.trigger('groupby_changed');
        }
        this.trigger('redraw_required');
	},

	expand: function (header_id, groupby) {
        var self = this,
            header = this.get_header(header_id),
			otherRoot = this.get_other_root(header),
			fields = otherRoot.groupby.concat(this.measures);

        if (header.path.length === header.root.groupby.length) {
            self._add_groupby(header.root.groupby, groupby);
            this.trigger('groupby_changed');
        }
        groupby = [header.root.groupby[header.path.length]].concat(otherRoot.groupby);

        return this.get_groups(groupby, fields, header.domain)
            .then(function (groups) {
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
                self.trigger('redraw_required');
            });
	},

	make_header: function (group, parent) {
		var title = parent ? group.attributes.value : '';
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
		this.trigger('groupby_changed');
		this.trigger('redraw_required');
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
			self.trigger('redraw_required');
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

    expand_all: function () {
        this.rows.headers = null;
        this.cols.headers = null;
        this.update_data();
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

        var groupbys = _.map(_.range(cols.length + 1), function (i) {
            return cols.slice(0, i).concat(rows);
        });
        groupbys.push([]);

        var def_array = _.map(groupbys, function (groupby) {
            return self.get_groups(groupby, visible_fields, self.domain);
        });

        return $.when.apply(null, def_array).then(function () {
            var data = Array.prototype.slice.call(arguments),
                row_data = data[0],
                col_data = (cols.length !== 0) ? data[data.length - 2] : [],
                total = data[data.length - 1][0];

            return (total === undefined) ? undefined
                    : self.format_data(total, col_data, row_data, data);
        });
    },

	get_groups: function (groupbys, fields, domain, path) {
        path = path || [];
		var self = this,
            groupby = (groupbys.length) ? groupbys[0] : [];

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
            context = {};

        if (groupby.interval) {
            context.datetime_format = {};
            var display_format;
            switch (groupby.interval) {
                case 'day':
                    display_format = 'dd MMMM YYYY';
                    break;
                case 'week':
                    display_format = 'w YYYY';
                    break;
                case 'month':
                    display_format = 'MMMM YYYY';
                    break;
                case 'quarter':
                    display_format = 'QQQ YYYY';
                    break;
                case 'year':
                    display_format = 'YYYY';
                    break;
            }
            context.datetime_format[groupby.field] = {
                interval: groupby.interval,
                display_format: display_format
            };
        }
		return this.model.query(field_ids)
			.filter(domain)
            .context(context)
			.group_by(groupby.field)
			.then(function (results) {
				var groups = _.filter(results, function (group) {
					return group.attributes.length > 0;
				});
				return _.map(groups, function (g) { return self.format_group(g, path); });
			});
	},

    // add the path to the group and sanitize the value...
	format_group: function (group, current_path) {
         var value = group.attributes.value;

         if (group.attributes.grouped_on && this.fields[group.attributes.grouped_on].type === 'selection') {
             var selection = this.fields[group.attributes.grouped_on].selection,
                 value_lookup = _.find(selection, function (val) { return val[0] === value; });
             group.attributes.value = value_lookup ? value_lookup[1] : 'undefined';
         } else if (value === false) {
             group.attributes.value = 'undefined';
         } else if (value instanceof Array) {
             group.attributes.value = value[1];
         }

        group.path = value ? (current_path || []).concat(group.attributes.value) : [];
        group.attributes.aggregates.__count = group.attributes.length;

		return group;
	},

	format_data: function (total, col_data, row_data, cell_data) {
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
				values = _.map(self.measures, function (measure) {
					return (measure.field === '__count') ? attr.length : attr.aggregates[measure.field];
				});

			var row = _.find(rows, function (header) { return _.isEqual(header.path, path.slice(index)); });
			var col = _.find(cols, function (header) { return _.isEqual(header.path, path.slice(0, index)); });
			self.add_cell(row.id, col.id, values);

			if (group.children) {
				self.make_cells (group.children, index, path, rows, cols);
			}
		});
	},

});
})();


