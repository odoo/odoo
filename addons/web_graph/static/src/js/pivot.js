
/* jshint undef: false  */

(function () {
'use strict';

openerp.web_graph.PivotTable = openerp.web.Class.extend({
	init: function (model, domain) {
		this.rows = { groupby: [], main: null, headers: null };
		this.cols = { groupby: [], main: null, headers: null };
		this.cells = [];
		this.model = model;
		this.domain = domain;
		this.measure = null;

		this.id_seed = 0;
		this.no_data = true;
		this.stale_data = true;
	},

	visible_fields: function () {
		var result = this.rows.groupby.concat(this.cols.groupby);
		if (this.measure) {
			result = result.concat(this.measure);
		}
		return result;
	},

	set_domain: function (domain) {
		if (!_.isEqual(domain, this.domain)) {
			this.domain = domain;
			this.stale_data = true;
		}
	},

	set_measure: function (measure) {
		if (measure !== this.measure) {
			this.measure = measure;
			this.stale_data = true;
		}
	},

	set_row_groupby: function (groupby) {
        if ((!groupby.length) && (this.rows.main)) {
            this.fold(this.rows.main);
        }
		if (!_.isEqual(groupby, this.rows.groupby)) {
			this.rows.groupby = groupby;
			this.invalidate_data();
		}
	},

	set_col_groupby: function (groupby) {
        if ((!groupby.length) && (this.cols.main)) {
            this.fold(this.cols.main);
        }
		if (!_.isEqual(groupby, this.cols.groupby)) {
			this.cols.groupby = groupby;
            this.invalidate_data();
		}
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
        header.root.groupby.splice(new_groupby_length);
        header.children = [];
        this.cells = _.reject(this.cells, function (cell) {
            return (_.contains(ids_to_remove, cell.x) || _.contains(ids_to_remove, cell.y));
        });
	},

	expand: function (header_id, field_id) {
        var self = this,
            header = this.get_header(header_id);

        if (header.path.length == header.root.groupby.length) {
            header.root.groupby.push(field_id);
        }

        var otherDim = (header.root === this.cols) ? this.rows : this.cols;
        return query_groups_data(this.model, this.visible_fields(), header.domain, otherDim.groupby, field_id)
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
            });
	},

	make_header: function (groups, parent) {
		var name = get_attribute_value(groups[0]),
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
		insertAfter(parent.root.headers, parent, new_header);
		return new_header.id;
	},

	swap_axis: function () {
		var temp = this.rows;
		this.rows = this.cols;
		this.cols = temp;
	},

	fold_rows: function () {
		this.fold(this.rows.main);
	},

	fold_cols: function () {
		this.fold(this.cols.main);
	},

	expand_headers: function (root, new_headers) {
		root.headers = new_headers;
		root.main = new_headers[0];
		_.each(root.headers, function (header) {
			header.root = root;
			header.is_expanded = (header.children.length > 0);
		});
	},

	get_total: function (header) {
		if (header) {
			var main = (header.root === this.rows) ? this.cols.main : this.rows.main;
			return this.get_value(header.id, main.id);
		} else {
			return this.rows.main.total;
		}
	},

	invalidate_data: function () {
		this.cells = null;
		this.rows.main = null;
		this.cols.main = null;
		this.rows.headers = null;
		this.cols.headers = null;
		this.stale_data = true;
	},

	update_data: function () {
		var self = this;
		return this.query_all_values().then(function (result) {
			self.stale_data = false;
			if (result) {
				self.no_data = false;
				if (self.cols.headers) {
					self.update_headers(self.cols, result.col_headers);
					self.update_headers(self.rows, result.row_headers);					
				} else {
					self.expand_headers(self.cols, result.col_headers);
					self.expand_headers(self.rows, result.row_headers);					
				}
				self.cells = result.cells;
			} else {
				self.no_data = true;
			}
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

	// this method is a little tricky.  In order to obtain all the values 
	// required to draw the full table, we have to do at least 
	//             2 + min(row.groupby.length, col.groupby.length)
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

			return (total === undefined) ? undefined
                    : self.format_data(total, col_data, row_data, cell_data);
		});

	},

	format_data: function (total, col_data, row_data, cell_data) {
		var self = this,
			dim_row = this.rows.groupby.length,
			dim_col = this.cols.groupby.length,
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
				domain: self.domain,
			};
			if (self.measure) {
				main.total = total.attributes.aggregates[self.measure];
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
			var value = get_attribute_value(data_pt),
				node = {
					id: _.uniqueId(),
					path: parent.path.concat(value),
					title: value,
					domain: data_pt.model._domain,
					parent: parent,
					children: [],
				};
			if (self.measure) {
				node.total = data_pt.attributes.aggregates[self.measure];
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
					value;

				if (group_val === false) {
					group_val = undefined;
				}

				if (self.measure) {
					value = attr.aggregates[self.measure];
				} else {
					value = attr.length;
				}

				if (attr.grouped_on !== undefined) {
					if (attr.value === false) {
						path = path.concat('undefined');
					} else {
						path = path.concat(group_val);
					}
				}

				console.log('attr', attr);
				var rowpath = path.slice(0, index),
					colpath = path.slice(index);

				var row = _.find(row_headers, function (header) {
					return _.isEqual(header.path, rowpath);
				});
				var col = _.find(col_headers, function (header) {
					return _.isEqual(header.path, colpath);
				});
				debugger;
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

function insertAfter(array, after, elem) {
    array.splice(array.indexOf(after) + 1, 0, elem);
}

/**
 * Query the server and return a deferred which will return the data
 * with all the groupbys applied (this is done for now, but the goal
 * is to modify read_group in order to allow eager and lazy groupbys
 */
function query_groups (model, fields, domain, groupbys) {
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

function query_groups_data (model, fields, domain, row_groupbys, col_groupby) {
    return query_groups(model, fields, domain, [col_groupby].concat(row_groupbys)).then(function (groups) {
        return _.map(groups, function (group) {
            return format_group(group, []);
        });
    });
}

function format_group (group, path) {
    group.path = path.concat(get_attribute_value(group));
    var result = [group];
    _.each(group.subgroups_data, function (subgroup) {
        result = result.concat(format_group (subgroup, group.path));
    });
    return result;
}

function get_attribute_value (group) {
	var value = group.attributes.value;
	if (value === false) return 'undefined';
	return (value instanceof Array) ? value[1] : value;
}

})();