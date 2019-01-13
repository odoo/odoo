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

var AbstractModel = require('web.AbstractModel');
var concurrency = require('web.concurrency');
var dataComparisonUtils = require('web.dataComparisonUtils');
var core = require('web.core');
var session = require('web.session');
var utils = require('web.utils');

var computeVariation = dataComparisonUtils.computeVariation;

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
        this._loadDataDropPrevious = new concurrency.DropPrevious();
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
        var measures = _.map(this.data.measures, function(measure) {
            var type = self.fields[measure].type;
            return (type === 'many2one') ? measure + ":count_distinct" : measure;
        });
        var groupBys = [];
        for (var i = 0; i <= other_groupbys.length; i++) {
            groupBys.push([field].concat(other_groupbys.slice(0,i)));
        }
        var defs = [];
        if ((typeof header.count === 'object' && header.count.data) || (typeof header.count === 'number' && header.count)) {
            defs = defs.concat(groupBys.map(function (groupBy) {
                return self._rpc({
                        model: self.modelName,
                        method: 'read_group',
                        context: self.data.context,
                        domain: header.domain ||
                                    self.data.domain.concat(self.data.timeRange),
                        fields: measures,
                        groupBy: groupBy,
                        lazy: false,
                    }).then(function (result) {
                        return ['data', result];
                    });
            }));
        }
        if (header.comparisonCount && this.data.compare) {
            defs = defs.concat(groupBys.map(function (groupBy) {
                return self._rpc({
                        model: self.modelName,
                        method: 'read_group',
                        context: self.data.context,
                        domain: header.comparisonDomain ||
                                    self.data.domain.concat(self.data.comparisonTimeRange),
                        fields: measures,
                        groupBy: groupBy,
                        lazy: false,
                    }).then(function (result) {
                        return ['comparisonData', result];
                    });
            }));
        }
        return $.when.apply(null, defs).then(function () {
            var results = Array.prototype.slice.call(arguments);
            var data = [];
            var comparisonData = [];
            _.each(results, function (result) {
                if (result[0] === 'data') {
                    data.push(result[1]);
                } else {
                    comparisonData.push(result[1]);
                }
            });
            var allData = self._mergeData(data, comparisonData, groupBys);
            var dataPoint, attrs, j, l, row, col, cell_value;
            for (i = 0; i < allData.length; i++) {
                for (j = 0; j < allData[i].length; j++){
                    dataPoint = allData[i][j];
                    groupBys = [field].concat(other_groupbys.slice(0,i));
                    attrs = {
                        value: self._getValue(dataPoint, groupBys),
                        domain: dataPoint.__domain,
                        comparisonDomain: dataPoint.__comparisonDomain,
                        length: dataPoint.__count.data ? dataPoint.__count.data : dataPoint.__count,
                        comparisonLength: dataPoint.__comparisonCount|| 0,
                    };

                    if (i === 0) {
                        row = self._makeHeader(attrs.value, attrs.domain, attrs.comparisonDomain, attrs.length, attrs.comparisonLength , header.root, 0, 1, header);
                    } else {
                        row = self._getHeader(attrs.value, header.root, 0, 1, header);
                    }
                    col = self._getHeader(attrs.value, other_root, 1, i + 1);
                    if (!col) {
                        continue;
                    }
                    for (cell_value = {}, l=0; l < self.data.measures.length; l++) {
                        var _value = dataPoint[self.data.measures[l]];
                        if (_value instanceof Array) {
                            // when a many2one field is used as a measure AND as
                            // a grouped field, bad things happen.  The server
                            // will only return the grouped value and will not
                            // aggregate it.  Since there is a nameclash, we are
                            // then in the situation where this value is an
                            // array.  Fortunately, if we group by a field,
                            // then we can say for certain that the group contains
                            // exactly one distinct value for that field.
                            if (self.data.compare) {
                                _value = dataPoint[self.data.measures[l] + 'Aggregate'];
                            } else {
                                _value = 1;
                            }
                        }
                        cell_value[self.data.measures[l]] =_value;
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
     * Export the current pivot view in a simple JS object.
     *
     * @returns {Object}
     */
    exportData: function () {
        var self = this;
        var measureNbr = this.data.measures.length;
        var headers = this._computeHeaders();
        if (this.data.compare) {
            _.each(headers, function (headerGroup) {
                _.each(headerGroup, function (header) {
                    header.width = header.width ? 3 * header.width : 3;
                });
            });
        }
        var measureRow = measureNbr >= 1 ? _.last(headers) : [];
        var rows = this._computeRows();
        var i, j, value, values, is_bold, additionalHeaders = [];
        // remove the empty headers on left side
        headers[0].splice(0,1);

        function isBold (i, j) {
            return (i === 0) ||
                        ((self.data.main_col.width > 1) &&
                        (j >= rows[i].values.length - measureNbr));
        }

        function makeValue (value, is_bold) {
            return {
                        is_bold: is_bold,
                        value:  (value === undefined) ? "" : value,
            };
        }

        function makeMeasure (name) {
            return {
                is_bold: false,
                measure: name
            };
        }

        // process measureRow
        additionalHeaders = [];
        for (i = 0; i < measureRow.length; i++) {
            if (this.data.compare) {
                measureRow[i].title = this.fields[measureRow[i].measure].string;
                measureRow[i].height = 1;
                measureRow[i].expanded = true;
                additionalHeaders = additionalHeaders.concat(
                        _.map(
                            [
                                this.data.timeRangeDescription.toString(),
                                this.data.comparisonTimeRangeDescription.toString(),
                                'Variation'
                            ],
                            makeMeasure
                        )
                    );
            } else {
                measureRow[i].measure = this.fields[measureRow[i].measure].string;
            }
        }
        if (this.data.compare) {
            for (i =0, j, value; i < rows.length; i++) {
                values = [];
                for (j = 0; j < rows[i].values.length; j++) {
                    value = rows[i].values[j];
                    is_bold = isBold(i, j);
                    if (value instanceof Object) {
                        for (var origin in value) {
                            if (origin === 'variation') {
                                values.push(makeValue(value[origin].magnitude * 100, is_bold));
                            } else {
                                values.push(makeValue(value[origin], is_bold));
                            }
                        }
                    } else {
                        for (var l = 0; l < 3; l++) {
                            values.push(makeValue(undefined, isBold(i, j)));
                        }
                    }
                }
                rows[i].values = values;
            }
            headers.push(additionalHeaders);
            return {
                headers: _.initial(headers),
                measure_row: additionalHeaders,
                rows: rows,
                nbr_measures: 3 * measureNbr,
            };
        } else {
        // process all rows
            for (i =0, j, value; i < rows.length; i++) {
                for (j = 0; j < rows[i].values.length; j++) {
                    rows[i].values[j] = makeValue(rows[i].values[j], isBold(i, j));
                }
            }
            return {
                headers: _.initial(headers),
                measure_row: measureRow,
                rows: rows,
                nbr_measures: measureNbr,
            };
        }
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
            return {
                has_data: false,
                colGroupBys: this.data.main_col.groupbys,
                rowGroupBys:  this.data.main_row.groupbys,
                measures: this.data.measures,
            };
        }
        return {
            colGroupBys: this.data.main_col.groupbys,
            context: this.data.context,
            domain: this.data.domain,
            compare: this.data.compare,
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
     * @param {string[]} params.timeRange
     * @param {string[]} params.comparisonTimeRange
     * @param {string[]} params.timeRangeDescription
     * @param {string[]} params.comparisonTimeRangeDescription
     * @param {string[]} params.compare
     * @param {Object} params.fields
     * @param {string} params.default_order
     * @returns {Deferred}
     */
    load: function (params) {
        var self = this;

        this.initialDomain = params.domain;
        this.initialRowGroupBys = params.context.pivot_row_groupby || params.rowGroupBys;
        this.fields = params.fields;
        this.modelName = params.modelName;
        this.data = {
            domain: this.initialDomain,
            timeRange: params.timeRange || [],
            timeRangeDescription: params.timeRangeDescription || "",
            comparisonTimeRange: params.comparisonTimeRange || [],
            comparisonTimeRangeDescription: params.comparisonTimeRangeDescription || "",
            compare: params.compare || false,
            context: _.extend({}, session.user_context, params.context),
            groupedBy: params.groupedBy,
            colGroupBys: params.context.pivot_column_groupby || params.colGroupBys,
            measures: this._processMeasures(params.context.pivot_measures) || params.measures,
            sorted_column: {},
        };
        this.variationData = {};
        this.defaultGroupedBy = params.groupedBy;

        return this._loadData().then(function () {
            if (params.default_order) {
                var info = params.default_order.split(' ');
                self.sortRows(self.data.main_col.root.id, info[0], info[1] === 'desc');
            }
        });
    },
    /**
     * @override
     * @param {any} handle this parameter is ignored
     * @param {Object} params
     * @returns {Deferred}
     */
    reload: function (handle, params) {
        var self = this;
        if ('context' in params) {
            this.data.context = params.context;
            this.data.colGroupBys = params.context.pivot_column_groupby || this.data.colGroupBys;
            this.data.groupedBy = params.context.pivot_row_groupby || this.data.groupedBy;
            this.data.measures = this._processMeasures(params.context.pivot_measures) || this.data.measures;
            this.defaultGroupedBy = this.data.groupedBy.length ? this.data.groupedBy : this.defaultGroupedBy;
            var timeRangeMenuData = params.context.timeRangeMenuData;
            if (timeRangeMenuData) {
                this.data.timeRange = timeRangeMenuData.timeRange || [];
                this.data.timeRangeDescription = timeRangeMenuData.timeRangeDescription || "";
                this.data.comparisonTimeRange = timeRangeMenuData.comparisonTimeRange || [];
                this.data.comparisonTimeRangeDescription = timeRangeMenuData.comparisonTimeRangeDescription || "";
                this.data.compare = this.data.comparisonTimeRange.length > 0;
            } else {
                this.data.timeRange = [];
                this.data.timeRangeDescription = "";
                this.data.comparisonTimeRange = [];
                this.data.comparisonTimeRangeDescription = "";
                this.data.compare = false;
                this.data.context = _.omit(this.data.context, 'timeRangeMenuData');
            }
        }
        if ('domain' in params) {
            this.data.domain = params.domain;
        } else {
            this.data.domain = this.initialDomain;
        }
        if ('groupBy' in params) {
            this.data.groupedBy = params.groupBy.length ? params.groupBy : this.defaultGroupedBy;
        }
        if (!this.data.has_data) {
            return this._loadData();
        }

        var old_row_root = this.data.main_row.root;
        var old_col_root = this.data.main_col.root;
        return this._loadData().then(function () {
            var new_groupby_length;
            if (!('groupBy' in params) && !('pivot_row_groupby' in (params.context || {}))) {
                // we only update the row groupbys according to the old groupbys
                // if we don't have the key 'groupBy' in params.  In that case,
                // we want to have the full open state for the groupbys.
                self._updateTree(old_row_root, self.data.main_row.root);
                new_groupby_length = self._getHeaderDepth(self.data.main_row.root) - 1;
                self.data.main_row.groupbys = old_row_root.groupbys.slice(0, new_groupby_length);
            }

            self._updateTree(old_col_root, self.data.main_col.root);
            new_groupby_length = self._getHeaderDepth(self.data.main_col.root) - 1;
            self.data.main_row.groupbys = old_row_root.groupbys.slice(0, new_groupby_length);
        });
    },
    /**
     * Sort the rows, depending on the values of a given column.  This is an
     * in-memory sort.
     *
     * @param {any} col_id
     * @param {any} measure
     * @param {any} descending
     * @param {'data'|'comparisonData'|'variation'} [dataType]
     */
    sortRows: function (col_id, measure, descending, dataType) {
        var cells = this.data.cells;
        var comparisonFunction = compare;
        if (this.data.compare) {
            dataType = dataType || 'data';
            comparisonFunction = specialCompare;
        }
        this._traverseTree(this.data.main_row.root, function (header) {
            header.children.sort(comparisonFunction);
        });
        this.data.sorted_column = {
            id: col_id,
            measure: measure,
            order: descending ? 'desc' : 'asc',
            dataType: dataType,
        };
        function _getValue (id1, id2) {
            if ((id1 in cells) && (id2 in cells[id1])) {
                return cells[id1][id2];
            }
            if (id2 in cells) return cells[id2][id1];
        }

        function compare (row1, row2) {
            var values1 = _getValue(row1.id, col_id);
            var values2 = _getValue(row2.id, col_id);
            var value1 = values1 ? values1[measure] : 0;
            var value2 = values2 ? values2[measure] : 0;
            return descending ? value1 - value2 : value2 - value1;
        }
        function specialCompare (row1, row2) {
            var values1 = _getValue(row1.id, col_id);
            var values2 = _getValue(row2.id, col_id);
            var value1 = values1 ? values1[measure] : {data: 0, comparisonData: 0, variation: {magnitude: 0}};
            var value2 = values2 ? values2[measure] : {data: 0, comparisonData: 0, variation: {magnitude: 0}};
            if (dataType === 'variation') {
                return descending ?
                        value1[dataType].magnitude - value2[dataType].magnitude:
                        value2[dataType].magnitude - value1[dataType].magnitude;
            }
            return descending ?
                        value1[dataType] - value2[dataType]:
                        value2[dataType] - value1[dataType];
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
        var id = value[0];
        var name = value[1];
        this.numbering[field] = this.numbering[field] || {};
        this.numbering[field][name] = this.numbering[field][name] || {};
        var numbers = this.numbering[field][name];
        numbers[id] = numbers[id] || _.size(numbers) + 1;
        return name + (numbers[id] > 1 ? "  (" + numbers[id] + ")" : "");
    },
    /**
     * @param {any} dataPoint
     * @param {any} fields
     * @returns {string[]}
     */
    _getValue: function (dataPoint, fields) {
        var result = [];
        var value;
        for (var i = 0; i < fields.length; i++) {
            value = this._sanitizeValue(dataPoint[fields[i]],fields[i]);
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
        var rowGroupBys = !_.isEmpty(this.data.groupedBy) ? this.data.groupedBy : this.initialRowGroupBys;
        var colGroupBys = this.data.colGroupBys;
        var measures = _.map(this.data.measures, function(measure) {
            if (self.fields[measure].type === 'many2one') {
                return measure + ":count_distinct";
            }
            else {
                return measure;
            }
        });

        for (var i = 0; i < rowGroupBys.length + 1; i++) {
            for (var j = 0; j < colGroupBys.length + 1; j++) {
                groupBys.push(rowGroupBys.slice(0,i).concat(colGroupBys.slice(0,j)));
            }
        }
        var defs = groupBys.map(function (groupBy) {
            return self._rpc({
                    model: self.modelName,
                    method: 'read_group',
                    context: self.data.context,
                    domain: self.data.domain.concat(self.data.timeRange),
                    fields: measures,
                    groupBy: groupBy,
                    lazy: false,
                }).then(function (result) {
                    return ['data', result];
                });
        });
        if (this.data.compare) {
            defs = defs.concat(groupBys.map(function (groupBy) {
                return self._rpc({
                        model: self.modelName,
                        method: 'read_group',
                        context: self.data.context,
                        domain: self.data.domain.concat(self.data.comparisonTimeRange),
                        fields: measures,
                        groupBy: groupBy,
                        lazy: false,
                    }).then(function (result) {
                        return ['comparisonData', result];
                    });
            }));
        }

        return this._loadDataDropPrevious.add($.when.apply(null, defs)).then(function () {
            var results = Array.prototype.slice.call(arguments);
            var data = [];
            var comparisonData = [];
            _.each(results, function (result) {
                if (result[0] === 'data') {
                    data.push(result[1]);
                } else {
                    comparisonData.push(result[1]);
                }
            });
            var allData = self._mergeData(data, comparisonData, groupBys);
            if (allData[0][0].__count === 0 && allData[0][0].__comparisonCount === 0) {
                self.data.has_data = false;
            }
            self._prepareData(allData);
        });
    },
    /**
     * @param {any} value
     * @param {any} domain
     * @param {any} comparisonDomain
     * @param {any} root
     * @param {any} count
     * @param {any} comparisonCount
     * @param {any} i
     * @param {any} j
     * @param {any} parent_header
     * @returns {Object}
     */

    _makeHeader: function (value, domain, comparisonDomain, count, comparisonCount, root, i, j, parent_header) {
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
            domain: domain,
            comparisonDomain: comparisonDomain,
            count: count,
            comparisonCount: comparisonCount,
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
     * Here data and comparisonData are arrays of arrays of objects.
     * Each one of those objects is called a dataPoint and represents a group of records
     * (determined by some groupbys values) together with measure values aggregated.
     * An exception: if a many2one is selected as a measure and a groupby simultaneously,
     * we have only the corresponding groupby value which is the of the form ['id', 'name_get']
     * but the measure value can be inferred, it is indeed 1.
     * In case 'this.data.compare' is true (a comparison is required),
     * the dataPoint are transformed in such a way that the measures values become objects of the form
     *
     *      {'data': 'some value', 'comparisonData': 'other value', 'variation': 'yet another value'}.
     *
     * In case two dataPoints have the same associated group
     * (they then come necessarily from 'data' and 'comparisonData'),
     * they are merged into a single dataPoint of the form above.
     *
     * @param {Object[][]} data
     * @param {Object[][]} comparisonData
     * @param {string[][]} groupBys
     * @returns {Object[][]}
     */
    _mergeData: function (data, comparisonData, groupBys) {
        if (!this.data.compare) {
            return data;
        }
        var allData = [];
        var dataPoints;
        var value, groupIdentifier, dataPoint, m, measureName, measureValue, measureComparisonValue;
        for (var index = 0; index < groupBys.length; index++) {
            dataPoints = {};
            // Consider dataPoints comming from 'data'. The dataPoint measure values are objects with
            // zeros values for the 'comparisonData' key since we don't know at this stage
            // if the group is represented in the 'comparisonData'.
            if (data.length) {
                for (var k = 0; k < data[index].length; k++) {
                    dataPoint  = data[index][k];
                    if (_.isEmpty(dataPoint)){
                        break;
                    }
                    value = this._getValue(dataPoint, groupBys[index]);
                    groupIdentifier = value.join();
                    for (m=0; m < this.data.measures.length; m++) {
                        measureName = this.data.measures[m];
                        measureValue = dataPoint[measureName];
                        if (typeof measureValue === 'boolean') {
                            measureValue = measureValue ? 1 : 0;
                        }
                        if (measureValue === null) {
                            measureValue = 0;
                        }
                        if (!(measureValue instanceof Array) && measureName !== '__count') {
                            dataPoint[measureName] = {
                                data: measureValue,
                                comparisonData : 0,
                                variation: computeVariation(measureValue, 0),
                            };
                        }
                        if (measureValue instanceof Array) {
                            dataPoint[measureName + 'Aggregate'] = {
                                data: 1,
                                comparisonData: 0,
                                variation: computeVariation(1, 0),
                            };
                        }
                    }
                    dataPoint.__count = {
                        data: dataPoint.__count,
                        comparisonData: 0,
                        variation: computeVariation(dataPoint.__count, 0)
                    };
                    dataPoints[groupIdentifier] = dataPoint;
                }
            }
            if (comparisonData.length) {
                for (var l = 0; l < comparisonData[index].length; l++) {
                    dataPoint  = comparisonData[index][l];
                    if (_.isEmpty(dataPoint)){
                        break;
                    }
                    value = this._getValue(dataPoint, groupBys[index]);
                    groupIdentifier = value.join();
                    if (!dataPoints[groupIdentifier]) {
                        // Here we know that the group is not represented in 'data'.
                        for (m=0; m < this.data.measures.length; m++) {
                            measureName = this.data.measures[m];
                            measureComparisonValue = dataPoint[measureName];
                            if (typeof(measureComparisonValue) === 'boolean') {
                                measureComparisonValue = measureComparisonValue ? 1 : 0;
                            }
                            if (measureComparisonValue === null) {
                                measureComparisonValue = 0;
                            }
                            if (!(measureComparisonValue instanceof Array) && measureName !== '__count') {
                                dataPoint[measureName] = {
                                    data: 0,
                                    comparisonData: measureComparisonValue,
                                    variation: computeVariation(0, measureComparisonValue),
                                };
                            }
                            if (measureComparisonValue instanceof Array) {
                                dataPoint[measureName + 'Aggregate'] = {
                                    data: 0,
                                    comparisonData: 1,
                                    variation: computeVariation(0,1),
                                };
                            }
                        }
                        dataPoint.__count = {
                            data: 0,
                            comparisonData: dataPoint.__count,
                            variation: computeVariation(0, dataPoint.__count)
                        };
                        dataPoint.__comparisonCount = dataPoint.__count;
                        dataPoint.__comparisonDomain = dataPoint.__domain;
                        dataPoints[groupIdentifier] = _.omit(dataPoint, '__domain');
                    } else {
                        // Here we know that the group is represented in 'data'.
                        // Therefore we modify the corresonding dataPoint:
                        // we modify the key 'comparisonData' and recompute 'variation'.
                        for (m=0; m < this.data.measures.length; m++) {
                            measureName = this.data.measures[m];
                            measureComparisonValue = dataPoint[measureName];
                            if (typeof(measureComparisonValue) === 'boolean') {
                                measureComparisonValue = measureComparisonValue ? 1 : 0;
                            }
                            if (measureComparisonValue === null) {
                                measureComparisonValue = 0;
                            }
                            if (!(measureComparisonValue instanceof Array) && measureName !== '__count') {
                                dataPoints[groupIdentifier][measureName].comparisonData = measureComparisonValue;
                                dataPoints[groupIdentifier][measureName].variation = computeVariation(
                                    dataPoints[groupIdentifier][measureName].data,
                                    measureComparisonValue
                                );
                            }
                            if (measureComparisonValue instanceof Array) {
                                dataPoints[groupIdentifier][measureName + 'Aggregate'].comparisonData = 1;
                                dataPoints[groupIdentifier][measureName].variation = computeVariation(
                                    dataPoints[groupIdentifier][measureName].data,
                                    1
                                );

                            }
                        }
                        dataPoints[groupIdentifier].__count.comparisonData = dataPoint.__count;
                        dataPoints[groupIdentifier].__count.variation = computeVariation(
                            dataPoints[groupIdentifier].__count.data,
                            dataPoint.__count
                        );
                        dataPoints[groupIdentifier].__comparisonCount = dataPoint.__count;
                        dataPoints[groupIdentifier].__comparisonDomain = dataPoint.__domain;
                    }
                }
            }
            allData.push(_.values(dataPoints));
        }
        return allData;
    },
    /**
     * @param {Object[][]} data
     */
    _prepareData: function (data) {
        var self = this;
        _.extend(this.data, {
            main_row: {},
            main_col: {},
            headers: {},
            cells: [],
        });

        var index = 0;
        var rowGroupBys = !_.isEmpty(this.data.groupedBy) ? this.data.groupedBy : this.initialRowGroupBys;
        var colGroupBys = this.data.colGroupBys;
        var dataPoint, row, col, attrs, cell_value;
        var main_row_header, main_col_header;
        var groupBys;
        var m;


        for (var i = 0; i < rowGroupBys.length + 1; i++) {
            for (var j = 0; j < colGroupBys.length + 1; j++) {
                for (var k = 0; k < data[index].length; k++) {
                    dataPoint = data[index][k];
                    groupBys = rowGroupBys.slice(0,i).concat(colGroupBys.slice(0,j));
                    attrs = {
                        // value could be named 'groupIdentifier'
                        value: self._getValue(dataPoint, groupBys),
                        domain: dataPoint.__domain,
                        comparisonDomain: dataPoint.__comparisonDomain,
                    };
                    if (dataPoint.__count) {
                        attrs.length = dataPoint.__count instanceof Object ? dataPoint.__count.data : dataPoint.__count;
                        attrs.comparisonLength = dataPoint.__comparisonCount;
                    }

                    if (j === 0) {
                        row = this._makeHeader(attrs.value, attrs.domain, attrs.comparisonDomain, attrs.length, attrs.comparisonLength, main_row_header, 0, i);
                    } else {
                        row = this._getHeader(attrs.value, main_row_header, 0, i);
                    }
                    if (i === 0) {
                        col = this._makeHeader(attrs.value, attrs.domain, attrs.comparisonDomain, attrs.length, attrs.comparisonLength, main_col_header, i, i+j);
                    } else {
                        col = this._getHeader(attrs.value, main_col_header, i, i+j);
                    }
                    if (i + j === 0) {
                        this.data.has_data = attrs.length > 0 || attrs.comparisonLength > 0;
                        main_row_header = row;
                        main_col_header = col;
                    }
                    if (!this.data.cells[row.id]) this.data.cells[row.id] = [];
                    for (cell_value = {}, m=0; m < this.data.measures.length; m++) {
                        var _value = dataPoint[this.data.measures[m]];
                        if (_value instanceof Array) {
                            // when a many2one field is used as a measure AND as
                            // a grouped field, bad things happen.  The server
                            // will only return the grouped value and will not
                            // aggregate it.  Since there is a nameclash, we are
                            // then in the situation where this value is an
                            // array.  Fortunately, if we group by a field,
                            // then we can say for certain that the group contains
                            // exactly one distinct value for that field.
                            if (this.data.compare) {
                                _value = dataPoint[this.data.measures[m] + 'Aggregate'];
                            } else {
                                _value = 1;
                            }
                        }
                        cell_value[this.data.measures[m]] = _value;
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
     * In the preview implementation of the pivot view (a.k.a. version 2),
     * the virtual field used to display the number of records was named
     * __count__, whereas __count is actually the one used in xml. So
     * basically, activating a filter specifying __count as measures crashed.
     * Unfortunately, as __count__ was used in the JS, all filters saved as
     * favorite at that time were saved with __count__, and not __count.
     * So in order the make them still work with the new implementation, we
     * handle both __count__ and __count.
     *
     * This function replaces in the given array of measures occurences of
     * '__count__' by '__count'.
     *
     * @param {Array[string] || undefined} measures
     * @return {Array[string] || undefined}
     */
    _processMeasures: function (measures) {
        if (measures) {
            return _.map(measures, function (measure) {
                return measure === '__count__' ? '__count' : measure;
            });
        }
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
