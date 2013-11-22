

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
		};

		this.cols = {
			id: this.generate_id(),
			path: [],
			name: this.measure_label,
			is_expanded: false,
			parent: null,
			children: [],
			domain: this.domain,
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
					});
					self.set_value(new_id, self.cols.id, 
								   group.attributes.aggregates[self.measure]);
				});
				self.rows.is_expanded = true;
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

	iterate_rows: function (iterator) {
		this.iterate(this.rows, iterator);
	},

	iterate_cols: function (iterator) {
		this.iterate(this.cols, iterator);
	},

	get_max_path_length: function (header) {
        var height = 0;
        this.iterate_cols(function (col) {
            height = Math.max(height, col.path.length);
        });
        return height;
	},

	rows_array: function () {
		var result = [];
		this.iterate_rows(function (row) { result.push(row); });
		return result;
	},

	cols_array: function () {
		var result = [];
		this.iterate_cols(function (col) { result.push(col); });
		return result;
	},

	get_col: function (id) {
		return _.find(this.cols_array(), function (col) { return col.id == id;});
	},

	get_row: function (id) {
		return _.find(this.rows_array(), function (row) { return row.id == id;});
	},

	fold: function (header) {
		header.children = [];
		header.is_expanded = false;
        var fold_lvls = _.map(this.rows_array(), function(g) {return g.path.length;});
        var new_groupby_length = _.max(fold_lvls); 

        this.row_groupby.splice(new_groupby_length);

		// to do : remove every corresponding cells
	},

	fold_row: function (row) {
		this.fold(row);
	},

	fold_col: function (col) {
		this.fold(col);
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
                	var new_row_id = self.make_header(group, row);
                    var cols_array = self.cols_array();
                    _.each(group, function (data) {
                    	var col = _.find(cols_array, function (c) {
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

	expand_col: function (col_id, field_id) {
        var self = this,
        	col = this.get_col(col_id);

        if (col.path.length == this.col_groupby.length) {
            this.col_groupby.push(field_id);
        }

		console.log("cols",this.cols_array());
        console.log("dbg",this.col_groupby);
        return query_groups_data(this.model, this.visible_fields(), col.domain, this.row_groupby, field_id)
            .then(function (groups) {
            	console.log("groups",groups);
                _.each(groups, function (group) {
        //         	console.log("adding group",group);
                	var new_col_id = self.make_header(group, col);
        //          //    var rows_array = self.rows_array();
        //             // _.each(group, function (data) {
        //             // 	var row = _.find(rows_array, function (c) {
        //             // 		return _.isEqual(data.path.slice(1), c.path);
        //             // 	});
        //             // 	if (row) {
        //             // 		self.set_value(row.id, new_col_id, data.attributes.aggregates[self.measure]);
        //             // 	}
        //             // });
                });
        //         col.is_expanded = true;
        //         // console.log("col is now",col);
        //         // console.log("dbg",col.children.length);
        });

	},

	make_header: function (groups, parent) {

		var new_header = {
			id: this.generate_id(),
			path: parent.path.concat(groups[0].attributes.value[1]),
			name: groups[0].attributes.value[1],
			is_expanded: false,
			parent: parent.id,
			children: [],
			domain: groups[0].model._domain,
		};
		parent.children.push(new_header);
		return new_header.id;
	},

//     make_row: function (groups, parent_id) {
//         var self = this,
//             path,
//             value,
//             expanded,
//             domain,
//             parent,
//             has_parent = (parent_id !== undefined),
//             row_id = this.generate_id();

//         if (has_parent) {
//             parent = this.get_row(parent_id);
//             path = parent.path.concat(groups[0].attributes.value[1]);
//             value = groups[0].attributes.value[1];
//             expanded = false;
//             parent.children.push(row_id);
//             domain = groups[0].model._domain;
//         } else {
//             parent = null;
//             path = [];
//             value = 'Total';
//             expanded = true;
//             domain = this.data.domain;
//         }

//         var jquery_row = $('<tr></tr>');

//         var header = self.make_cell(value, {is_border:true, indent: path.length, foldable:true, row_id: row_id});
//         jquery_row.append(header);

//         var cell;

//         _.each(this.cols, function (col) {
//             var element = _.find(groups, function (group) {
//                 return _.isEqual(_.rest(group.path), col.path);
//             });
//             if (element === undefined) {
//                 cell = self.make_cell('');
//             } else {
//                 cell = self.make_cell(element.attributes.aggregates[self.data.measure]);                
//             }
//             if (col.expanded) {
//                 cell.css('display', 'none');
//             }
//             col.cells.push({td:cell, row_id:row_id});
//             jquery_row.append(cell);
//         });

//         if (!has_parent) {
//             header.find('.icon-plus-sign')
//                 .removeClass('icon-plus-sign')
//                 .addClass('icon-minus-sign');            
//         }

//         var row = {
//             id: row_id,
//             path: path,
//             value: value,
//             expanded: expanded,
//             parent: parent_id,
//             children: [],
//             html: jquery_row,
//             domain: domain,
//         };
//         this.rows.push(row);  // to do, insert it properly, after all childs of parent
//         return row;
//     },

//     expand_row: function (row_id, field_id) {
//         var self = this;
//         var row = this.get_row(row_id);

//         if (row.path.length == this.data.row_groupby.length) {
//             this.data.row_groupby.push(field_id);
//         }
//         row.expanded = true;
//         row.html.find('.icon-plus-sign')
//             .removeClass('icon-plus-sign')
//             .addClass('icon-minus-sign');

//         var visible_fields = this.data.row_groupby.concat(this.data.col_groupby, this.data.measure);
//         query_groups_data(this.data.model, visible_fields, row.domain, this.data.col_groupby, field_id)
//             .then(function (groups) {
//                 _.each(groups.reverse(), function (group) {
//                     var new_row = self.make_row(group, row_id);
//                     row.html.after(new_row.html);
//                 });
//         });

//     },

	// toArray: function (header) {
	// 	return [header].concat(_.map(header.children), this.toArray(hea))
	// }

});



	// function expand_row (row, field) {

	// }

	// function expand_col (col, field) {

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