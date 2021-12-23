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
 * way, and to transform it into a list of lines to be displayed by the renderer.
 *
 * Basicaly the pivot table presents aggregated values for various groups of records
 * in one domain. If a comparison is asked for, two domains are considered.
 *
 * Let us consider a simple example and let us fix the vocabulary (let us suppose we are in June 2020):
 * ___________________________________________________________________________________________________________________________________________
 * |                    |   Total                                                                                                             |
 * |                    |_____________________________________________________________________________________________________________________|
 * |                    |   Sale Team 1                         |  Sale Team 2                         |                                      |
 * |                    |_______________________________________|______________________________________|______________________________________|
 * |                    |   Sales total                         |  Sales total                         |  Sales total                         |
 * |                    |_______________________________________|______________________________________|______________________________________|
 * |                    |   May 2020   | June 2020  | Variation |  May 2020   | June 2020  | Variation |  May 2020   | June 2020  | Variation |
 * |____________________|______________|____________|___________|_____________|____________|___________|_____________|____________|___________|
 * | Total              |     85       |     110    |  29.4%    |     40      |    30      |   -25%    |    125      |    140     |     12%   |
 * |    Europe          |     25       |     35     |    40%    |     40      |    30      |   -25%    |     65      |     65     |      0%   |
 * |        Brussels    |      0       |     15     |   100%    |     30      |    30      |     0%    |     30      |     45     |     50%   |
 * |        Paris       |     25       |     20     |   -20%    |     10      |     0      |  -100%    |     35      |     20     |  -42.8%   |
 * |    North America   |     60       |     75     |    25%    |             |            |           |     60      |     75     |     25%   |
 * |        Washington  |     60       |     75     |    25%    |             |            |           |     60      |     75     |     25%   |
 * |____________________|______________|____________|___________|_____________|____________|___________|_____________|____________|___________|
 *
 *
 * META DATA:
 *
 * In the above pivot table, the records have been grouped using the fields
 *
 *      continent_id, city_id
 *
 * for rows and
 *
 *      sale_team_id
 *
 * for columns.
 *
 * The measure is the field 'sales_total'.
 *
 * Two domains are considered: 'May 2020' and 'June 2020'.
 *
 * In the model,
 *
 *      - rowGroupBys is the list [continent_id, city_id]
 *      - colGroupBys is the list [sale_team_id]
 *      - measures is the list [sales_total]
 *      - domains is the list [d1, d2] with d1 and d2 domain expressions
 *          for say sale_date in May 2020 and June 2020, for instance
 *          d1 = [['sale_date', >=, 2020-05-01], ['sale_date', '<=', 2020-05-31]]
 *      - origins is the list ['May 2020', 'June 2020']
 *
 * DATA:
 *
 * Recall that a group is constituted by records (in a given domain)
 * that have the same (raw) values for a list of fields.
 * Thus the group itself is identified by this list and the domain.
 * In comparison mode, the same group (forgetting the domain part or 'originIndex')
 * can be eventually found in the two domains.
 * This defines the way in which the groups are identified or not.
 *
 * In the above table, (forgetting the domain) the following groups are found:
 *
 *      the 'row groups'
 *      - Total
 *      - Europe
 *      - America
 *      - Europe, Brussels
 *      - Europe, Paris
 *      - America, Washington
 *
 *      the 'col groups'
 *
 *      - Total
 *      - Sale Team 1
 *      - Sale Team 2
 *
 *      and all non trivial combinations of row groups and col groups
 *
 *      - Europe, Sale Team 1
 *      - Europe, Brussels, Sale Team 2
 *      - America, Washington, Sale Team 1
 *      - ...
 *
 * The list of fields is created from the concatenation of two lists of fields, the first in
 *
 * [], [f1], [f1, f2], ... [f1, f2, ..., fn]  for [f1, f2, ..., fn] the full list of groupbys
 * (called rowGroupBys) used to create row groups
 *
 * In the example: [], [continent_id], [continent_id, city_id].
 *
 * and the second in
 * [], [g1], [g1, g2], ... [g1, g2, ..., gm]  for [g1, g2, ..., gm] the full list of groupbys
 * (called colGroupBys) used to create col groups.
 *
 * In the example: [], [sale_team_id].
 *
 * Thus there are (n+1)*(m+1) lists of fields possible.
 *
 * In the example: 6 lists possible, namely [],
 *                                          [continent_id], [sale_team_id],
 *                                          [continent_id, sale_team_id], [continent_id, city_id],
 *                                          [continent_id, city_id, sale_team_id]
 *
 * A given list is thus of the form [f1,..., fi, g1,..., gj] or better [[f1,...,fi], [g1,...,gj]]
 *
 * For each list of fields possible and each domain considered, one read_group is done
 * and gives results of the form (an exception for list [])
 *
 * g = {
 *  f1: v1, ..., fi: vi,
 *  g1: w1, ..., gj: wj,
 *  m1: x1, ..., mk: xk,
 *  __count: c,
 *  __domain: d
 * }
 *
 * where v1,...,vi,w1,...,Wj are 'values' for the corresponding fields and
 * m1,...,mk are the fields selected as measures.
 *
 * For example, g = {
 *      continent_id: [1, 'Europe']
 *      sale_team_id: [1, 'Sale Team 1']
 *      sales_count: 25,
 *      __count: 4
 *      __domain: [
 *                  ['sale_date', >=, 2020-05-01], ['sale_date', '<=', 2020-05-31],
 *                  ['continent_id', '=', 1],
 *                  ['sale_team_id', '=', 1]
 *                ]
 * }
 *
 * Thus the above group g is fully determined by [[v1,...,vi], [w1,...,wj]] and the base domain
 * or the corresponding 'originIndex'.
 *
 * When j=0, g corresponds to a row group (or also row header) and is of the form [[v1,...,vi], []] or more simply [v1,...vi]
 * (not forgetting the list [v1,...vi] comes from left).
 * When i=0, g corresponds to a col group (or col header) and is of the form [[], [w1,...,wj]] or more simply [w1,...,wj].
 *
 * A generic group g as above [[v1,...,vi], [w1,...,wj]] corresponds to the two headers [[v1,...,vi], []]
 * and [[], [w1,...,wj]].
 *
 * Here is a description of the data structure manipulated by the pivot model.
 *
 * Five objects contain all the data from the read_groups
 *
 *      - rowGroupTree: contains information on row headers
 *             the nodes correspond to the groups of the form [[v1,...,vi], []]
 *             The root is [[], []].
 *             A node [[v1,...,vl], []] has as direct children the nodes of the form [[v1,...,vl,v], []],
 *             this means that a direct child is obtained by grouping records using the single field fi+1
 *
 *             The structure at each level is of the form
 *
 *             {
 *                  root: {
 *                      values: [v1,...,vl],
 *                      labels: [la1,...,lal]
 *                  },
 *                  directSubTrees: {
 *                      v => {
 *                              root: {
 *                                  values: [v1,...,vl,v]
 *                                  labels: [label1,...,labell,label]
 *                              },
 *                              directSubTrees: {...}
 *                          },
 *                      v' => {...},
 *                      ...
 *                  }
 *             }
 *
 *             (directSubTrees is a Map instance)
 *
 *             In the example, the rowGroupTree is:
 *
 *             {
 *                  root: {
 *                      values: [],
 *                      labels: []
 *                  },
 *                  directSubTrees: {
 *                      1 => {
 *                              root: {
 *                                  values: [1],
 *                                  labels: ['Europe'],
 *                              },
 *                              directSubTrees: {
 *                                  1 => {
 *                                          root: {
 *                                              values: [1, 1],
 *                                              labels: ['Europe', 'Brussels'],
 *                                          },
 *                                          directSubTrees: new Map(),
 *                                  },
 *                                  2 => {
 *                                          root: {
 *                                              values: [1, 2],
 *                                              labels: ['Europe', 'Paris'],
 *                                          },
 *                                          directSubTrees: new Map(),
 *                                  },
 *                              },
 *                          },
 *                      2 => {
 *                              root: {
 *                                  values: [2],
 *                                  labels: ['America'],
 *                              },
 *                              directSubTrees: {
 *                                  3 => {
 *                                          root: {
 *                                              values: [2, 3],
 *                                              labels: ['America', 'Washington'],
 *                                          }
 *                                          directSubTrees: new Map(),
 *                                  },
 *                              },
 *                      },
 *                  },
 *             }
 *
 *      - colGroupTree: contains information on col headers
 *              The same as above with right instead of left
 *
 *      - measurements: contains information on measure values for all the groups
 *
 *              the object keys are of the form JSON.stringify([[v1,...,vi], [w1,...,wj]])
 *              and values are arrays of length equal to number of origins containing objects of the form
 *                  {m1: x1,...,mk: xk}
 *              The structure looks like
 *
 *              {
 *                  JSON.stringify([[], []]): [{m1: x1,...,mk: xk}, {m1: x1',...,mk: xk'},...]
 *                  ....
 *                  JSON.stringify([[v1,...,vi], [w1,...,wj]]): [{m1: y1',...,mk: yk'}, {m1: y1',...,mk: yk'},...],
 *                  ....
 *                  JSON.stringify([[v1,...,vn], [w1,...,wm]]): [{m1: z1',...,mk: zk'}, {m1: z1',...,mk: zk'},...],
 *              }
 *              Thus the structure contains all information for all groups and all origins on measure values.
 *
 *
 *              this.measurments["[[], []]"][0]['foo'] gives the value of the measure 'foo' for the group 'Total' and the
 *              first domain (origin).
 *
 *              In the example:
 *                  {
 *                      "[[], []]": [{'sales_total': 125}, {'sales_total': 140}]                      (total/total)
 *                      ...
 *                      "[[1, 2], [2]]": [{'sales_total': 10}, {'sales_total': 0}]                   (Europe/Paris/Sale Team 2)
 *                      ...
 *                  }
 *
 *      - counts: contains information on the number of records in each groups
 *              The structure is similar to the above but the arrays contains numbers (counts)
 *      - groupDomains:
 *              The structure is similar to the above but the arrays contains domains
 *
 *      With this light data structures, all manipulation done by the model are eased and redundancies are limited.
 *      Each time a rendering or an export of the data has to be done, the pivot table is generated by the _getTable function.
 */

