
/* jshint undef: false  */

(function () {
'use strict';

openerp.web_graph.PivotTable = openerp.web.Class.extend(openerp.EventDispatcherMixin, {

	// PivotTable require a 'update_data' after init to be ready
	// to do: add an option to enable/disable update_data at the end of init
	init: function (model, domain) {
        openerp.EventDispatcherMixin.init.call(this);
		this.rows = { groupby: [], main: null, headers: null };
		this.cols = { groupby: [], main: null, headers: null };
		this.cells = [];
		this.domain = domain;
		this.measure = null;

		this.data_loader = new openerp.web_graph.DataLoader(model);

		this.no_data = true;
	},

	visible_fields: function () {
		var result = this.rows.groupby.concat(this.cols.groupby);
		if (this.measure) {
			result = result.concat(this.measure);
		}
		return result;
	},

	config: function (options) {
		var changed = false;
		var groupby_changed = false;
		var default_options = {
				update:true, 
				domain:this.domain, 
				col_groupby: this.cols.groupby,
				row_groupby: this.rows.groupby,
				measure: this.measure,
				silent:false
			};
		var options = _.extend(default_options, options);

		if (!_.isEqual(options.domain, this.domain)) {
			this.domain = options.domain;
			changed = true;
		}
		if (options.measure !== this.measure) {
			this.measure = options.measure;
			changed = true;
		}
		if (!_.isEqual(options.col_groupby, this.cols.groupby)) {
			this.cols.groupby = options.col_groupby;
			changed = true;
			this.cols.headers = null;
			groupby_changed = true;
		}
		if (!_.isEqual(options.row_groupby, this.rows.groupby)) {
			this.rows.groupby = options.row_groupby;
			this.rows.headers = null;
			changed = true;
			groupby_changed = true;
		}

		if (!options.silent && groupby_changed) { this.trigger('groupby_changed'); }
		if (options.update && changed) { this.update_data(); }
	},

	set_value: function (id1, id2, value) {
		var x = Math.min(id1, id2),
			y = Math.max(id1, id2),
			cell = _.find(this.cells, function (c) {
			return ((c.x == x) && (c.y == y));
		});
		if (cell) {
			cell.value = value;
		} else {
			this.cells.push({x: x, y: y, value: value});
		}
	},

	get_value: function (id1, id2, default_value) {
		var x = Math.min(id1, id2),
			y = Math.max(id1, id2),
			cell = _.find(this.cells, function (c) {
			return ((c.x == x) && (c.y == y));
		});
		return (cell === undefined) ? default_value : cell.value;
	},

	is_row: function (id) {
		return !!_.find(this.rows.headers, function (header) {
			return header.id == id;
		});
	},

	is_col: function (id) {
		return !!_.find(this.cols.headers, function (header) {
			return header.id == id;
		});
	},

	get_header: function (id) {
		return _.find(this.rows.headers.concat(this.cols.headers), function (header) {
			return header.id == id;
		});
	},

	// return all columns with a path length of 'depth'
	get_columns_depth: function (depth) {
		return _.filter(this.cols.headers, function (hdr) {
			return hdr.path.length === depth;
		});
	},

	// return all rows with a path length of 'depth'
	get_rows_depth: function (depth) {
		return _.filter(this.rows.headers, function (hdr) {
			return hdr.path.length === depth;
		});
	},

	// return all non expanded rows
	get_rows_leaves: function () {
		return _.filter(this.rows.headers, function (hdr) {
			return !hdr.is_expanded;
		});
	},
	
	// return all non expanded cols
	get_cols_leaves: function () {
		return _.filter(this.cols.headers, function (hdr) {
			return !hdr.is_expanded;
		});
	},
	
	fold: function (header) {
		var list = [];
		function tree_traversal(tree) {
			list.push(tree);
			_.each(tree.children, tree_traversal);
		}
		tree_traversal(header);
		var ids_to_remove = _.map(_.rest(list), function (h) { return h.id;});

		header.root.headers = _.difference(header.root.headers, _.rest(list));
		header.is_expanded = false;
        var fold_lvls = _.map(header.root.headers, function(g) {return g.path.length;});
        var new_groupby_length = _.max(fold_lvls);

        header.children = [];
        this.cells = _.reject(this.cells, function (cell) {
            return (_.contains(ids_to_remove, cell.x) || _.contains(ids_to_remove, cell.y));
        });
        if (new_groupby_length < header.root.groupby.length) {
			header.root.groupby.splice(new_groupby_length);
			this.trigger('groupby_changed');
        }
        this.trigger('redraw_required');
	},

	expand: function (header_id, field_id) {
        var self = this,
            header = this.get_header(header_id);

        if (header.path.length == header.root.groupby.length) {
            header.root.groupby.push(field_id);
            this.trigger('groupby_changed');
        }

        var otherDim = (header.root === this.cols) ? this.rows : this.cols;
        return this.data_loader.get_groups(this.visible_fields(), header.domain, otherDim.groupby, {first_groupby:field_id, add_path:true})
            .then(function (groups) {
                _.each(groups.reverse(), function (group) {
                    var new_header_id = self.make_header(group, header);
                    _.each(group, function (data) {
						var other = _.find(otherDim.headers, function (h) {
							if (header.root === self.cols) {
								return _.isEqual(data.path.slice(1), h.path);
                            } else {
                                return _.isEqual(_.rest(data.path), h.path);
                            }
                        });
                        if (other) {
                            if (self.measure) {
                                self.set_value(new_header_id, other.id, data.attributes.aggregates[self.measure]);
                            } else {
                                self.set_value(new_header_id, other.id, data.attributes.length);
                            }
                        }
                    });
                });
                header.is_expanded = true;
                self.trigger('redraw_required');
            });
	},

	make_header: function (groups, parent) {
		var name = groups[0].attributes.value,
            new_header = {
				id: _.uniqueId(),
				path: parent.path.concat(name),
				title: name,
				is_expanded: false,
				parent: parent.id,
				children: [],
				domain: groups[0].model._domain,
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

	get_total: function (header) {
		if (header) {
			var main = (header.root === this.rows) ? this.cols.main : this.rows.main;
			return this.get_value(header.id, main.id);
		} else {
			return this.rows.main.total;
		}
	},

	update_data: function () {
		var self = this,
			options = {
				col_groupby: this.cols.groupby,
				row_groupby: this.rows.groupby,
				measure: this.measure,
				domain: this.domain,
			};

		return this.data_loader.load_data(options).then (function (result) {
			if (result) {
				self.no_data = false;
				if (self.cols.headers) {
					self.update_headers(self.cols, result.col_headers);
				} else {
					self.expand_headers(self.cols, result.col_headers);
				}
				if (self.rows.headers) {
					self.update_headers(self.rows, result.row_headers);
				} else {
					self.expand_headers(self.rows, result.row_headers);
				}
				self.cells = result.cells;
			} else {
				self.no_data = true;
			}
			self.trigger('redraw_required');
		});
	},

	expand_headers: function (root, new_headers) {
		root.headers = new_headers;
		root.main = new_headers[0];
		_.each(root.headers, function (header) {
			header.root = root;
			header.is_expanded = (header.children.length > 0);
		});
	},

	update_headers: function (root, new_headers) {
		_.each(root.headers, function (header) {
			var corresponding_header = _.find(new_headers, function (h) {
				return _.isEqual(h.path, header.path);
			});
			if (corresponding_header && (header.is_expanded)) {
				corresponding_header.is_expanded = true;
				_.each(corresponding_header.children, function (c) {
					c.is_expanded = false;
				});
			}
			if (corresponding_header && (!header.is_expanded)) {
				corresponding_header.is_expanded = false;
			}
		});
		var updated_headers = _.filter(new_headers, function (header) {
			return (header.is_expanded !== undefined);
		});
		_.each(updated_headers, function (hdr) {
			if (!hdr.is_expanded) {
				hdr.children = [];
			}
			hdr.root = root;
		});
		root.headers = updated_headers;
		root.main = root.headers[0];
	},

});

openerp.web_graph.DataLoader = openerp.web.Class.extend({
	init: function (model) {
		this.model = model;
	},

	get_groups: function (fields, domain, groupbys, options) {
		var self = this,
			options = (options) ? options : {},
			groupings = (options.first_groupby) ? [options.first_groupby].concat(groupbys) : groupbys;

		return this.query_db(fields, domain, groupings).then(function (groups) {
			return _.map(groups, function (group) {
				return (options.add_path) ?self.add_path(group, []) : group;
			});
		});

	},

	query_db: function (fields, domain, groupbys) {
		var self = this;
		return this.model.query(fields)
			.filter(domain)
			.group_by(groupbys)
			.then(function (results) {
				var non_empty_results = _.filter(results, function (group) {
					return group.attributes.length > 0;
				});
				_.each(non_empty_results, self.sanitize_value);
				if (groupbys.length <= 1) {
					return non_empty_results;
				} else {
					var get_subgroups = $.when.apply(null, _.map(non_empty_results, function (result) {
						var new_domain = result.model._domain;
						var new_groupings = groupbys.slice(1);
						return self.query_db(fields,new_domain, new_groupings).then(function (subgroups) {
							result.subgroups_data = subgroups;
						});
					}));
					return get_subgroups.then(function () {
						return non_empty_results;
					});
				}
			});
	},

	sanitize_value: function (group) {
		var value = group.attributes.value;
		if (value === false) {
			group.attributes.value = 'undefined';
		} else if (value instanceof Array) {
			group.attributes.value = value[1];
		} else {
			group.attributes.value = value;
		}
	},

	add_path: function (group, current_path) {
		var self = this;

		group.path = current_path.concat(group.attributes.value);
		var result = [group];
		_.each(group.subgroups_data, function (subgroup) {
			result = result.concat(self.add_path(subgroup, group.path));
		});
		return result;
	},

	// To obtain all the values required to draw the full table, we have to do 
	// at least      2 + min(row.groupby.length, col.groupby.length)
	// calls to readgroup.  For example, if row.groupby = [r1, r2, r3] and 
	// col.groupby = [c1, c2, c3, c4], then a minimal set of calls is done 
	// with the following groupby:
	// [], [c1, c2, c3, c4], r1, c1, c2, c3, c4], [r1, r2, c1, c2, c3, c4],
	// [r1, r2, r3, c1, c2, c3, c4]
	// To simplify the code, we will always do 2 + row.groupby.length calls,
	// unless col.groupby.length = 0, in which case we do 2 calls ([] and 
	// row_groupbys), but this can be optimized later.
	load_data: function (options) {
		var self = this,
			cols = options.col_groupby,
			rows = options.row_groupby,
			measure = options.measure,
			domain = options.domain,
			visible_fields = rows.concat(cols),
			def_array,
			groupbys;

		if (measure) { visible_fields = visible_fields.concat(measure); }

		if (cols.length > 0) {
			groupbys = _.map(_.range(rows.length + 1), function (i) {
				return rows.slice(0, i).concat(cols);
			});
			groupbys.push([]);
		} else {
			groupbys = [rows, []];
		}
		def_array = _.map(groupbys, function (groupby) {
			return self.get_groups(visible_fields, domain, groupby);
		});

		return $.when.apply(null, def_array).then(function () {
			var args = Array.prototype.slice.call(arguments),
				col_data = _.first(args),
				total = _.last(args)[0],
				row_data = _.last(_.initial(args)),
				cell_data = args;

			return (total === undefined) ? undefined
                    : self.format_data(total, col_data, row_data, cell_data, options);
		});
	},


	format_data: function (total, col_data, row_data, cell_data, options) {
		var self = this,
			dim_row = options.row_groupby.length,
			dim_col = options.col_groupby.length,
			measure = options.measure,
			col_headers = make_headers(col_data, dim_col),
			row_headers = make_headers(row_data, dim_row),
			cells = [];

		if (dim_col > 0) {
			_.each(cell_data, function (data, index) {
				make_cells(data, index, []);
			}); // make it more functional?
		} else {
			make_cells(cell_data[0], dim_row, []);
			make_cells(cell_data[1], 0, []);
		}

		return {col_headers: col_headers,
                row_headers: row_headers,
                cells: cells};

		function make_headers (data, depth) {
			var main = {
				id: _.uniqueId(),
				path: [],
				parent: null,
				children: [],
				title: '',
				domain: options.domain,
			};
			if (measure) {
				main.total = total.attributes.aggregates[measure];
			} else {
				main.total = total.attributes.length;
			}

			if (depth > 0) {
				main.children = _.map(data, function (data_pt) {
					return make_tree_headers (data_pt, main, depth);
				});
			}

			var result = [],
				make_list = function (tree) {
					result.push(tree);
					_.each(tree.children, make_list);
				};

			make_list(main);
			return result;
		}

		function make_tree_headers (data_pt, parent, max_depth) {
			var value = data_pt.attributes.value,
				node = {
					id: _.uniqueId(),
					path: parent.path.concat(value),
					title: value,
					domain: data_pt.model._domain,
					parent: parent,
					children: [],
				};
			if (measure) {
				node.total = data_pt.attributes.aggregates[measure];
			} else {
				node.total = data_pt.attributes.length;
			}

			if (node.path.length < max_depth) {
				node.children = _.map(data_pt.subgroups_data, function (child) {
					return make_tree_headers (child, node, max_depth);
				});
			}
			return node;
		}

		function make_cells (data, index, current_path) {
			_.each(data, function (group) {
				var attr = group.attributes,
					group_val = (attr.value instanceof Array) ? attr.value[1] : attr.value,
					path = current_path,
					value = (measure) ? attr.aggregates[measure] : attr.length;

				group_val = (group_val === false) ? undefined : group_val;

				if (attr.grouped_on !== undefined) {
					path = path.concat((attr.value === false) ? 'undefined' : group_val);
				}

				var rowpath = path.slice(0, index),
					colpath = path.slice(index);

				var row = _.find(row_headers, function (header) {
					return _.isEqual(header.path, rowpath);
				});
				var col = _.find(col_headers, function (header) {
					return _.isEqual(header.path, colpath);
				});
				cells.push({x: Math.min(row.id, col.id),
							y: Math.max(row.id, col.id),
							value: value});

				if (attr.has_children) {
					make_cells (group.subgroups_data, index, path);
				}
			});
		}
	},

});

})();