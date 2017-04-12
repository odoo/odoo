odoo.define('web.PivotModel', function (require) {
"use strict";

/**
 * Pivot Model
 *
 * The pivot model keeps an in-memory representation of the pivot table that is
 * displayed on the screen.  The exact layout of this representation is not so
 * simple, because a pivot table is at its core a 2-dimensional object, but
 * with a 'tree' component: some rows/cols can be expanded so we zoom into the
 * structure.
 *
 * However, we need to be able to manipulate the data in a somewhat efficient
 * way, and to transform it into a list of lines to be displayed by the renderer
 *
 * @todo add a full description/specification of the data layout
 */

var core = require('web.core');
var utils = require('web.utils');
var AbstractModel = require('web.AbstractModel');

var _t = core._t;

var PivotModel = AbstractModel.extend({
    /**
     * @override
     * @param {Object} params
     */
    init: function () {
        this._super.apply(this, arguments);
        this.numbering = {};
        this.data = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Close a header. This method is actually synchronous, but returns a
     * deferred.
     *
     * @param {any} headerID
     * @returns {Deferred}
     */
    closeHeader: function (headerID) {
        var header = this.data.headers[headerID];
        header.expanded = false;
        header.children = [];
        var newGroupbyLength = this._getHeaderDepth(header.root) - 1;
        header.root.groupbys.splice(newGroupbyLength);
    },
    /**
     * @returns {Deferred}
     */
    expandAll: function () {
        return this._loadData();
    },
    /**
     * Expand (open up) a given header, be it a row or a column.
     *
     * @todo: add discussion on the number of read_group that it will generate,
     * which is (r+1) or (c+1) I think
     *
     * @param {any} header
     * @param {any} field
     * @returns
     */
    expandHeader: function (header, field) {
        var self = this;

        var other_root = header.root.other_root;
        var other_groupbys = header.root.other_root.groupbys;
        var fields = [].concat(field, other_groupbys, this.data.measures);
        var groupbys = [];

        for (var i = 0; i <= other_groupbys.length; i++) {
            groupbys.push([field].concat(other_groupbys.slice(0,i)));
        }

        return $.when.apply(null, groupbys.map(function (groupBy) {
            return self._rpc({
                    model: self.modelName,
                    method: 'read_group',
                    context: self.data.context,
                    domain: header.domain.length ? header.domain : self.data.domain,
                    fields: _.map(fields, function (field) { return field.split(':')[0]; }),
                    groupBy: groupBy,
                    lazy: false,
                });
        })).then(function () {
            var data = Array.prototype.slice.call(arguments);
            var datapt, attrs, j, l, row, col, cell_value, groupBys;
            for (i = 0; i < data.length; i++) {
                for (j = 0; j < data[i].length; j++){
                    datapt = data[i][j];
                    groupBys = [field].concat(other_groupbys.slice(0,i));
                    attrs = {
                        value: self._getValue(datapt, groupBys),
                        domain: datapt.__domain || [],
                        length: datapt.__count,
                    };

                    if (i === 0) {
                        row = self._makeHeader(attrs.value, attrs.domain, header.root, 0, 1, header);
                    } else {
                        row = self._getHeader(attrs.value, header.root, 0, 1, header);
                    }
                    col = self._getHeader(attrs.value, other_root, 1, i + 1);
                    if (!col) {
                        continue;
                    }
                    for (cell_value = {}, l=0; l < self.data.measures.length; l++) {
                        cell_value[self.data.measures[l]] = datapt[self.data.measures[l]];
                    }
                    // cell_value.__count = attrs.length;
                    if (!self.data.cells[row.id]) {
                        self.data.cells[row.id] = [];
                    }
                    self.data.cells[row.id][col.id] = cell_value;
                }
            }
            if (!_.contains(header.root.groupbys, field)) {
                header.root.groupbys.push(field);
            }
        });
    },
    /**
     * @returns {Object}
     */
    exportData: function () {
        var record = this.data;
        var measureNbr = record.measures.length;
        var headers = this.renderer._computeHeaders();
        var measureRow = measureNbr > 1 ? _.last(headers) : [];
        var rows = this.renderer._computeRows();
        var i, j, value;
        headers[0].splice(0,1);

        // process measureRow
        for (i = 0; i < measureRow.length; i++) {
            measureRow[i].measure = this.measures[measureRow[i].measure].string;
        }
        // process all rows
        for (i =0, j, value; i < rows.length; i++) {
            for (j = 0; j < rows[i].values.length; j++) {
                value = rows[i].values[j];
                rows[i].values[j] = {
                    is_bold: (i === 0) ||
                        ((record.data.main_col.width > 1) &&
                         (j >= rows[i].values.length - measureNbr)),
                    value:  (value === undefined) ? "" : value,
                };
            }
        }
        return {
            headers: _.initial(headers),
            measure_row: measureRow,
            rows: rows,
            nbr_measures: measureNbr,
            title: this.title,
        };
    },
    /**
     * Swap the columns and the rows.  It is a synchronous operation.
     */
    flip: function () {
        // swap the data: the main column and the main row
        var temp = this.data.main_col;
        this.data.main_col = this.data.main_row;
        this.data.main_row = temp;

        // we need to update the record metadata: row and col groupBys
        temp = this.data.groupedBy;
        this.data.groupedBy = this.data.colGroupBys;
        this.data.colGroupBys = temp;
    },
    /**
     * @override
     * @param {Object} [options]
     * @param {boolean} [options.raw=false]
     * @returns {Object}
     */
    get: function (options) {
        var isRaw = options && options.raw;
        if (!this.data.has_data) {
            return {has_data: false};
        }
        return {
            colGroupBys: this.data.main_col.groupbys,
            fields: this.fields,
            headers: !isRaw && this._computeHeaders(),
            has_data: true,
            mainColWidth: this.data.main_col.width,
            measures: this.data.measures,
            rows: !isRaw && this._computeRows(),
            rowGroupBys: this.data.main_row.groupbys,
            sortedColumn: this.data.sorted_column,
        };
    },
    /**
     * @param {string} id
     * @returns {object}
     */
    getHeader: function (id) {
        return this.data.headers[id];
    },
    /**
     * @override
     * @param {Object} params
     * @param {string[]} [params.groupedBy]
     * @param {string[]} [params.colGroupBys]
     * @param {string[]} params.domain
     * @param {string[]} params.rowGroupBys
     * @param {string[]} params.colGroupBys
     * @param {string[]} params.measures
     * @param {Object} params.fields
     * @returns {Deferred}
     */
    load: function (params) {
        this.initialDomain = params.domain;
        this.initialRowGroupBys = params.rowGroupBys;
        this.initialColGroupBys = params.colGroupBys;
        this.initialMeasures = params.measures;
        this.fields = params.fields;
        this.modelName = params.modelName;
        var groupedBy = params.groupedBy.length ? params.groupedBy : this.initialRowGroupBys;
        this.data = {
            domain: params.domain,
            context: params.context,
            groupedBy: groupedBy,
            colGroupBys: params.colGroupBys || this.initialColGroupBys,
            measures: this.initialMeasures,
            sorted_column: {},
        };
        return this._loadData();
    },
    /**
     * @override
     * @param {any} handle this parameter is ignored
     * @param {Object} params
     * @returns {Deferred}
     */
    reload: function (handle, params) {
        var self = this;
        if ('domain' in params) {
            this.data.domain = params.domain;
        } else {
            this.data.domain = this.initialDomain;
        }
        if ('groupBy' in params) {
            this.data.groupedBy = params.groupBy;
        }
        if (!this.data.has_data) {
            return this._loadData();
        }

        var old_row_root = this.data.main_row.root;
        var old_col_root = this.data.main_col.root;
        return this._loadData().then(function () {
            var new_groupby_length;
            if (!('groupBy' in params)) {
                // we only update the row groupbys according to the old groupbys
                // if we don't have the key 'groupBy' in params.  In that case,
                // we want to have the full open state for the groupbys.
                self._updateTree(old_row_root, self.data.main_row.root);
                new_groupby_length = self._getHeaderDepth(self.data.main_row.root) - 1;
                self.data.main_row.groupbys = old_row_root.groupbys.slice(0, new_groupby_length);
            }

            self._updateTree(old_col_root, self.data.main_col.root);
            new_groupby_length = self._getHeaderDepth(self.data.main_col.root) - 1;
            self.data.main_row.groupbys = old_col_root.groupbys.slice(0, new_groupby_length);
        });
    },
    /**
     * Sort the rows, depending on the values of a given column.  This is an
     * in-memory sort.
     *
     * @param {any} col_id
     * @param {any} measure
     * @param {any} descending
     */
    sortRows: function (col_id, measure, descending) {
        var cells = this.data.cells;
        this._traverseTree(this.data.main_row.root, function (header) {
            header.children.sort(compare);
        });
        this.data.sorted_column = {
            id: col_id,
            measure: measure,
            order: descending ? 'desc' : 'asc',
        };
        function _getValue (id1, id2) {
            if ((id1 in cells) && (id2 in cells[id1])) {
                return cells[id1][id2];
            }
            if (id2 in cells) return cells[id2][id1];
        }

        function compare (row1, row2) {
            var values1 = _getValue(row1.id, col_id),
                values2 = _getValue(row2.id, col_id),
                value1 = values1 ? values1[measure] : 0,
                value2 = values2 ? values2[measure] : 0;
            return descending ? value1 - value2 : value2 - value1;
        }
    },
    /**
     * Toggle the active state for a given measure, then reload the data.
     *
     * @param {string} field
     * @returns {Deferred}
     */
    toggleMeasure: function (field) {
        if (_.contains(this.data.measures, field)) {
            this.data.measures = _.without(this.data.measures, field);
            // in this case, we already have all data in memory, no need to
            // actually reload a lesser amount of information
            return $.when();
        } else {
            this.data.measures.push(field);
        }
        return this._loadData();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _computeHeaders: function () {
        var self = this;
        var main_col_dims = this._getHeaderDim(this.data.main_col.root);
        var depth = main_col_dims.depth;
        var width = main_col_dims.width;
        var nbr_measures = this.data.measures.length;
        var result = [[{width:1, height: depth + 1}]];
        var col_ids = [];
        this.data.main_col.width = width;
        this._traverseTree(this.data.main_col.root, function (header) {
            var index = header.path.length - 1;
            var cell = {
                    width: self._getHeaderWidth(header) * nbr_measures,
                    height: header.expanded ? 1 : depth - index,
                    title: header.path[header.path.length-1],
                    id: header.id,
                    expanded: header.expanded,
                };
            if (!header.expanded) col_ids.push(header.id);
            if (result[index]) result[index].push(cell);
            else result[index] = [cell];
        });
        col_ids.push(this.data.main_col.root.id);
        this.data.main_col.width = width;
        if (width > 1) {
            var total_cell = {width:nbr_measures, height: depth, title:""};
            if (nbr_measures === 1) {
                total_cell.total = true;
            }
            result[0].push(total_cell);
        }
        var nbr_cols = width === 1 ? nbr_measures : (width + 1)*nbr_measures;
        for (var i = 0, measure_row = [], measure; i < nbr_cols; i++) {
            measure = this.data.measures[i % nbr_measures];
            measure_row.push({
                measure: measure,
                is_bold: (width > 1) && (i >= nbr_measures*width),
                id: col_ids[Math.floor(i / nbr_measures)],
            });
        }
        result.push(measure_row);
        return result;
    },
    _computeRows: function () {
        var self = this;
        var aggregates, i;
        var result = [];
        this._traverseTree(this.data.main_row.root, function (header) {
            var values = [],
                col_ids = [];
            result.push({
                id: header.id,
                col_ids: col_ids,
                indent: header.path.length - 1,
                title: header.path[header.path.length-1],
                expanded: header.expanded,
                values: values,
            });
            self._traverseTree(self.data.main_col.root, add_cells, header.id, values, col_ids);
            if (self.data.main_col.width > 1) {
                aggregates = self._getCellValue(header.id, self.data.main_col.root.id);
                for (i = 0; i < self.data.measures.length; i++) {
                    values.push(aggregates && aggregates[self.data.measures[i]]);
                }
                col_ids.push( self.data.main_col.root.id);
            }
        });
        return result;
        function add_cells (col_hdr, row_id, values, col_ids) {
            if (col_hdr.expanded) return;
            col_ids.push(col_hdr.id);
            aggregates = self._getCellValue(row_id, col_hdr.id);
            for (i = 0; i < self.data.measures.length; i++) {
                values.push(aggregates && aggregates[self.data.measures[i]]);
            }
        }
    },
    /**
     * Static helper method
     *
     * @private @static
     * @param {any} root
     * @param {any} path
     * @returns
     */
    _findPathInTree: function (root, path) {
        var i,
            l = root.path.length;
        if (l === path.length) {
            return (root.path[l-1] === path[l - 1]) ? root : null;
        }
        for (i = 0; i < root.children.length; i++) {
            if (root.children[i].path[l] === path[l]) {
                return this._findPathInTree(root.children[i], path);
            }
        }
        return null;
    },
    _getCellValue: function (id1, id2) {
        if ((id1 in this.data.cells) && (id2 in this.data.cells[id1])) {
            return this.data.cells[id1][id2];
        }
        if (id2 in this.data.cells) return this.data.cells[id2][id1];
    },
    /**
     * @param {any} value
     * @param {any} root
     * @param {any} i
     * @param {any} j
     * @param {any} parent
     * @returns {Object}
     */
    _getHeader: function (value, root, i, j, parent) {
        var path;
        var total = _t("Total");
        if (parent) {
            path = parent.path.concat(value.slice(i,j));
        } else {
            path = [total].concat(value.slice(i,j));
        }
        return this._findPathInTree(root, path);
    },
    /**
     * @private @static
     * @param {any} header
     * @returns {integer}
     */
    _getHeaderDepth: function (header) {
        var depth = 1;
        this._traverseTree(header, function (hdr) {
            depth = Math.max(depth, hdr.path.length);
        });
        return depth;
    },
    _getHeaderDim: function (header) {
        var depth = 1;
        var width = 0;
        this._traverseTree(header, function (hdr) {
            depth = Math.max(depth, hdr.path.length);
            if (!hdr.expanded) width++;
        });
        return {width: width, depth: depth};
    },
    _getHeaderWidth: function (header) {
        var self = this;
        if (!header.children.length) return 1;
        if (!header.expanded) return 1;
        return header.children.reduce(function (s, c) {
            return s + self._getHeaderWidth(c);
        }, 0);
    },
    /**
     * @param {any} value
     * @param {any} field
     * @returns {string}
     */
    _getNumberedValue: function (value, field) {
        var id= value[0];
        var name= value[1];
        this.numbering[field] = this.numbering[field] || {};
        this.numbering[field][name] = this.numbering[field][name] || {};
        var numbers = this.numbering[field][name];
        numbers[id] = numbers[id] || _.size(numbers) + 1;
        return name + (numbers[id] > 1 ? "  (" + numbers[id] + ")" : "");
    },
    /**
     * @param {any} datapt
     * @param {any} fields
     * @returns {string[]}
     */
    _getValue: function (datapt, fields) {
        var result = [];
        var value;
        for (var i = 0; i < fields.length; i++) {
            value = this._sanitizeValue(datapt[fields[i]],fields[i]);
            result.push(value);
        }
        return result;
    },
    /**
     * @returns {Deferred}
     */
    _loadData: function () {
        var self = this;
        var groupBys = [];
        var rowGroupBys = this.data.groupedBy;
        var colGroupBys = this.data.colGroupBys;
        var fields = [].concat(rowGroupBys, colGroupBys, this.data.measures);

        for (var i = 0; i < rowGroupBys.length + 1; i++) {
            for (var j = 0; j < colGroupBys.length + 1; j++) {
                groupBys.push(rowGroupBys.slice(0,i).concat(colGroupBys.slice(0,j)));
            }
        }

        return $.when.apply(null, groupBys.map(function (groupBy) {
            return self._rpc({
                    model: self.modelName,
                    method: 'read_group',
                    context: self.data.context,
                    domain: self.data.domain,
                    fields: _.map(fields, function (field) { return field.split(':')[0]; }),
                    groupBy: groupBy,
                    lazy: false,
                });
        })).then(function () {
            var data = Array.prototype.slice.call(arguments);
            if (data[0][0].__count === 0) {
                self.data.has_data = false;
                return;
            }
            self._prepareData(data);
        });
    },
    /**
     * @param {any} value
     * @param {any} domain
     * @param {any} root
     * @param {any} i
     * @param {any} j
     * @param {any} parent_header
     * @returns {Object}
     */
    _makeHeader: function (value, domain, root, i, j, parent_header) {
        var total = _t("Total");
        var title = value.length ? value[value.length - 1] : total;
        var path, parent;
        if (parent_header) {
            path = parent_header.path.concat(title);
            parent = parent_header;
        } else {
            path = [total].concat(value.slice(i,j-1));
            parent = value.length ? this._findPathInTree(root, path) : null;
        }
        var header = {
            id: utils.generateID(),
            expanded: false,
            domain: domain || [],
            children: [],
            path: value.length ? parent.path.concat(title) : [title]
        };
        this.data.headers[header.id] = header;
        header.root = root || header;
        if (parent) {
            parent.children.push(header);
            parent.expanded = true;
        }
        return header;
    },
    /**
     * @param {Object} data
     */
    _prepareData: function (data) {
        var self = this;
        _.extend(self.data, {
            main_row: {},
            main_col: {},
            headers: {},
            cells: [],
        });

        var index = 0;
        var rowGroupBys = this.data.groupedBy;
        var colGroupBys = this.data.colGroupBys;
        var datapt, row, col, attrs, cell_value;
        var main_row_header, main_col_header;
        var groupBys;
        var m;


        for (var i = 0; i < rowGroupBys.length + 1; i++) {
            for (var j = 0; j < colGroupBys.length + 1; j++) {
                for (var k = 0; k < data[index].length; k++) {
                    datapt = data[index][k];
                    groupBys = rowGroupBys.slice(0,i).concat(colGroupBys.slice(0,j));
                    attrs = {
                        value: self._getValue(datapt, groupBys),
                        domain: datapt.__domain || [],
                        length: datapt.__count,
                    };

                    if (j === 0) {
                        row = this._makeHeader(attrs.value, attrs.domain, main_row_header, 0, i);
                    } else {
                        row = this._getHeader(attrs.value, main_row_header, 0, i);
                    }
                    if (i === 0) {
                        col = this._makeHeader(attrs.value, attrs.domain, main_col_header, i, i+j);
                    } else {
                        col = this._getHeader(attrs.value, main_col_header, i, i+j);
                    }
                    if (i + j === 0) {
                        this.data.has_data = attrs.length > 0;
                        main_row_header = row;
                        main_col_header = col;
                    }
                    if (!this.data.cells[row.id]) this.data.cells[row.id] = [];
                    for (cell_value = {}, m=0; m < this.data.measures.length; m++) {
                        cell_value[this.data.measures[m]] = datapt[this.data.measures[m]];
                    }
                    this.data.cells[row.id][col.id] = cell_value;
                }
                index++;
            }
        }

        this.data.main_row.groupbys = rowGroupBys;
        this.data.main_col.groupbys = colGroupBys;

        main_row_header.other_root = main_col_header;
        main_col_header.other_root = main_row_header;

        main_row_header.groupbys = rowGroupBys;
        main_col_header.groupbys = colGroupBys;

        this.data.main_row.root = main_row_header;
        this.data.main_col.root = main_col_header;
    },
    /**
     * Format a value to a usable string, for the renderer to display.
     *
     * @param {any} value
     * @param {any} field
     * @returns {string}
     */
    _sanitizeValue: function (value, field) {
        if (value === false) {
            return _t("Undefined");
        }
        if (value instanceof Array) {
            return this._getNumberedValue(value, field);
        }
        if (field && this.fields[field] && (this.fields[field].type === 'selection')) {
            var selected = _.where(this.fields[field].selection, {0: value})[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
    /**
     * @private @static
     * @param {any} root
     * @param {any} f
     * @param {any} arg1
     * @param {any} arg2
     * @param {any} arg3
     * @returns
     */
    _traverseTree: function (root, f, arg1, arg2, arg3) {
        f(root, arg1, arg2, arg3);
        if (!root.expanded) return;
        for (var i = 0; i < root.children.length; i++) {
            this._traverseTree(root.children[i], f, arg1, arg2, arg3);
        }
    },
    /**
     * @param {Object} old_tree
     * @param {Object} new_tree
     */
    _updateTree: function (old_tree, new_tree) {
        if (!old_tree.expanded) {
            new_tree.expanded = false;
            new_tree.children = [];
            return;
        }
        var tree, j, old_title, new_title;
        for (var i = 0; i < new_tree.children.length; i++) {
            tree = undefined;
            new_title = new_tree.children[i].path[new_tree.children[i].path.length - 1];
            for (j = 0; j < old_tree.children.length; j++) {
                old_title = old_tree.children[j].path[old_tree.children[j].path.length - 1];
                if (old_title === new_title) {
                    tree = old_tree.children[j];
                    break;
                }
            }
            if (tree) {
                this._updateTree(tree, new_tree.children[i]);
            } else {
                new_tree.children[i].expanded = false;
                new_tree.children[i].children = [];
            }
        }
    },
});

return PivotModel;

});
