

var PivotTable = openerp.web.Class.extend({
	init: function (options) {
		this.rows = {};
		this.cols = {};
		this.cells = [];
		this.row_groupby = options.row_groupby;
		this.col_groupby = [];
		this.model = options.model;
		this.measure = options.measure;
		this.measure_label = options.measure_label;
		this.domain = options.domain;

		this.id_seed = -1;
	},

	// Load initial data into the rows, cols and cells array.
	// This function needs to be called after init and before
	// drawing the table (otherwise the data returned will be empty...)
	start: function () {
		var self = this;
		this.rows = {
			id: this.generate_id(),
			path: [],
			name: "Total",
			is_expanded: false,
			parent: null,
			children: [],
			domain: this.domain,
			height: 1,
			width: 1,
		};

		this.cols = {
			id: this.generate_id(),
			path: [],
			name: this.measure_label,
			is_expanded: false,
			parent: null,
			children: [],
			domain: this.domain,
			height: 1,
			width: 1,
		};

		// get total and create first cell
		var tot = query_groups (this.model, this.measure, this.domain, [])
			.then(function (total) {
				var val = total[0].attributes.aggregates[self.measure];
				self.set_value(self.rows.id, self.cols.id, val);
			});

		var grp = query_groups (this.model, this.visible_fields(), this.domain, this.row_groupby)
			.then(function (groups) {
				_.each(groups, function (group) {
					var new_id = self.generate_id();
					self.rows.children.push({
						id: new_id,
						path: [group.attributes.value[1]],
						name: group.attributes.value[1],
						is_expanded: false,
						parent: self.rows,
						children: [],
						domain: group.model._domain,
						height: 1,
						width: 1,
					});
					self.set_value(new_id, self.cols.id, 
								   group.attributes.aggregates[self.measure]);
				});
				self.rows.is_expanded = true;
				self.rows.width = groups.length;
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

	iterate: function (header, iterator) {
		var self = this;
		iterator(header);
		_.each(header.children, function (child) {
			self.iterate(child, iterator);
		});
	},

	get_max_path_length: function (header) {
        var height = 0;
        this.iterate(this.cols, function (col) {
            height = Math.max(height, col.path.length);
        });
        return height;
	},

        // function set_dim (cols) {
        //     _.each(cols.children, set_dim);
        //     if (cols.children.length === 0) {
        //         cols.height = height - cols.path.length + 1;
        //         cols.width = 1;
        //     } else {
        //         cols.height = 1;
        //         cols.width = _.reduce(cols.children, function (sum,c) { return sum + c.width;}, 0);
        //     }
        // }


	// toArray: function (header) {
	// 	return [header].concat(_.map(header.children), this.toArray(hea))
	// }

});



	// function expand_row (row, field) {

	// }

	// function expand_col (col, field) {

	// }

	// function fold_row (row) {

	// }

	// function fold_col (col) {

	// }


// 	function update_values () {
// 		// update all cells (reload data from db)
// 		// return a deferred
// 	}

// 	var id_seed = -1;

// 	return init();
// }