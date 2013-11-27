
(function () {

openerp.web_graph.PivotTable = openerp.web.Class.extend({
	init: function (options) {
		this.rows = { groupby: options.row_groupby };
		this.cols = { groupby: [] };
		this.cells = [];
		this.model = options.model;
		this.domain = options.domain;
		this.measure = options.measure;
		this.measure_label = options.measure_label;
		this.total = 0;
		this.id_seed = 0;
	},

	start: function () {
		return this.expand_all();
	},

	generate_id: function () {
		this.id_seed += 1;
		return this.id_seed;
	},

	visible_fields: function () {
		return this.rows.groupby.concat(this.cols.groupby, this.measure);
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

	get_value: function (id1, id2) {
		var x = Math.min(id1, id2),
			y = Math.max(id1, id2),
			cell = _.find(this.cells, function (c) {
			return ((c.x == x) && (c.y == y));
		});
		return (cell === undefined) ? undefined : cell.value;
	},

	get_header: function (id) {
		return _.find(this.rows.headers.concat(this.cols.headers), function (header) {
			return header.id == id;
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
        header.root.groupby.splice(new_groupby_length);
        header.children = [];
        this.cells = _.reject(this.cells, function (cell) {
        	return (_.contains(ids_to_remove, cell.x) || _.contains(ids_to_remove, cell.y));
        });
	},

	expand: function (row_id, field_id) {
        var self = this,
            row = this.get_header(row_id);

        if (row.path.length == row.root.groupby.length) {
            row.root.groupby.push(field_id);
        }

        var otherDim = (row.root === this.cols) ? this.rows : this.cols; 
        return query_groups_data(this.model, this.visible_fields(), row.domain, otherDim.groupby, field_id)
            .then(function (groups) {
                _.each(groups.reverse(), function (group) {
                	var new_row_id = self.make_header(group, row);
                    _.each(group, function (data) {
                    	var col = _.find(otherDim.headers, function (c) {
                    		if (row.root === this.cols) {
                    			return _.isEqual(data.path.slice(1), c.path);
                    		} else {
                    			return _.isEqual(_.rest(data.path), c.path);
                    		}
                    	});
                    	if (col) {
                    		self.set_value(new_row_id, col.id, data.attributes.aggregates[self.measure]);
                    	}
                    });
                });
                row.is_expanded = true;
        });
	},

	make_header: function (groups, parent) {
		var name = groups[0].attributes.value[1],
		    new_header = {
				id: this.generate_id(),
				path: parent.path.concat(name),
				title: name,
				is_expanded: false,
				parent: parent.id,
				children: [],
				domain: groups[0].model._domain,
				root: parent.root,
			};
		parent.children.splice(0,0, new_header);
		insertAfter(parent.root.headers, parent, new_header);
		return new_header.id;
	},

	swap_axis: function () {
		var temp = this.rows;
		this.rows = this.cols;
		this.cols = temp;

		this.rows.main.title = "Total";
		this.cols.main.title = this.measure_label;
	},

	fold_rows: function () {
		this.fold(this.rows.main);
	},

	fold_cols: function () {
		this.fold(this.cols.main);
	},

	fold_all: function () {
		this.fold_rows();
		this.fold_cols();
	},

	expand_all: function () {
		var self = this;

		return this.query_all_values().then(function (result) {
			self.rows.headers = result.row_headers;
			self.cols.headers = result.col_headers;
			self.cells = result.cells;
			self.rows.main = self.rows.headers[0];
			self.cols.main = self.cols.headers[0];
			self.total = self.rows.main.total;
			self.rows.main.title = "Total";
			self.cols.main.title = self.measure_label;
			_.each(self.rows.headers, function (row) {
				row.root = self.rows;
				row.is_expanded = (row.children.length > 0);
			});
			_.each(self.cols.headers, function (col) {
				col.root = self.cols;
				col.is_expanded = (col.children.length > 0);
			});

		});
	},

	update_values: function () {
		var self = this;
		return this.query_all_values().then(function (result) {
			var old_col_headers = self.cols.headers,
				old_row_headers = self.rows.headers;

			// the next 30 lines replace this.cols.headers with the 
			// corresponding headers in result.col_headers
			_.each(old_col_headers, function (header) {
				var corresponding_col = _.find(result.col_headers, function (c) {
					return _.isEqual(c.path, header.path);
				});

				if (corresponding_col !== undefined) {
					if (header.is_expanded) {
						corresponding_col.is_expanded = true;
						_.each(corresponding_col.children, function (c) {
							c.is_expanded = false;
						});
					} else {
						corresponding_col.is_expanded = false;
					}
				}
			});

			self.cols.headers = _.filter(result.col_headers, function (header) {
				return (header.is_expanded !== undefined);
			});

			_.each(self.cols.headers, function (col) {
				if (!col.is_expanded) {
					col.children = [];
				}
			});
			self.cols.main = self.cols.headers[0];

			// the next 30 lines replace this.rows.headers with the 
			// corresponding headers in result.row_headers
			_.each(old_row_headers, function (header) {
				var corresponding_row = _.find(result.row_headers, function (c) {
					return _.isEqual(c.path, header.path);
				});

				if (corresponding_row !== undefined) {
					if (header.is_expanded) {
						corresponding_row.is_expanded = true;
						_.each(corresponding_row.children, function (c) {
							c.is_expanded = false;
						});
					} else {
						corresponding_row.is_expanded = false;
					}
				}
			});

			self.rows.headers = _.filter(result.row_headers, function (header) {
				return (header.is_expanded !== undefined);
			});

			_.each(self.rows.headers, function (col) {
				if (!col.is_expanded) {
					col.children = [];
				}
			});
			self.rows.main = self.rows.headers[0];

			// now some more tweaks
			self.total = self.rows.main.total;
			_.each(self.rows.headers, function (row) {
				row.root = self.rows;
			});
			_.each(self.cols.headers, function (col) {
				col.root = self.cols;
			});
			self.cells = result.cells;
			self.rows.main.title = "Total";
			self.cols.main.title = self.measure_label;
		});
	},

	// this method is a little tricky.  In order to obtain all the values 
	// required to draw the full table, we have to do at least 
	// 			2 + min(row.groupby.length, col.groupby.length)
	// calls to readgroup.  For example, if row.groupby = [r1, r2, r3] and 
	// col.groupby = [c1, c2, c3, c4], then a minimal set of calls is done 
	// with the following groupby:
	// []
	// [c1, c2, c3, c4]
	// [r1, c1, c2, c3, c4]
	// [r1, r2, c1, c2, c3, c4]
	// [r1, r2, r3, c1, c2, c3, c4]
	// To simplify the code, we will always do 2 + row.groupby.length calls,
	// unless col.groupby.length = 0, in which case we do 2 calls ([] and 
	// row_groupbys), but this can be optimized later.
	query_all_values: function () {
		var self = this,
			cols = this.cols.groupby,
			rows = this.rows.groupby,
			def_array,
			groupbys;

		if (cols.length > 0) {
			groupbys = _.map(_.range(rows.length + 1), function (i) {
				return rows.slice(0, i).concat(cols);
			});
			groupbys.push([]);
		} else {
			groupbys = [rows, []];
		}
		def_array = _.map(groupbys, function (groupby) {
			return query_groups(self.model, self.visible_fields(), self.domain, groupby);
		});

		return $.when.apply(null, def_array).then(function () {
			var args = Array.prototype.slice.call(arguments), 
				col_data = _.first(args),
				total = _.last(args)[0],
				row_data = _.last(_.initial(args)),
				cell_data = args;

			return self.format_data(total, col_data, row_data, cell_data);
		});

	},

	format_data: function (total, col_data, row_data, cell_data) {
		var self = this,
			dim_row = this.rows.groupby.length,
			dim_col = this.cols.groupby.length,
			col_headers = make_headers(col_data, dim_col),
			row_headers = make_headers(row_data, dim_row);
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
				id: self.generate_id(),
				count: total.attributes.length,
				total: total.attributes.aggregates[self.measure],
				path: [],
				parent: null,
				children: [],
				title: '',
				domain: self.domain,
			};

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
			var node = {
				id: self.generate_id(),
				count: data_pt.attributes.length,
				total: data_pt.attributes.aggregates[self.measure],
				path: parent.path.concat(data_pt.attributes.value[1]),
				title: data_pt.attributes.value[1],
				domain: data_pt.model._domain,
				parent: parent,
				children: [],
			};
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
					path = current_path,
					value = attr.aggregates[self.measure];

				if (attr.grouped_on !== undefined) {
					path = path.concat(attr.value[1]);
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


removeFromArray = function (array, element) {
    var index = array.indexOf(element);
    if (index > -1) {
        array.splice(index, 1);
    }
}

insertAfter = function (array, after, elem) {
    array.splice(array.indexOf(after) + 1, 0, elem);
}

/**
 * Query the server and return a deferred which will return the data
 * with all the groupbys applied (this is done for now, but the goal
 * is to modify read_group in order to allow eager and lazy groupbys
 */
query_groups = function (model, fields, domain, groupbys) {
    return model.query(fields)
        .filter(domain)
        .group_by(groupbys)
        .then(function (results) {
            var non_empty_results = _.filter(results, function (group) {
                return group.attributes.length > 0;
            });
            if (groupbys.length <= 1) {
                return non_empty_results;
            } else {
                var get_subgroups = $.when.apply(null, _.map(non_empty_results, function (result) {
                    var new_domain = result.model._domain;
                    var new_groupings = groupbys.slice(1);
                    return query_groups(model, fields,new_domain, new_groupings).then(function (subgroups) {
                        result.subgroups_data = subgroups;
                    });
                }));
                return get_subgroups.then(function () {
                    return non_empty_results;
                });
            }
        });
}

query_groups_data = function (model, fields, domain, row_groupbys, col_groupby) {
    return query_groups(model, fields, domain, [col_groupby].concat(row_groupbys)).then(function (groups) {
        return _.map(groups, function (group) {
            return format_group(group, []);
        });
    });
}

format_group = function (group, path) {
    group.path = path.concat(group.attributes.value[1]);
    result = [group];
    _.each(group.subgroups_data, function (subgroup) {
        result = result.concat(format_group (subgroup, group.path));
    });
    return result;
}

})();