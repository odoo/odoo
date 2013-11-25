
var PivotTable = openerp.web.Class.extend({
	id_seed: 0,

	init: function (options) {
		main_row = {
			id: this.generate_id(),
			path: [],
			name: "Total",
			is_expanded: false,
			parent: null,
			children: [],
			domain: options.domain,
		}; 
		main_col = {
			id: this.generate_id(),
			path: [],
			name: options.measure_label,
			is_expanded: false,
			parent: null,
			children: [],
			domain: options.domain,				
		};

		this.rows = {
			groupby: options.row_groupby,
			main: main_row,
			headers: [main_row],
		};
		this.cols = {
			groupby: [],
			main: main_col,
			headers: [main_col],
		};

		main_row.root = this.rows;
		main_col.root = this.cols;
		this.cells = [];
		this.model = options.model;
		this.domain = options.domain;
		this.measure = options.measure;
		this.measure_label = options.measure_label;
		this.total = 0;
	},

	// Load initial data into the rows, cols and cells array.
	// This function needs to be called after init and before
	// drawing the table (otherwise the data returned will be empty...)
	start: function () {
		var self = this,
			initial_group = this.expand(this.rows.main.id, this.rows.groupby[0]),
			total = query_groups(this.model, this.measure, this.domain, [])
				.then(function (total) {
					var val = total[0].attributes.aggregates[self.measure];
					self.set_value(self.rows.main.id, self.cols.main.id, val);
					self.total = val;
				});

		return $.when(total, initial_group);
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
		var name = (groups[0].attributes.value) ? groups[0].attributes.value[1] : 'Undefined',
		    new_header = {
			id: this.generate_id(),
			path: parent.path.concat(name),
			name: name,
			is_expanded: false,
			parent: parent.id,
			children: [],
			domain: groups[0].model._domain,
			root: parent.root,
		};
		parent.children.splice(0,0, new_header)
		insertAfter(parent.root.headers, parent, new_header);
		return new_header.id;
	},

	swap_axis: function () {
		var temp = this.rows;
		this.rows = this.cols;
		this.cols = temp;

		this.rows.main.name = "Total";
		this.cols.main.name = this.measure_label;
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
		// temporary code, to use while waiting for correct code.
		// this code expands all rows/cols by doing as many db queries.
		// correct code widd do that with just 1 request.
		var header_to_expand = _.find(this.rows.headers.concat(this.cols.headers), function (header) {
			return ((!header.is_expanded) && (header.path.length < header.root.groupby.length))
		});
		if (header_to_expand === undefined) {
			return $.when();
		} else {
			return this.expand(header_to_expand.id, header_to_expand.root.groupby[header_to_expand.path.length]).then(function () {
				return self.expand_all();
			});
		}
	},

});


function removeFromArray(array, element) {
    var index = array.indexOf(element);
    if (index > -1) {
        array.splice(index, 1);
    }
}

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

function query_groups_data(model, fields, domain, row_groupbys, col_groupby) {
    return query_groups(model, fields, domain, [col_groupby].concat(row_groupbys)).then(function (groups) {
        return _.map(groups, function (group) {
            return format_group(group, []);
        });
    });
}

function format_group (group, path) {
    group.path = path.concat(group.attributes.value[1]);
    result = [group];
    _.each(group.subgroups_data, function (subgroup) {
        result = result.concat(format_group (subgroup, group.path));
    });
    return result;
}

