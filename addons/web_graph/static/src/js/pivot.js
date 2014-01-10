
/* jshint undef: false  */

(function () {
'use strict';

// Pivot Table
//
//  Here is a short description of the way the data is organized:
//  Main fields:
//      cells = [cell]
//               cell = {x: _, y: _, values: [value]}
//               value = {type: _, value: _}
//      measures = [measure]
// 				  measure = {field: _, string: _, type: _}
//      rows, cols = {groupby: [groupby], headers: [header]}
//				groupby = {field: _, string: _, type: _, interval: _} (interval only if type = date/datetime)
// 				header = {
//					id: _,
//					path: _,
//					title: _,
//					expanded: _,
//					parent: _,
//					children: _,
//					domain: _,
//					root: _,
//				}
//
//  Pivot Table emits the events 'groupby_changed' and 'redraw_required' when necessary.
// PivotTable require a 'update_data' after init to be ready
// to do: add an option to enable/disable update_data at the end of init
openerp.web_graph.PivotTable = openerp.web.Class.extend(openerp.EventDispatcherMixin, {

	init: function (model, domain, fields, options) {
        openerp.EventDispatcherMixin.init.call(this);
		this.rows = { groupby: [], headers: null };
		this.cols = { groupby: [], headers: null };
		this.cells = [];
		this.domain = domain;
		this.no_data = true;
		this.model = model;
		this.fields = fields;
        this.fields.__count = {type: 'integer', string:'Quantity'};
        this.measures = [{field:'__count', type: this.fields.type, string:this.fields.string}];
		this.active = false;
		if (options.measures) { this.set_measures(options.measures); }
		if (options.col_groupby) { this.set_col_groupby(options.col_groupby); }
		if (options.row_groupby) { this.set_row_groupby(options.row_groupby); }
	},

	// ----------------------------------------------------------------------
	// Configuration methods
	// ----------------------------------------------------------------------
	activate: function() {
		this.active = true;
		this.update_data();
	},

	set_domain: function (domain) {
		this.domain = domain;
		if (this.active) { this.update_data(); }
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

	set_col_groupby: function (groupbys) {
		var self = this;
		if (!_.isEqual(groupbys, this.cols.groupby)) {
			this.cols.groupby = [];
			_.each(groupbys, function (g) { self._add_groupby(self.cols.groupby, g); });
			this.cols.headers = null;
			if (this.active) { 
                this.trigger('groupby_changed');
				this.update_data();
			}
		}
	},

	set_row_groupby: function (groupbys) {
		var self = this;
		if (!_.isEqual(groupbys, this.rows.groupby)) {
			this.rows.groupby = [];
			_.each(groupbys, function (g) { self._add_groupby(self.rows.groupby, g); });
			this.rows.headers = null;
			if (this.active) { 
                this.trigger('groupby_changed');
				this.update_data();
			}
		}
	},

	_add_groupby: function(groupby_list, groupby) {
		if (groupby.field && groupby.string && groupby.type) {
			groupby_list.push(groupby);
		} else {
			groupby_list.push({
				field:groupby,
				string: this.fields[groupby].string,
				type: this.fields[groupby].type
			});
		}
	},

	// ----------------------------------------------------------------------
	// Cells manipulation methods
	// ----------------------------------------------------------------------
	add_cell : function (id1, id2, values) {
		var x = Math.min(id1, id2),
			y = Math.max(id1, id2);
		this.cells.push({x: x, y: y, values: values});
	},

	get_values: function (id1, id2, default_values) {
		var x = Math.min(id1, id2),
			y = Math.max(id1, id2),
			cell = _.find(this.cells, function (c) {
					return ((c.x == x) && (c.y == y));
				});
		return (cell !== undefined) ? cell.values : (default_values || new Array(this.measures.length));
	},

	// ----------------------------------------------------------------------
	// Headers/Rows/Cols manipulation methods
	// ----------------------------------------------------------------------
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
	// Table manipulation methods
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
                    var child_id = self.make_header(group, header);
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
                            self.add_cell(child_id, other.id, values);
                        }
                    });
                });
                header.expanded = true;
                self.trigger('redraw_required');
            });
	},

	make_header: function (group, parent) {
		var title = group.attributes.value,
            new_header = {
				id: _.uniqueId(),
				path: parent.path.concat(title),
				title: title,
				expanded: false,
				children: [],
				domain: group.model._domain,
				root: parent.root,
			};
		parent.children.splice(0,0, new_header);
		parent.root.headers.splice(parent.root.headers.indexOf(parent) + 1, 0, new_header);
		return new_header.id;
	},

	swap_axis: function () {
		var temp = this.rows;
		this.rows = this.cols;
		this.cols = temp;
		this.trigger('groupby_changed');
		this.trigger('redraw_required');
	},

	// ----------------------------------------------------------------------
	// Data loading methods
	// ----------------------------------------------------------------------
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

	// options: fields: _, path_prefix: []
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
            field_ids = _.without(_.pluck(fields, 'field'), '__count');
        // To do : add code to check if groupby is date/datetime 
        //     and in that case, add the correct code to the context 
		return this.model.query(field_ids)
			.filter(domain)
			.group_by(groupby.field)
			.then(function (results) {
				var groups = _.filter(results, function (group) {
					return group.attributes.length > 0;
				});
				return _.map(groups, function (g) { return self.format_group(g, path); });
			});
	},

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

	format_data: function (total, col_data, row_data, cell_data) {
		var self = this,
			dim_row = this.rows.groupby.length,
			dim_col = this.cols.groupby.length,
            col_headers = this.get_ancestors_and_self(this.make_headers(col_data, dim_col)),
            row_headers = this.get_ancestors_and_self(this.make_headers(row_data, dim_row)),
			cells = [];

        this.cells = [];
		_.each(cell_data, function (data, index) {
			self.make_cells(data, index, [], row_headers, col_headers);
		}); // make it more functional?

		return {col_headers: col_headers,
                row_headers: row_headers};
	},

	make_headers: function (data, depth, parent) {
		var self = this,
			main = {
				id: _.uniqueId(),
				path: parent ? parent.path.concat(data.attributes.value) : [],
				children: [],
				title: parent ? data.attributes.value : '',
				domain: parent ? data.model._domain : this.domain,
			};

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