var AbstractModel = require('web.AbstractModel');
var concurrency = require('web.concurrency');
var core = require('web.core');
var dataComparisonUtils = require('web.dataComparisonUtils');
const Domain = require('web.Domain');
var mathUtils = require('web.mathUtils');
var session = require('web.session');


var _t = core._t;
var cartesian = mathUtils.cartesian;
var computeVariation = dataComparisonUtils.computeVariation;
var sections = mathUtils.sections;

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
     * Add a groupBy to rowGroupBys or colGroupBys according to provided type.
     *
     * @param {string} groupBy
     * @param {'row'|'col'} type
     */
    addGroupBy: function (groupBy, type) {
        if (type === 'row') {
            this.data.expandedRowGroupBys.push(groupBy);
        } else {
            this.data.expandedColGroupBys.push(groupBy);
        }
    },
    /**
     * Close the group with id given by groupId. A type must be specified
     * in case groupId is [[], []] (the id of the group 'Total') because this
     * group is present in both colGroupTree and rowGroupTree.
     *
     * @param {Array[]} groupId
     * @param {'row'|'col'} type
     */
    closeGroup: function (groupId, type) {
        var groupBys;
        var expandedGroupBys;
        let keyPart;
        var group;
        var tree;
        if (type === 'row') {
            groupBys = this.data.rowGroupBys;
            expandedGroupBys = this.data.expandedRowGroupBys;
            tree = this.rowGroupTree;
            group = this._findGroup(this.rowGroupTree, groupId[0]);
            keyPart = 0;
        } else {
            groupBys = this.data.colGroupBys;
            expandedGroupBys = this.data.expandedColGroupBys;
            tree = this.colGroupTree;
            group = this._findGroup(this.colGroupTree, groupId[1]);
            keyPart = 1;
        }

        const groupIdPart = groupId[keyPart];
        const range = groupIdPart.map((_, index) => index);
        function keep(key) {
            const idPart = JSON.parse(key)[keyPart];
            return range.some(index => groupIdPart[index] !== idPart[index]) ||
                    idPart.length ===  groupIdPart.length;
        }
        function omitKeys(object) {
            const newObject = {};
            for (const key in object) {
                if (keep(key)) {
                    newObject[key] = object[key];
                }
            }
            return newObject;
        }
        this.measurements = omitKeys(this.measurements);
        this.counts = omitKeys(this.counts);
        this.groupDomains = omitKeys(this.groupDomains);

        group.directSubTrees.clear();
        delete group.sortedKeys;
        var newGroupBysLength = this._getTreeHeight(tree) - 1;
        if (newGroupBysLength <= groupBys.length) {
            expandedGroupBys.splice(0);
            groupBys.splice(newGroupBysLength);
        } else {
            expandedGroupBys.splice(newGroupBysLength - groupBys.length);
        }
    },
    /**
     * Reload the view with the current rowGroupBys and colGroupBys
     * This is the easiest way to expand all the groups that are not expanded
     *
     * @returns {Promise}
     */
    expandAll: function () {
        return this._loadData();
    },
    /**
     * Expand a group by using groupBy to split it.
     *
     * @param {Object} group
     * @param {string} groupBy
     * @returns {Promise}
     */
    expandGroup: async function (group, groupBy) {
        var leftDivisors;
        var rightDivisors;

        if (group.type === 'row') {
            leftDivisors = [[groupBy]];
            rightDivisors = sections(this._getGroupBys().colGroupBys);
        } else {
            leftDivisors = sections(this._getGroupBys().rowGroupBys);
            rightDivisors = [[groupBy]];
        }
        var divisors = cartesian(leftDivisors, rightDivisors);

        delete group.type;
        return this._subdivideGroup(group, divisors);
    },
    /**
     * Export model data in a form suitable for an easy encoding of the pivot
     * table in excell.
     *
     * @returns {Object}
     */
    exportData: function () {
        var measureCount = this.data.measures.length;
        var originCount = this.data.origins.length;

        var table = this._getTable();

        // process headers
        var headers = table.headers;
        var colGroupHeaderRows;
        var measureRow = [];
        var originRow = [];

        function processHeader(header) {
            var inTotalColumn = header.groupId[1].length === 0;
            return {
                title: header.title,
                width: header.width,
                height: header.height,
                is_bold: !!header.measure && inTotalColumn
            };
        }

        if (originCount > 1) {
            colGroupHeaderRows = headers.slice(0, headers.length - 2);
            measureRow = headers[headers.length - 2].map(processHeader);
            originRow = headers[headers.length - 1].map(processHeader);
        } else {
            colGroupHeaderRows = headers.slice(0, headers.length - 1);
            measureRow = headers[headers.length - 1].map(processHeader);
        }

        // remove the empty headers on left side
        colGroupHeaderRows[0].splice(0, 1);

        colGroupHeaderRows = colGroupHeaderRows.map(function (headerRow) {
            return headerRow.map(processHeader);
        });

        // process rows
        var tableRows = table.rows.map(function (row) {
            return {
                title: row.title,
                indent: row.indent,
                values: row.subGroupMeasurements.map(function (measurement) {
                    var value = measurement.value;
                    if (value === undefined) {
                        value = "";
                    } else if (measurement.originIndexes.length > 1) {
                        // in that case the value is a variation and a
                        // number between 0 and 1
                        value = value * 100;
                    }
                    return {
                        is_bold: measurement.isBold,
                        value: value,
                    };
                }),
            };
        });

        return {
            col_group_headers: colGroupHeaderRows,
            measure_headers: measureRow,
            origin_headers: originRow,
            rows: tableRows,
            measure_count: measureCount,
            origin_count: originCount,
        };
    },
    /**
     * Swap the pivot columns and the rows. It is a synchronous operation.
     */
    flip: function () {
        // swap the data: the main column and the main row
        var temp = this.rowGroupTree;
        this.rowGroupTree = this.colGroupTree;
        this.colGroupTree = temp;

        // we need to update the record metadata: (expanded) row and col groupBys
        temp = this.data.rowGroupBys;
        this.data.groupedBy = this.data.colGroupBys;
        this.data.rowGroupBys = this.data.colGroupBys;
        this.data.colGroupBys = temp;
        temp = this.data.expandedColGroupBys;
        this.data.expandedColGroupBys = this.data.expandedRowGroupBys;
        this.data.expandedRowGroupBys = temp;

        function twistKey(key) {
            return JSON.stringify(JSON.parse(key).reverse());
        }

        function twist(object) {
            var newObject = {};
            Object.keys(object).forEach(function (key) {
                var value = object[key];
                newObject[twistKey(key)] = value;
            });
            return newObject;
        }

        this.measurements = twist(this.measurements);
        this.counts = twist(this.counts);
        this.groupDomains = twist(this.groupDomains);
    },
    /**
     * @override
     *
     * @param {Object} [options]
     * @param {boolean} [options.raw=false]
     * @returns {Object}
     */
    __get: function (options) {
        options = options || {};
        var raw = options.raw || false;
        var groupBys = this._getGroupBys();
        var state = {
            colGroupBys: groupBys.colGroupBys,
            context: this.data.context,
            domain: this.data.domain,
            fields: this.fields,
            hasData: this._hasData(),
            isSample: this.isSampleModel,
            measures: this.data.measures,
            origins: this.data.origins,
            rowGroupBys: groupBys.rowGroupBys,
            selectionGroupBys: this._getSelectionGroupBy(groupBys),
            modelName: this.modelName
        };
        if (!raw && state.hasData) {
            state.table = this._getTable();
            state.tree = this.rowGroupTree;
        }
        return state;
    },
    /**
     * Returns the total number of columns of the pivot table.
     *
     * @returns {integer}
     */
    getTableWidth: function () {
        var leafCounts = this._getLeafCounts(this.colGroupTree);
        return leafCounts[JSON.stringify(this.colGroupTree.root.values)] + 2;
    },
    /**
     * @override
     *
     * @param {Object} params
     * @param {boolean} [params.compare=false]
     * @param {Object} params.context
     * @param {Object} params.fields
     * @param {string[]} [params.groupedBy]
     * @param {string[]} params.colGroupBys
     * @param {Array[]} params.domain
     * @param {string[]} params.measures
     * @param {string[]} params.rowGroupBys
     * @param {string} [params.default_order]
     * @param {string} params.modelName
     * @param {Object[]} params.groupableFields
     * @param {Object} params.timeRanges
     * @returns {Promise}
     */
    __load: function (params) {
        this.initialDomain = params.domain;
        this.initialRowGroupBys = params.context.pivot_row_groupby || params.rowGroupBys;
        this.defaultGroupedBy = params.groupedBy;

        this.fields = params.fields;
        this.modelName = params.modelName;
        this.groupableFields = params.groupableFields;
        const measures = this._processMeasures(params.context.pivot_measures) ||
                            params.measures.map(m => m);
        this.data = {
            expandedRowGroupBys: [],
            expandedColGroupBys: [],
            domain: this.initialDomain,
            context: _.extend({}, session.user_context, params.context),
            groupedBy: params.context.pivot_row_groupby || params.groupedBy,
            colGroupBys: params.context.pivot_column_groupby || params.colGroupBys,
            measures,
            timeRanges: params.timeRanges,
        };
        this._computeDerivedParams();

        this.data.groupedBy = this.data.groupedBy.slice();
        this.data.rowGroupBys = !_.isEmpty(this.data.groupedBy) ? this.data.groupedBy : this.initialRowGroupBys.slice();

        var defaultOrder = params.default_order && params.default_order.split(' ');
        if (defaultOrder) {
            this.data.sortedColumn = {
                groupId: [[], []],
                measure: defaultOrder[0],
                order: defaultOrder[1] ? defaultOrder [1] : 'asc',
            };
        }
        return this._loadData();
    },
    /**
     * @override
     *
     * @param {any} handle this parameter is ignored
     * @param {Object} params
     * @param {boolean} [params.compare=false]
     * @param {Object} params.context
     * @param {string[]} [params.groupedBy]
     * @param {Array[]} params.domain
     * @param {string[]} params.groupBy
     * @param {string[]} params.measures
     * @param {Object} [params.timeRanges]
     * @returns {Promise}
     */
    __reload: function (handle, params) {
        var self = this;
        var oldColGroupBys = this.data.colGroupBys;
        var oldRowGroupBys = this.data.rowGroupBys;
        if ('context' in params) {
            this.data.context = params.context;
            this.data.colGroupBys = params.context.pivot_column_groupby || this.data.colGroupBys;
            this.data.groupedBy = params.context.pivot_row_groupby || this.data.groupedBy;
            this.data.measures = this._processMeasures(params.context.pivot_measures) || this.data.measures;
            this.defaultGroupedBy = this.data.groupedBy.length ? this.data.groupedBy : this.defaultGroupedBy;
        }
        if ('domain' in params) {
            this.data.domain = params.domain;
            this.initialDomain = params.domain;
        } else {
            this.data.domain = this.initialDomain;
        }
        if ('groupBy' in params) {
            this.data.groupedBy = params.groupBy.length ? params.groupBy : this.defaultGroupedBy;
        }
        if ('timeRanges' in params) {
            this.data.timeRanges = params.timeRanges;
        }
        this._computeDerivedParams();

        this.data.groupedBy = this.data.groupedBy.slice();
        this.data.rowGroupBys = !_.isEmpty(this.data.groupedBy) ? this.data.groupedBy : this.initialRowGroupBys.slice();

        if (!_.isEqual(oldRowGroupBys, self.data.rowGroupBys)) {
            this.data.expandedRowGroupBys = [];
        }
        if (!_.isEqual(oldColGroupBys, self.data.colGroupBys)) {
            this.data.expandedColGroupBys = [];
        }

        if ('measure' in params) {
            return this._toggleMeasure(params.measure);
        }

        if (!this._hasData()) {
            return this._loadData();
        }

        var oldRowGroupTree = this.rowGroupTree;
        var oldColGroupTree = this.colGroupTree;
        return this._loadData().then(function () {
            if (_.isEqual(oldRowGroupBys, self.data.rowGroupBys)) {
                self._pruneTree(self.rowGroupTree, oldRowGroupTree);
            }
            if (_.isEqual(oldColGroupBys, self.data.colGroupBys)) {
                self._pruneTree(self.colGroupTree, oldColGroupTree);
            }
        });
    },
    /**
     * Sort the rows, depending on the values of a given column.  This is an
     * in-memory sort.
     *
     * @param {Object} sortedColumn
     * @param {number[]} sortedColumn.groupId
     */
    sortRows: function (sortedColumn) {
        var self = this;
        var colGroupValues = sortedColumn.groupId[1];
        sortedColumn.originIndexes = sortedColumn.originIndexes || [0];
        this.data.sortedColumn = sortedColumn;

        var sortFunction = function (tree) {
            return function (subTreeKey) {
                var subTree = tree.directSubTrees.get(subTreeKey);
                var groupIntersectionId = [subTree.root.values, colGroupValues];
                var value = self._getCellValue(
                    groupIntersectionId,
                    sortedColumn.measure,
                    sortedColumn.originIndexes
                ) || 0;
                return sortedColumn.order === 'asc' ? value : -value;
            };
        };

        this._sortTree(sortFunction, this.rowGroupTree);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add labels/values in the provided groupTree. A new leaf is created in
     * the groupTree with a root object corresponding to the group with given
     * labels/values.
     *
     * @private
     * @param {Object} groupTree, either this.rowGroupTree or this.colGroupTree
     * @param {string[]} labels
     * @param {Array} values
     */
    _addGroup: function (groupTree, labels, values) {
        var tree = groupTree;
        // we assume here that the group with value value.slice(value.length - 2) has already been added.
        values.slice(0, values.length - 1).forEach(function (value) {
            tree = tree.directSubTrees.get(value);
        });
        const value = values[values.length - 1];
        if (tree.directSubTrees.has(value)) {
            return;
        }
        tree.directSubTrees.set(value, {
            root: {
                labels: labels,
                values: values,
            },
            directSubTrees: new Map(),
        });
    },
    /**
     * Compute what should be used as rowGroupBys by the pivot view
     *
     * @private
     * @returns {string[]}
     */
    _computeRowGroupBys: function () {
        return !_.isEmpty(this.data.groupedBy) ? this.data.groupedBy : this.initialRowGroupBys;
    },
    /**
     * Find a group with given values in the provided groupTree, either
     * this.rowGrouptree or this.colGroupTree.
     *
     * @private
     * @param  {Object} groupTree
     * @param  {Array} values
     * @returns {Object}
     */
    _findGroup: function (groupTree, values) {
        var tree = groupTree;
        values.slice(0, values.length).forEach(function (value) {
            tree = tree.directSubTrees.get(value);
        });
        return tree;
    },
    /**
     * In case originIndex is an array of length 1, thus a single origin
     * index, returns the given measure for a group determined by the id
     * groupId and the origin index.
     * If originIndexes is an array of length 2, we compute the variation
     * ot the measure values for the groups determined by groupId and the
     * different origin indexes.
     *
     * @private
     * @param  {Array[]} groupId
     * @param  {string} measure
     * @param  {number[]} originIndexes
     * @returns {number}
     */
    _getCellValue: function (groupId, measure, originIndexes) {
        var self = this;
        var key = JSON.stringify(groupId);
        if (!self.measurements[key]) {
            return;
        }
        var values = originIndexes.map(function (originIndex) {
            return self.measurements[key][originIndex][measure];
        });
        if (originIndexes.length > 1) {
            return computeVariation(values[1], values[0]);
        } else {
            return values[0];
        }
    },
    /**
     * Returns the rowGroupBys and colGroupBys arrays that
     * are actually used by the pivot view internally
     * (for read_group or other purpose)
     *
     * @private
     * @returns {Object} with keys colGroupBys and rowGroupBys
     */
    _getGroupBys: function () {
        return {
            colGroupBys: this.data.colGroupBys.concat(this.data.expandedColGroupBys),
            rowGroupBys: this.data.rowGroupBys.concat(this.data.expandedRowGroupBys),
        };
    },
    /**
     * Returns a domain representation of a group
     *
     * @private
     * @param  {Object} group
     * @param  {Array} group.colValues
     * @param  {Array} group.rowValues
     * @param  {number} group.originIndex
     * @returns {Array[]}
     */
    _getGroupDomain: function (group) {
        var key = JSON.stringify([group.rowValues, group.colValues]);
        return this.groupDomains[key][group.originIndex];
    },
    /**
     * Returns the group sanitized labels.
     *
     * @private
     * @param  {Object} group
     * @param  {string[]} groupBys
     * @returns {string[]}
     */
    _getGroupLabels: function (group, groupBys) {
        var self = this;
        return groupBys.map(function (groupBy) {
            return self._sanitizeLabel(group[groupBy], groupBy);
        });
    },
    /**
     * Returns a promise that returns the annotated read_group results
     * corresponding to a partition of the given group obtained using the given
     * rowGroupBy and colGroupBy.
     *
     * @private
     * @param  {Object} group
     * @param  {string[]} rowGroupBy
     * @param  {string[]} colGroupBy
     * @returns {Promise}
     */
    _getGroupSubdivision: function (group, rowGroupBy, colGroupBy) {
        var groupDomain = this._getGroupDomain(group);
        var measureSpecs = this._getMeasureSpecs();
        var groupBy = rowGroupBy.concat(colGroupBy);
        return this._rpc({
            model: this.modelName,
            method: 'read_group',
            context: this.data.context,
            domain: groupDomain,
            fields: measureSpecs,
            groupBy: groupBy,
            lazy: false,
        }).then(function (subGroups) {
            return {
                group: group,
                subGroups: subGroups,
                rowGroupBy: rowGroupBy,
                colGroupBy: colGroupBy
            };
        });
    },
    /**
     * Returns the group sanitized values.
     *
     * @private
     * @param  {Object} group
     * @param  {string[]} groupBys
     * @returns {Array}
     */
    _getGroupValues: function (group, groupBys) {
        var self = this;
        return groupBys.map(function (groupBy) {
            return self._sanitizeValue(group[groupBy]);
        });
    },
    /**
     * Returns the leaf counts of each group inside the given tree.
     *
     * @private
     * @param {Object} tree
     * @returns {Object} keys are group ids
     */
    _getLeafCounts: function (tree) {
        var self = this;
        var leafCounts = {};
        var leafCount;
        if (!tree.directSubTrees.size) {
            leafCount = 1;
        } else {
            leafCount = [...tree.directSubTrees.values()].reduce(
                function (acc, subTree) {
                    var subLeafCounts = self._getLeafCounts(subTree);
                    _.extend(leafCounts, subLeafCounts);
                    return acc + leafCounts[JSON.stringify(subTree.root.values)];
                },
                0
            );
        }

        leafCounts[JSON.stringify(tree.root.values)] = leafCount;
        return leafCounts;
    },
    /**
     * Returns the group sanitized measure values for the measures in
     * this.data.measures (that migth contain '__count', not really a fieldName).
     *
     * @private
     * @param  {Object} group
     * @returns {Array}
     */
    _getMeasurements: function (group) {
        var self = this;
        return this.data.measures.reduce(
            function (measurements, fieldName) {
                var measurement = group[fieldName];
                if (measurement instanceof Array) {
                    // case field is many2one and used as measure and groupBy simultaneously
                    measurement = 1;
                }
                if (self.fields[fieldName].type === 'boolean' && measurement instanceof Boolean) {
                    measurement = measurement ? 1 : 0;
                }
                if (self.data.origins.length > 1 && !measurement) {
                    measurement = 0;
                }
                measurements[fieldName] = measurement;
                return measurements;
            },
            {}
        );
    },
    /**
     * Returns a description of the measures row of the pivot table
     *
     * @private
     * @param {Object[]} columns for which measure cells must be generated
     * @returns {Object[]}
     */
    _getMeasuresRow: function (columns) {
        var self = this;
        var sortedColumn = this.data.sortedColumn || {};
        var measureRow = [];

        columns.forEach(function (column) {
            self.data.measures.forEach(function (measure) {
                var measureCell = {
                    groupId: column.groupId,
                    height: 1,
                    measure: measure,
                    title: self.fields[measure].string,
                    width: 2 * self.data.origins.length - 1,
                };
                if (sortedColumn.measure === measure &&
                    _.isEqual(sortedColumn.groupId, column.groupId)) {
                    measureCell.order = sortedColumn.order;
                }
                measureRow.push(measureCell);
            });
        });

        return measureRow;
    },
    /**
     * Returns the list of measure specs associated with data.measures, i.e.
     * a measure 'fieldName' becomes 'fieldName:groupOperator' where
     * groupOperator is the value specified on the field 'fieldName' for
     * the key group_operator.
     *
     * @private
     * @return {string[]}
     */
    _getMeasureSpecs: function () {
        var self = this;
        return this.data.measures.reduce(
            function (acc, measure) {
                if (measure === '__count') {
                    acc.push(measure);
                    return acc;
                }
                var type = self.fields[measure].type;
                var groupOperator = self.fields[measure].group_operator;
                if (type === 'many2one') {
                    groupOperator = 'count_distinct';
                }
                if (groupOperator === undefined) {
                    throw new Error("No aggregate function has been provided for the measure '" + measure + "'");
                }
                acc.push(measure + ':' + groupOperator);
                return acc;
            },
            []
        );
    },
    /**
     * Make sure that the labels of different many2one values are distinguished
     * by numbering them if necessary.
     *
     * @private
     * @param {Array} label
     * @param {string} fieldName
     * @returns {string}
     */
    _getNumberedLabel: function (label, fieldName) {
        var id = label[0];
        var name = label[1];
        this.numbering[fieldName] = this.numbering[fieldName] || {};
        this.numbering[fieldName][name] = this.numbering[fieldName][name] || {};
        var numbers = this.numbering[fieldName][name];
        numbers[id] = numbers[id] || _.size(numbers) + 1;
        return name + (numbers[id] > 1 ? "  (" + numbers[id] + ")" : "");
    },
    /**
     * Returns a description of the origins row of the pivot table
     *
     * @private
     * @param {Object[]} columns for which origin cells must be generated
     * @returns {Object[]}
     */
    _getOriginsRow: function (columns) {
        var self = this;
        var sortedColumn = this.data.sortedColumn || {};
        var originRow = [];

        columns.forEach(function (column) {
            var groupId = column.groupId;
            var measure = column.measure;
            var isSorted = sortedColumn.measure === measure &&
                _.isEqual(sortedColumn.groupId, groupId);
            var isSortedByOrigin = isSorted && !sortedColumn.originIndexes[1];
            var isSortedByVariation = isSorted && sortedColumn.originIndexes[1];

            self.data.origins.forEach(function (origin, originIndex) {
                var originCell = {
                    groupId: groupId,
                    height: 1,
                    measure: measure,
                    originIndexes: [originIndex],
                    title: origin,
                    width: 1,
                };
                if (isSortedByOrigin && sortedColumn.originIndexes[0] === originIndex) {
                    originCell.order = sortedColumn.order;
                }
                originRow.push(originCell);

                if (originIndex > 0) {
                    var variationCell = {
                        groupId: groupId,
                        height: 1,
                        measure: measure,
                        originIndexes: [originIndex - 1, originIndex],
                        title: _t('Variation'),
                        width: 1,
                    };
                    if (isSortedByVariation && sortedColumn.originIndexes[1] === originIndex) {
                        variationCell.order = sortedColumn.order;
                    }
                    originRow.push(variationCell);
                }

            });
        });

        return originRow;
    },

    /**
     * Get the selection needed to display the group by dropdown
     * @returns {Object[]}
     * @private
     */
    _getSelectionGroupBy: function (groupBys) {
        let groupedFieldNames = groupBys.rowGroupBys
            .concat(groupBys.colGroupBys)
            .map(function (g) {
                return g.split(':')[0];
            });

        var fields = Object.keys(this.groupableFields)
            .map((fieldName, index) => {
                return {
                    name: fieldName,
                    field: this.groupableFields[fieldName],
                    active: groupedFieldNames.includes(fieldName)
                }
            })
            .sort((left, right) => left.field.string < right.field.string ? -1 : 1);
        return fields;
    },

    /**
     * Returns a description of the pivot table.
     *
     * @private
     * @returns {Object}
     */
    _getTable: function () {
        var headers = this._getTableHeaders();
        return {
            headers: headers,
            rows: this._getTableRows(this.rowGroupTree, headers[headers.length - 1]),
        };
    },
    /**
     * Returns the list of header rows of the pivot table: the col group rows
     * (depending on the col groupbys), the measures row and optionnaly the
     * origins row (if there are more than one origins).
     *
     * @private
     * @returns {Object[]}
     */
    _getTableHeaders: function () {
        var colGroupBys = this._getGroupBys().colGroupBys;
        var height = colGroupBys.length + 1;
        var measureCount = this.data.measures.length;
        var originCount = this.data.origins.length;
        var leafCounts = this._getLeafCounts(this.colGroupTree);
        var headers = [];
        var measureColumns = []; // used to generate the measure cells

        // 1) generate col group rows (total row + one row for each col groupby)
        var colGroupRows = (new Array(height)).fill(0).map(function () {
            return [];
        });
        // blank top left cell
        colGroupRows[0].push({
            height: height + 1 + (originCount > 1 ? 1 : 0), // + measures rows [+ origins row]
            title: "",
            width: 1,
        });

        // col groupby cells with group values
        /**
         * Recursive function that generates the header cells corresponding to
         * the groups of a given tree.
         *
         * @param {Object} tree
         */
        function generateTreeHeaders(tree, fields) {
            var group = tree.root;
            var rowIndex = group.values.length;
            var row = colGroupRows[rowIndex];
            var groupId = [[], group.values];
            var isLeaf = !tree.directSubTrees.size;
            var leafCount = leafCounts[JSON.stringify(tree.root.values)];
            var cell = {
                groupId: groupId,
                height: isLeaf ? (colGroupBys.length + 1 - rowIndex) : 1,
                isLeaf: isLeaf,
                label: rowIndex === 0 ? undefined : fields[colGroupBys[rowIndex - 1].split(':')[0]].string,
                title: group.labels[group.labels.length - 1] || _t('Total'),
                width: leafCount * measureCount * (2 * originCount - 1),
            };
            row.push(cell);
            if (isLeaf) {
                measureColumns.push(cell);
            }

            [...tree.directSubTrees.values()].forEach(function (subTree) {
                generateTreeHeaders(subTree, fields);
            });
        }

        generateTreeHeaders(this.colGroupTree, this.fields);
        // blank top right cell for 'Total' group (if there is more that one leaf)
        if (leafCounts[JSON.stringify(this.colGroupTree.root.values)] > 1) {
            var groupId = [[], []];
            var totalTopRightCell = {
                groupId: groupId,
                height: height,
                title: "",
                width: measureCount * (2 * originCount - 1),
            };
            colGroupRows[0].push(totalTopRightCell);
            measureColumns.push(totalTopRightCell);
        }
        headers = headers.concat(colGroupRows);

        // 2) generate measures row
        var measuresRow = this._getMeasuresRow(measureColumns);
        headers.push(measuresRow);

        // 3) generate origins row if more than one origin
        if (originCount > 1) {
            headers.push(this._getOriginsRow(measuresRow));
        }

        return headers;
    },
    /**
     * Returns the list of body rows of the pivot table for a given tree.
     *
     * @private
     * @param {Object} tree
     * @param {Object[]} columns
     * @returns {Object[]}
     */
    _getTableRows: function (tree, columns) {
        var self = this;

        var rows = [];
        var group = tree.root;
        var rowGroupId = [group.values, []];
        var title = group.labels[group.labels.length - 1] || _t('Total');
        var indent = group.labels.length;
        var isLeaf = !tree.directSubTrees.size;
        var rowGroupBys = this._getGroupBys().rowGroupBys;

        var subGroupMeasurements = columns.map(function (column) {
            var colGroupId = column.groupId;
            var groupIntersectionId = [rowGroupId[0], colGroupId[1]];
            var measure = column.measure;
            var originIndexes = column.originIndexes || [0];

            var value = self._getCellValue(groupIntersectionId, measure, originIndexes);

            var measurement = {
                groupId: groupIntersectionId,
                originIndexes: originIndexes,
                measure: measure,
                value: value,
                isBold: !groupIntersectionId[0].length || !groupIntersectionId[1].length,
            };
            return measurement;
        });

        rows.push({
            title: title,
            label: indent === 0 ? undefined : this.fields[rowGroupBys[indent - 1].split(':')[0]].string,
            groupId: rowGroupId,
            indent: indent,
            isLeaf: isLeaf,
            subGroupMeasurements: subGroupMeasurements
        });

        var subTreeKeys = tree.sortedKeys || [...tree.directSubTrees.keys()];
        subTreeKeys.forEach(function (subTreeKey) {
            var subTree = tree.directSubTrees.get(subTreeKey);
            rows = rows.concat(self._getTableRows(subTree, columns));
        });

        return rows;
    },
    /**
     * returns the height of a given groupTree
     *
     * @private
     * @param  {Object} tree, a groupTree
     * @returns {number}
     */
    _getTreeHeight: function (tree) {
        var subTreeHeights = [...tree.directSubTrees.values()].map(this._getTreeHeight.bind(this));
        return Math.max(0, Math.max.apply(null, subTreeHeights)) + 1;
    },
    /**
     * @private
     * @returns {boolean}
     */
    _hasData: function () {
        return (this.counts[JSON.stringify([[], []])] || []).some(function (count) {
            return count > 0;
        });
    },
    /**
     * @override
     */
    _isEmpty() {
        return !this._hasData();
    },
    /**
     * Initilize/Reinitialize this.rowGroupTree, colGroupTree, measurements,
     * counts and subdivide the group 'Total' as many times it is necessary.
     * A first subdivision with no groupBy (divisors.slice(0, 1)) is made in
     * order to see if there is data in the intersection of the group 'Total'
     * and the various origins. In case there is none, nonsupplementary rpc
     * will be done (see the code of subdivideGroup).
     * Once the promise resolves, this.rowGroupTree, colGroupTree,
     * measurements, counts are correctly set.
     *
     * @private
     * @return {Promise}
     */
    _loadData: function () {
        var self = this;

        this.rowGroupTree = { root: { labels: [], values: [] }, directSubTrees: new Map() };
        this.colGroupTree = { root: { labels: [], values: [] }, directSubTrees: new Map() };
        this.measurements = {};
        this.counts = {};

        var key = JSON.stringify([[], []]);
        this.groupDomains = {};
        this.groupDomains[key] = this.data.domains.slice(0);


        var group = { rowValues: [], colValues: [] };
        var groupBys = this._getGroupBys();
        var leftDivisors = sections(groupBys.rowGroupBys);
        var rightDivisors = sections(groupBys.colGroupBys);
        var divisors = cartesian(leftDivisors, rightDivisors);

        return this._subdivideGroup(group, divisors.slice(0, 1)).then(function () {
            return self._subdivideGroup(group, divisors.slice(1));
        });
    },
    /**
     * Extract the information in the read_group results (groupSubdivisions)
     * and develop this.rowGroupTree, colGroupTree, measurements, counts, and
     * groupDomains.
     * If a column needs to be sorted, the rowGroupTree corresponding to the
     * group is sorted.
     *
     * @private
     * @param  {Object} group
     * @param  {Object[]} groupSubdivisions
     */
    _prepareData: function (group, groupSubdivisions) {
        var self = this;

        var groupRowValues = group.rowValues;
        var groupRowLabels = [];
        var rowSubTree = this.rowGroupTree;
        var root;
        if (groupRowValues.length) {
            // we should have labels information on hand! regretful!
            rowSubTree = this._findGroup(this.rowGroupTree, groupRowValues);
            root = rowSubTree.root;
            groupRowLabels = root.labels;
        }

        var groupColValues = group.colValues;
        var groupColLabels = [];
        if (groupColValues.length) {
            root = this._findGroup(this.colGroupTree, groupColValues).root;
            groupColLabels = root.labels;
        }

        groupSubdivisions.forEach(function (groupSubdivision) {
            groupSubdivision.subGroups.forEach(function (subGroup) {

                var rowValues = groupRowValues.concat(self._getGroupValues(subGroup, groupSubdivision.rowGroupBy));
                var rowLabels = groupRowLabels.concat(self._getGroupLabels(subGroup, groupSubdivision.rowGroupBy));

                var colValues = groupColValues.concat(self._getGroupValues(subGroup, groupSubdivision.colGroupBy));
                var colLabels = groupColLabels.concat(self._getGroupLabels(subGroup, groupSubdivision.colGroupBy));

                if (!colValues.length && rowValues.length) {
                    self._addGroup(self.rowGroupTree, rowLabels, rowValues);
                }
                if (colValues.length && !rowValues.length) {
                    self._addGroup(self.colGroupTree, colLabels, colValues);
                }

                var key = JSON.stringify([rowValues, colValues]);
                var originIndex = groupSubdivision.group.originIndex;

                if (!(key in self.measurements)) {
                    self.measurements[key] = self.data.origins.map(function () {
                        return self._getMeasurements({});
                    });
                }
                self.measurements[key][originIndex] = self._getMeasurements(subGroup);

                if (!(key in self.counts)) {
                    self.counts[key] = self.data.origins.map(function () {
                        return 0;
                    });
                }
                self.counts[key][originIndex] = subGroup.__count;

                if (!(key in self.groupDomains)) {
                    self.groupDomains[key] = self.data.origins.map(function () {
                        return Domain.FALSE_DOMAIN;
                    });
                }
                // if __domain is not defined this means that we are in the
                // case where
                // groupSubdivision.rowGroupBy = groupSubdivision.rowGroupBy = []
                if (subGroup.__domain) {
                    self.groupDomains[key][originIndex] = subGroup.__domain;
                }
            });
        });

        if (this.data.sortedColumn) {
            this.sortRows(this.data.sortedColumn, rowSubTree);
        }
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
     * @private
     * @param {Array[string] || undefined} measures
     * @returns {Array[string] || undefined}
     */
    _processMeasures: function (measures) {
        if (measures) {
            return _.map(measures, function (measure) {
                return measure === '__count__' ? '__count' : measure;
            });
        }
    },
    /**
     * Determine this.data.domains and this.data.origins from
     * this.data.domain and this.data.timeRanges;
     *
     * @private
     */
    _computeDerivedParams: function () {
        const { range, rangeDescription, comparisonRange, comparisonRangeDescription } = this.data.timeRanges;
        if (range) {
            this.data.domains = [this.data.domain.concat(comparisonRange), this.data.domain.concat(range)];
            this.data.origins = [comparisonRangeDescription, rangeDescription];
        } else {
            this.data.domains = [this.data.domain];
            this.data.origins = [""];
        }
    },
    /**
     * Make any group in tree a leaf if it was a leaf in oldTree.
     *
     * @private
     * @param {Object} tree
     * @param {Object} oldTree
     */
    _pruneTree: function (tree, oldTree) {
        if (!oldTree.directSubTrees.size) {
            tree.directSubTrees.clear();
            delete tree.sortedKeys;
            return;
        }
        var self = this;
        [...tree.directSubTrees.keys()].forEach(function (subTreeKey) {
            var subTree = tree.directSubTrees.get(subTreeKey);
            if (!oldTree.directSubTrees.has(subTreeKey)) {
                subTree.directSubTrees.clear();
                delete subTreeKey.sortedKeys;
            } else {
                var oldSubTree = oldTree.directSubTrees.get(subTreeKey);
                self._pruneTree(subTree, oldSubTree);
            }
        });
    },
    /**
     * Toggle the active state for a given measure, then reload the data
     * if this turns out to be necessary.
     *
     * @param {string} fieldName
     * @returns {Promise}
     */
    _toggleMeasure: function (fieldName) {
        var index = this.data.measures.indexOf(fieldName);
        if (index !== -1) {
            this.data.measures.splice(index, 1);
            // in this case, we already have all data in memory, no need to
            // actually reload a lesser amount of information
            return Promise.resolve();
        } else {
            this.data.measures.push(fieldName);
        }
        return this._loadData();
    },
    /**
     * Extract from a groupBy value a label.
     *
     * @private
     * @param  {any} value
     * @param  {string} groupBy
     * @returns {string}
     */
    _sanitizeLabel: function (value, groupBy) {
        var fieldName = groupBy.split(':')[0];
        if (value === false) {
            return _t("Undefined");
        }
        if (value instanceof Array) {
            return this._getNumberedLabel(value, fieldName);
        }
        if (fieldName && this.fields[fieldName] && (this.fields[fieldName].type === 'selection')) {
            var selected = _.where(this.fields[fieldName].selection, { 0: value })[0];
            return selected ? selected[1] : value;
        }
        return value;
    },
    /**
     * Extract from a groupBy value the raw value of that groupBy (discarding
     * a label if any)
     *
     * @private
     * @param {any} value
     * @returns {any}
     */
    _sanitizeValue: function (value) {
        if (value instanceof Array) {
            return value[0];
        }
        return value;
    },
    /**
     * Get all partitions of a given group using the provided list of divisors
     * and enrich the objects of this.rowGroupTree, colGroupTree,
     * measurements, counts.
     *
     * @private
     * @param {Object} group
     * @param {Array[]} divisors
     * @returns
     */
    _subdivideGroup: function (group, divisors) {
        var self = this;

        var key = JSON.stringify([group.rowValues, group.colValues]);

        var proms = this.data.origins.reduce(
            function (acc, origin, originIndex) {
                // if no information on group content is available, we fetch data.
                // if group is known to be empty for the given origin,
                // we don't need to fetch data fot that origin.
                if (!self.counts[key] || self.counts[key][originIndex] > 0) {
                    var subGroup = {
                        rowValues: group.rowValues,
                        colValues: group.colValues,
                        originIndex: originIndex
                    };
                    divisors.forEach(function (divisor) {
                        acc.push(self._getGroupSubdivision(subGroup, divisor[0], divisor[1]));
                    });
                }
                return acc;
            },
            []
        );
        return this._loadDataDropPrevious.add(Promise.all(proms)).then(function (groupSubdivisions) {
            if (groupSubdivisions.length) {
                self._prepareData(group, groupSubdivisions);
            }
        });
    },
    /**
     * Sort recursively the subTrees of tree using sortFunction.
     * In the end each node of the tree has its direct children sorted
     * according to the criterion reprensented by sortFunction.
     *
     * @private
     * @param  {Function} sortFunction
     * @param  {Object} tree
     */
    _sortTree: function (sortFunction, tree) {
        var self = this;
        tree.sortedKeys = _.sortBy([...tree.directSubTrees.keys()], sortFunction(tree));
        [...tree.directSubTrees.values()].forEach(function (subTree) {
            self._sortTree(sortFunction, subTree);
        });
    },
});

return PivotModel;

});
