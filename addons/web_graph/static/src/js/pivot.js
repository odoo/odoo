

var PivotTable = openerp.web.Class.extend({
	init: function (options) {
		this.rows = [];
		this.cols = [];
		this.cells = [];
		this.row_groupby = options.row_groupby;
		this.col_groupby = [];
		this.model = options.model;
		this.measure = options.measure;
		this.measure_label = options.measure_label;
		this.domain = options.domain;
		this.id_seed = 0;
	},

	// Load initial data into the rows, cols and cells array.
	// This function needs to be called after init and before
	// drawing the table (otherwise the data returned will be empty...)
	start: function () {
		var self = this;
		this.rows.push({
			id: this.generate_id(),
			path: [],
			name: "Total",
			is_expanded: false,
			parent: null,
			children: [],
			domain: this.domain,
		});

		this.cols.push({
			id: this.generate_id(),
			path: [],
			name: this.measure_label,
			is_expanded: false,
			parent: null,
			children: [],
			domain: this.domain,
		});

		// get total and create first cell
		var tot = query_groups (this.model, this.measure, this.domain, [])
			.then(function (total) {
				var val = total[0].attributes.aggregates[self.measure];
				self.set_value(self.rows[0].id, self.cols[0].id, val);
			});

		var grp = query_groups (this.model, this.visible_fields(), this.domain, this.row_groupby)
			.then(function (groups) {
				_.each(groups, function (group) {
					var new_id = self.generate_id(),
						new_row = {
						id: new_id,
						path: [group.attributes.value[1]],
						name: group.attributes.value[1],
						is_expanded: false,
						parent: self.rows[0],
						children: [],
						domain: group.model._domain,
					};

					self.rows[0].children.push(new_row);
					self.rows.push(new_row);
					self.set_value(new_id, self.cols[0].id, 
								   group.attributes.aggregates[self.measure]);
				});
				self.rows[0].is_expanded = true;
			});

		return $.when(tot, grp);
	},

	generate_id: function () {
		this.id_seed += 1;
		return this.id_seed;
	},

	visible_fields: function () {
		return this.row_groupby.concat(this.col_groupby, this.measure);
	},

	set_value: function (row, col, value) {
		var cell = _.find(this.cells, function (c) {
			return ((c.row_id == row) && (c.col_id == col));
		});
		if (cell) {
			cell.value = value;
		} else {
			this.cells.push({row_id: row, col_id: col, value: value});
		}
	},

	get_value: function (row, col) {
		var cell = _.find(this.cells, function (c) {
			return ((c.row_id == row) && (c.col_id == col));
		});
		return (cell) ? cell.value : '';
	},

	get_col: function (id) {
		return _.find(this.cols, function (col) { return col.id == id;});
	},

	get_row: function (id) {
		return _.find(this.rows, function (row) { return row.id == id;});
	},

	fold_row: function (row) {
		var list = [];
		function tree_traversal(tree) {
			list.push(tree);
			_.each(tree.children, tree_traversal);
		}
		tree_traversal(row);
		this.rows = _.difference(this.rows, _.rest(list));
		row.is_expanded = false;
        var fold_lvls = _.map(this.rows, function(g) {return g.path.length;});
        var new_groupby_length = _.max(fold_lvls); 
        this.row_groupby.splice(new_groupby_length);
        row.children = [];
	},

	fold_col: function (col) {
		var list = [];
		function tree_traversal(tree) {
			list.push(tree);
			_.each(tree.children, tree_traversal);
		}
		tree_traversal(col);
		this.cols = _.difference(this.cols, _.rest(list));
		col.is_expanded = false;
        var fold_lvls = _.map(this.cols, function(g) {return g.path.length;});
        var new_groupby_length = _.max(fold_lvls); 
        this.col_groupby.splice(new_groupby_length);
        col.children = [];
	},

	expand_row: function (row_id, field_id) {
        var self = this,
        	row = this.get_row(row_id);

        if (row.path.length == this.row_groupby.length) {
            this.row_groupby.push(field_id);
        }
        return query_groups_data(this.model, this.visible_fields(), row.domain, this.col_groupby, field_id)
            .then(function (groups) {
                _.each(groups, function (group) {
                	var new_row_id = self.make_row(group, row);
                    _.each(group, function (data) {
                    	var col = _.find(self.cols, function (c) {
                    		return _.isEqual(_.rest(data.path), c.path);
                    	});
                    	if (col) {
                    		self.set_value(new_row_id, col.id, data.attributes.aggregates[self.measure]);
                    	}
                    });
                });
                row.is_expanded = true;
        });
	},

	make_row: function (groups, parent) {
		var new_row = {
			id: this.generate_id(),
			path: parent.path.concat(groups[0].attributes.value[1]),
			name: groups[0].attributes.value[1],
			is_expanded: false,
			parent: parent.id,
			children: [],
			domain: groups[0].model._domain,
		};
		parent.children.push(new_row);
		insertAfter(this.rows, parent, new_row);
		return new_row.id;
	},

	expand_col: function (col_id, field_id) {
        var self = this,
        	col = this.get_col(col_id);

        if (col.path.length == this.col_groupby.length) {
            this.col_groupby.push(field_id);
        }

        return query_groups_data(this.model, this.visible_fields(), col.domain, this.row_groupby, field_id)
            .then(function (groups) {
                _.each(groups, function (group) {
                	var new_col_id = self.make_col(group, col);
                    _.each(group, function (data) {
                    	var row = _.find(self.rows, function (c) {
                    		return _.isEqual(data.path.slice(1), c.path);
                    	});
                    	if (row) {
                    		self.set_value(row.id, new_col_id, data.attributes.aggregates[self.measure]);
                    	}
                    });
                });
                col.is_expanded = true;
        });

	},

	make_col: function (groups, parent) {
		var new_col = {
			id: this.generate_id(),
			path: parent.path.concat(groups[0].attributes.value[1]),
			name: groups[0].attributes.value[1],
			is_expanded: false,
			parent: parent.id,
			children: [],
			domain: groups[0].model._domain,
		};
		parent.children.push(new_col);
		insertAfter(this.cols, parent, new_col);
		return new_col.id;
	},


});

