

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

		this.id_seed = -1;
	},

	// Load initial data into the rows, cols and cells array.
	// This function needs to be called after init and before
	// drawing the table (otherwise the data returned will be empty...)
	start: function () {
		var self = this;
		var main_row = {
			id: this.generate_id(),
			path: [],
			name: "Total",
			is_expanded: false,
			parent: null,
			children: [],
			domain: this.domain,
		};
		this.rows.push(main_row);

		var main_col = {
			id: this.generate_id(),
			path: [],
			name: this.measure_label,
			is_expanded: false,
			parent: null,
			children: [],
			domain: this.domain,
		};
		this.cols.push(main_col);

		// get total and create first cell
		var tot = query_groups (this.model, this.measure, this.domain, [])
			.then(function (total) {
				var val = total[0].attributes.aggregates[self.measure];
				self.set_value(main_row.id, main_col.id, val);
			});

		var grp = query_groups (this.model, this.visible_fields(), this.domain, this.row_groupby)
			.then(function (groups) {
				_.each(groups, function (group) {
					var new_row = {
						id: self.generate_id(),
						path: [group.attributes.value[1]],
						name: group.attributes.value[1],
						is_expanded: false,
						parent: main_row,
						children: [],
						domain: group.model._domain,
					}
					self.rows.push(new_row);
					main_row.children.push(new_row.id);
					self.set_value(new_row.id, main_col.id, 
								   group.attributes.aggregates[self.measure]);
				});
				main_row.is_expanded = true;
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
	}


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