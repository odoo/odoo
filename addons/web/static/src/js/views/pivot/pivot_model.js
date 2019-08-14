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
 * Let us consider a simple example and let us fix the vocabulary:
 * ___________________________________________________________________________________________________________________________________________
 * |                    |   Total                                                                                                             |
 * |                    |_____________________________________________________________________________________________________________________|
 * |                    |   Sale Team 1                         |  Sale Team 2                         |                                      |
 * |                    |_______________________________________|______________________________________|______________________________________|
 * |                    |   Sales total                         |  Sales total                         |  Sales total                         |
 * |                    |_______________________________________|______________________________________|______________________________________|
 * |                    |   This Month | Last Month | Variation |  This Month | Last Month | Variation |  This Month | Last Month | Variation |
 * |____________________|______________|____________|___________|_____________|____________|___________|_____________|____________|___________|
 * | Total              |    110       |     85     |  29.4%    |     30      |    40      |   -25%    |    140      |    125     |     12%   |
 * |    Europe          |     35       |     25     |    40%    |     30      |    40      |   -25%    |     65      |     65     |      0%   |
 * |        Brussels    |     15       |      0     |   100%    |     30      |    30      |     0%    |     45      |     30     |     50%   |
 * |        Paris       |     20       |     25     |   -20%    |      0      |    10      |  -100%    |     20      |     35     |  -42.8%   |
 * |    North America   |     75       |     60     |    25%    |             |            |           |     75      |     60     |     25%   |
 * |        Washington  |     75       |     60     |    25%    |             |            |           |     75      |     60     |     25%   |
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
 * Two domains are considered: 'This Month' and 'Last Month'.
 *
 * In the model,
 *
 *      - rowGroupBys is the list [continent_id, city_id]
 *      - colGroupBys is the list [sale_team_id]
 *      - measures is the list [sales_total]
 *      - domains is the list [d1, d2] with d1 and d2 domain expressions
 *          for say sale_date in this month and last month, for instance
 *          d1 = [['sale_date', >=, 2019-05-01], ['sale_date', '<', 2019-05-31]]
 *      - origins is the list ['This Month', 'Last Month']
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
 * and gives results of the form (an exceptions for list [])
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
 *      sales_count: 35,
 *      __count: 4
 *      __domain: [
 *                  ['sale_date', >=, 2019-05-01], ['sale_date', '<', 2019-05-31],
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
 *      - headers: contains information on row headers
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
 *                  directSubHeaders: {
 *                      JSON.stringify(v): {
 *                              root: {
 *                                  values: [v1,...,vl,v]
 *                                  labels: [label1,...,labell,label]
 *                              },
 *                              directSubHeaders: {...}
 *                          },
 *                      JSON.stringify(v'): {...},
 *                      ...
 *                  }
 *             }
 *
 *             In the example, the headers is:
 *
 *             {
 *                  root: {
 *                      values: [],
 *                      labels: []
 *                  },
 *                  directSubHeaders: {
 *                      1: {
 *                              root: {
 *                                  values: [1],
 *                                  labels: ['Europe'],
 *                              },
 *                              directSubHeaders: {
 *                                  1: {
 *                                          root: {
 *                                              values: [1, 1],
 *                                              labels: ['Europe', 'Brussels'],
 *                                          },
 *                                          directSubHeaders: {},
 *                                  },
 *                                  2: {
 *                                          root: {
 *                                              values: [1, 2],
 *                                              labels: ['Europe', 'Paris'],
 *                                          },
 *                                          directSubHeaders: {},
 *                                  },
 *                              },
 *                          },
 *                      2: {
 *                              root: {
 *                                  values: [2],
 *                                  labels: ['America'],
 *                              },
 *                              directSubHeaders: {
 *                                  3: {
 *                                          root: {
 *                                              values: [2, 3],
 *                                              labels: ['America', 'Washington'],
 *                                          }
 *                                          directSubHeaders: {},
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
 *                      "[[], []]": [{'sales_total': 110}, {'sales_total': 85}]                      (total/total)
 *                      ...
 *                      "[[1, 2], [2]]": [{'sales_total': 0}, {'sales_total': 10}]                   (Europe/Paris/Sale Team 2)
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
     * @param {string} type
     */
    addGroupBy: function (groupBy, type) {
        if (type === 'row') {
            this.data.expandedRowGroupBys.push(groupBy);
        } else {
            this.data.expandedColGroupBys.push(groupBy);
        }
    },
    /**
     * Close the header with id given by headerId.
     *
     * @param {integer} headerId
     */
    closeHeader: function (headerId) {
        const header = this.headers[headerId];
        let groupBys;
        let expandedGroupBys;
        if (this.getHeaderType(headerId) === 'row') {
            groupBys = this.data.rowGroupBys;
            expandedGroupBys = this.data.expandedRowGroupBys;
        } else {
            groupBys = this.data.colGroupBys;
            expandedGroupBys = this.data.expandedColGroupBys;
        }
        header.directSubHeaders.clear();
        delete header.sortedIds;
        const newGroupBysLength = this._getTreeHeight(header.rootId) - 1;
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
     * @param {Object} header
     * @param {string} groupBy
     * @returns {Promise}
     */
    expandHeader: function (header, groupBy) {
        let groupId;
        let leftDivisors;
        let rightDivisors;

        if (this.getHeaderType(header.id) === 'row') {
            groupId = this._getGroupId(header.id, this.colRootId);
            leftDivisors = [[groupBy]];
            rightDivisors = sections(this._getGroupBys().colGroupBys);
        } else {
            groupId = this._getGroupId(header.id, this.rowRootId);
            leftDivisors = sections(this._getGroupBys().rowGroupBys);
            rightDivisors = [[groupBy]];
        }
        const divisors = cartesian(leftDivisors, rightDivisors);

        return this._subdivideGroup(groupId, divisors);
    },
    /**
     * Export model data in a form suitable for an easy encoding of the pivot
     * table in excell.
     *
     * @returns {Object}
     */
    exportData: function () {
        const measureCount = this.data.measures.length;
        const originCount = this.data.origins.length;

        const table = this._getTable();

        // process headers
        const headers = table.headers;
        let colGroupHeaderRows;
        let measureRow = [];
        let originRow = [];

        function processHeader(header) {
            const inTotalColumn = header.id === header.rootId;
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
            if (measureCount > 1) {
                measureRow = headers[headers.length - 1].map(processHeader);
            }
        }

        // remove the empty headers on left side
        colGroupHeaderRows[0].splice(0, 1);

        colGroupHeaderRows = colGroupHeaderRows.map(function (headerRow) {
            return headerRow.map(processHeader);
        });

        // process rows
        const tableRows = table.rows.map(function (row) {
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

        let temp = this.rowRootId;
        this.rowRootId = this.colRootId;
        this.colRootId = temp;

        // we need to update the record metadata: (expanded) row and col groupBys
        temp = this.data.rowGroupBys;
        this.data.groupedBy = this.data.colGroupBys;
        this.data.rowGroupBys = this.data.colGroupBys;
        this.data.colGroupBys = temp;
        temp = this.data.expandedColGroupBys;
        this.data.expandedColGroupBys = this.data.expandedRowGroupBys;
        this.data.expandedRowGroupBys = temp;
    },
    /**
     * @override
     *
     * @param {Object} [options]
     * @param {boolean} [options.raw=false]
     * @returns {Object}
     */
    get: function (options) {
        options = options || {};
        var raw = options.raw || false;
        var groupBys = this._getGroupBys();
        var state = {
            colGroupBys: groupBys.colGroupBys,
            context: this.data.context,
            domain: this.data.domain,
            fields: this.fields,
            hasData: this._hasData(),
            measures: this.data.measures,
            origins: this.data.origins,
            rowGroupBys: groupBys.rowGroupBys,
        };
        if (!raw && state.hasData) {
            state.table = this._getTable();
        }
        return state;
    },
    /**
     * Returns the header with id giben by headerId
     *
     * @param {integer} headerId
     * @returns {Object}
     */
    getHeader: function (headerId) {
        return this.headers[headerId];
    },
    /**
     * Returns the type of the header with id given by headerId.
     *
     * @param  {integer} headerId
     * @return {string}
     */
    getHeaderType: function (headerId) {
        const header = this.headers[headerId];
        return header.rootId === this.rowRootId ? 'row' : 'col';
    },
    /**
     * Returns the total number of columns of the pivot table.
     *
     * @returns {integer}
     */
    getTableWidth: function () {
        const leafCounts = this._getLeafCounts(this.headers[this.colRootId]);
        return leafCounts[this.colRootId] + 2;
    },
    /**
     * @override
     *
     * @param {Object} params
     * @param {boolean} [params.compare=false]
     * @param {Object} params.context
     * @param {Object} params.fields
     * @param {Array[]} [params.comparisonTimeRange=[]]
     * @param {string[]} [params.groupedBy]
     * @param {Array[]} [params.timeRange=[]]
     * @param {string[]} params.colGroupBys
     * @param {Array[]} params.domain
     * @param {string[]} params.measures
     * @param {string[]} params.rowGroupBys
     * @param {string} [params.comparisonTimeRangeDescription=""]
     * @param {string} [params.default_order]
     * @param {string} [params.timeRangeDescription=""]
     * @param {string} params.modelName
     * @returns {Promise}
     */
    load: function (params) {
        this.initialDomain = params.domain;
        this.initialRowGroupBys = params.context.pivot_row_groupby || params.rowGroupBys;
        this.defaultGroupedBy = params.groupedBy;

        this.fields = params.fields;
        this.modelName = params.modelName;
        this.data = {
            expandedRowGroupBys: [],
            expandedColGroupBys: [],
            domain: this.initialDomain,
            timeRange: params.timeRange || [],
            timeRangeDescription: params.timeRangeDescription || "",
            comparisonTimeRange: params.comparisonTimeRange || [],
            comparisonTimeRangeDescription: params.comparisonTimeRangeDescription || "",
            compare: params.compare || false,
            context: _.extend({}, session.user_context, params.context),
            groupedBy: params.context.pivot_row_groupby || params.groupedBy,
            colGroupBys: params.context.pivot_column_groupby || params.colGroupBys,
            measures: this._processMeasures(params.context.pivot_measures) || params.measures,
        };

        this.data.domains = this._getDomains();
        this.data.origins = this._getOrigins();
        this.data.rowGroupBys = !_.isEmpty(this.data.groupedBy) ? this.data.groupedBy : this.initialRowGroupBys;

        var defaultOrder = params.default_order && params.default_order.split(' ');
        if (defaultOrder) {
            this.data.sortedColumn = {
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
     * @param {Array[]} [params.comparisonTimeRange=[]]
     * @param {string[]} [params.groupedBy]
     * @param {Array[]} [params.timeRange=[]]
     * @param {Array[]} params.domain
     * @param {string[]} params.groupBy
     * @param {string[]} params.measures
     * @param {string} [params.comparisonTimeRangeDescription=""]
     * @param {string} [params.timeRangeDescription=""]
     * @returns {Promise}
     */
    reload: function (handle, params) {
        var self = this;
        var oldColGroupBys = this.data.colGroupBys;
        var oldRowGroupBys = this.data.rowGroupBys;
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
            this.initialDomain = params.domain;
        } else {
            this.data.domain = this.initialDomain;
        }
        if ('groupBy' in params) {
            this.data.groupedBy = params.groupBy.length ? params.groupBy : this.defaultGroupedBy;
        }

        this.data.domains = this._getDomains();
        this.data.origins = this._getOrigins();
        this.data.rowGroupBys = !_.isEmpty(this.data.groupedBy) ? this.data.groupedBy : this.initialRowGroupBys;

        if (!_.isEqual(oldRowGroupBys, self.data.rowGroupBys)) {
            this.data.expandedRowGroupBys = [];
        }
        if (!_.isEqual(oldColGroupBys, self.data.colGroupBys)) {
            this.data.expandedColGroupBys = [];
        }
        if (!this._hasData()) {
            return this._loadData();
        }
        const oldHeaders = this.headers;
        const oldRowRootId = this.rowRootId;
        const oldColRootId = this.colRootId;
        return this._loadData().then(function () {
            if (_.isEqual(oldRowGroupBys, self.data.rowGroupBys)) {
                self._pruneSubHeaderTree(self.headers[self.rowRootId], oldHeaders[oldRowRootId], oldHeaders);
            }
            if (_.isEqual(oldColGroupBys, self.data.colGroupBys)) {
                self._pruneSubHeaderTree(self.headers[self.colRootId], oldHeaders[oldColRootId], oldHeaders);
            }
        });
    },
    /**
     * Sort the rows, depending on the values of a given column.  This is an
     * in-memory sort.
     *
     * @param {Object} sortedColumn
     */
    sortRows: function (sortedColumn) {
        const self = this;
        const colHeaderId = sortedColumn.headerId || this.colRootId;
        sortedColumn.headerId = colHeaderId;
        sortedColumn.originIndexes = sortedColumn.originIndexes || [0];
        this.data.sortedColumn = sortedColumn;

        function _sortFunction (subHeaderId) {
            const subHeader = self.headers[subHeaderId];
            const groupId = self._getGroupId(subHeader.id, colHeaderId);
            const value = self._getCellValue(
                groupId,
                sortedColumn.measure,
                sortedColumn.originIndexes
            ) || 0;
            return sortedColumn.order === 'asc' ? value : -value;
        }

        function _sortSubHeaders (header) {
            header.sortedIds = _.sortBy([...header.directSubHeaders.values()], _sortFunction);
            header.directSubHeaders.forEach(function (headerId) {
                _sortSubHeaders(self.headers[headerId]);
            });
        }

        _sortSubHeaders(this.headers[this.rowRootId]);
    },
    /**
     * Toggle the active state for a given measure, then reload the data
     * if this turns out to be necessary.
     *
     * @param {string} fieldName
     * @returns {Promise}
     */
    toggleMeasure: function (fieldName) {
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a header corresponding to values/labels (if it does not
     * already exists).
     *
     * @private
     * @param {integer} rootId, either this.rowRootId or this.colRootId;
     * @param {Array} values
     * @param {string[]} labels
     */
    _addHeader: function (rootId, values, labels) {
        const parentHeaderId = this._findHeaderId(rootId, values.slice(0, values.length - 1));
        const parentHeader = this.headers[parentHeaderId];
        let headerId = parentHeader.directSubHeaders.get(values[values.length - 1]);
        if (headerId) {
            // TO DO: remove this part
            console.log('already there!');
        } else {
            headerId = this._makeHeader({ rootId, values, labels });
            parentHeader.directSubHeaders.set(values[values.length - 1], headerId);
        }
        return headerId;
    },
    /**
     * Remove from this.headers all sub headers of a header with id headerId.
     * @param  {integer} headerId
     */
    _deleteSubHeaders: function (headerId) {
        const header = this.headers[headerId];
        header.directSubHeaders.forEach(subHeaderId => {
            this._deleteSubHeaders(subHeaderId);
        });
        delete this.headers[headerId];
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
     * Returns the id of a header with given values and root given by rootId
     * (this.rowRootId or this.colRootId). If it does not exists returns 0.
     *
     * @private
     * @param  {integer} rootId
     * @param  {Array} values
     * @returns {integer}
     */
    _findHeaderId: function (rootId, values) {
        if (!values.length) {
            return rootId;
        }
        const parentHeaderId = this._findHeaderId(rootId, values.slice(0, values.length -1));
        if (!parentHeaderId) {
            return 0;
        }
        const parentHeader = this.headers[parentHeaderId];
        const headerId = parentHeader.directSubHeaders.get(values[values.length -1]);
        if (!headerId) {
            return 0;
        }
        return headerId;
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
     * @param  {integer} groupId
     * @param  {string} measure
     * @param  {integer[]} originIndexes
     * @returns {number}
     */
    _getCellValue: function (groupId, measure, originIndexes) {
        const group = this.groups[groupId];
        if (!group) {
            return;
        }
        var values = originIndexes.map(originIndex => {
            return group.measurements[originIndex][measure];
        });
        if (originIndexes.length > 1) {
            return computeVariation(values[0], values[1]);
        } else {
            return values[0];
        }
    },
    /**
     * Returns the principal domains used by the pivot model to fetch data.
     * The domains represent two main groups of records.
     *
     * @private
     * @returns {Array[][]}
     */
    _getDomains: function () {
        var domains = [this.data.domain.concat(this.data.timeRange)];
        if (this.data.compare) {
            domains.push(this.data.domain.concat(this.data.comparisonTimeRange));
        }
        return domains;
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
     * @param  {integer} groupId
     * @param  {interger} originIndex
     * @returns {Array[]}
     */
    _getGroupDomain: function (groupId, originIndex) {
        const group = this.groups[groupId];
        return group.domains[originIndex];
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
     * Returns a groupId for a given pair or header ids.
     * @param  {...[integer]} ids
     * @return {integer}
     */
    _getGroupId: function (...ids) {
        const [id1, id2] = ids.sort();
        const groupId = this._mapToGroupId[id1] && this._mapToGroupId[id1][id2];
        if (groupId) {
            return groupId;
        }
        this._lastGroupId++;
        this._mapToGroupId[id1] = this._mapToGroupId[id1] || {};
        this._mapToGroupId[id1][id2] = this._lastGroupId;
        this._mapFromGroupId[this._lastGroupId] = new Set([id1, id2]);
        return this._lastGroupId;
    },
    /**
     * Returns a promise that returns the annotated read_group results
     * corresponding to a partition of the given group obtained using the given
     * rowGroupBy and colGroupBy.
     *
     * @private
     * @param  {integer} groupId
     * @param {integer} originIndex
     * @param  {string[]} rowGroupBy
     * @param  {string[]} colGroupBy
     * @returns {Promise}
     */
    _getGroupSubdivision: function (groupId, originIndex, rowGroupBy, colGroupBy) {
        var groupDomain = this._getGroupDomain(groupId, originIndex);
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
                groupId: groupId,
                originIndex: originIndex,
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
     * Returns the headers corresponding to a group with id groupId
     * @param  {integer} groupId
     * @return {Object}
     */
    _getGroupHeaders: function (groupId) {
        const headerIds = this._mapFromGroupId[groupId];
        const headers = {};
        headerIds.forEach(headerId => {
            const header = this.headers[headerId];
            if (header.rootId === this.rowRootId) {
                headers.rowHeader = header;
            } else {
                headers.colHeader = header;
            }
        });
        return headers;
    },
    /**
     * Each header determines a tree by taking its sub headers.
     * Returns the leaf counts of each sub header tree inside the tree determined
     * by the given header.
     *
     * @private
     * @param {Object} header
     * @returns {Object} keys are header ids
     */
    _getLeafCounts: function (header) {
        const self = this;
        const leafCounts = {};
        let leafCount;
        if (!header.directSubHeaders.size) {
            leafCount = 1;
        } else {
            leafCount = [...header.directSubHeaders.values()].reduce(
                function (acc, subHeaderId) {
                    const subHeader = self.headers[subHeaderId];
                    var subLeafCounts = self._getLeafCounts(subHeader);
                    _.extend(leafCounts, subLeafCounts);
                    return acc + leafCounts[subHeaderId];
                },
                0
            );
        }

        leafCounts[header.id] = leafCount;
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
        const self = this;
        const sortedColumn = this.data.sortedColumn || {};
        const measureRow = [];

        columns.forEach(function (column) {
            self.data.measures.forEach(function (measure) {
                const measureCell = {
                    headerId: column.headerId,
                    height: 1,
                    measure: measure,
                    title: self.fields[measure].string,
                    width: 2 * self.data.origins.length - 1,
                };
                if (sortedColumn.measure === measure &&
                    _.isEqual(sortedColumn.headerId, column.headerId)) {
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
     * Returns a new Id used to identify a (row or col) header.
     * @return {integer}
     */
    _getNewHeaderId: function () {
        this._lastHeaderId++;
        return this._lastHeaderId;
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
        const self = this;
        const sortedColumn = this.data.sortedColumn || {};
        const originRow = [];

        columns.forEach(function (column) {
            const headerId = column.headerId;
            const measure = column.measure;
            const isSorted = sortedColumn.measure === measure &&
                           _.isEqual(sortedColumn.headerId, headerId);
            const isSortedByOrigin = isSorted && !sortedColumn.originIndexes[1];
            const isSortedByVariation = isSorted && sortedColumn.originIndexes[1];

            self.data.origins.forEach(function (origin, originIndex) {
                const originCell = {
                    headerId: headerId,
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
                    const variationCell = {
                        headerId: headerId,
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
     * Create an array with the origin descriptions.
     *
     * @private
     * @returns {string[]}
     */
    _getOrigins: function () {
        var origins = [this.data.timeRangeDescription || ""];
        if (this.data.compare) {
            origins.push(this.data.comparisonTimeRangeDescription);
        }
        return origins;
    },
    /**
     * Returns a description of the pivot table.
     *
     * @private
     * @returns {Object}
     */
    _getTable: function () {
        const headers = this._getTableHeaders();
        return {
            headers: headers,
            rows: this._getTableRows(this.headers[this.rowRootId], headers[headers.length - 1]),
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
        const self = this;
        const colGroupBys = this._getGroupBys().colGroupBys;
        const height = colGroupBys.length + 1;
        const measureCount = this.data.measures.length;
        const originCount = this.data.origins.length;
        const leafCounts = this._getLeafCounts(this.headers[this.colRootId]);
        let headers = [];
        const measureColumns = []; // used to generate the measure cells

        // 1) generate col group rows (total row + one row for each col groupby)
        const colGroupRows = (new Array(height)).fill(0).map(function () {
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
         * @param {Object} headerId
         */
        function generateTreeHeaders(headerId) {
            const header = self.headers[headerId];
            const rowIndex = header.values.length;
            const row = colGroupRows[rowIndex];
            const isLeaf = !header.directSubHeaders.size;
            const leafCount = leafCounts[header.id];
            const cell = {
                headerId: headerId,
                height: isLeaf ? (colGroupBys.length + 1 - rowIndex) : 1,
                isLeaf: isLeaf,
                title: header.labels[header.labels.length - 1] || _t('Total'),
                width: leafCount * measureCount * (2 * originCount - 1),
            };
            row.push(cell);
            if (isLeaf) {
                measureColumns.push(cell);
            }
            header.directSubHeaders.forEach(function (headerId) {
                generateTreeHeaders(headerId);
            });
        }
        generateTreeHeaders(this.colRootId);
        // blank top right cell for 'Total' group (if there is more that one leaf)
        if (leafCounts[this.colRootId] > 1) {
            const totalTopRightCell = {
                headerId: this.colRootId,
                height: height,
                title: "",
                width: measureCount * (2 * originCount - 1),
            };
            colGroupRows[0].push(totalTopRightCell);
            measureColumns.push(totalTopRightCell);
        }
        headers = headers.concat(colGroupRows);

        // 2) generate measures row
        const measuresRow = this._getMeasuresRow(measureColumns)
        headers.push(measuresRow);

        // 3) generate origins row if more than one origin
        if (originCount > 1) {
            headers.push(this._getOriginsRow(measuresRow));
        }

        return headers;
    },
    /**
     * Returns the list of body rows of the pivot table for a given header tree.
     *
     * @private
     * @param {Object} header
     * @param {Object[]} columns
     * @returns {Object[]}
     */
    _getTableRows: function (header, columns) {
        const self = this;

        let rows = [];
        const rowHeaderId = header.id;
        const title = header.labels[header.labels.length - 1] || _t('Total');
        const indent = header.labels.length;
        const isLeaf = !header.directSubHeaders.size;

        const subGroupMeasurements = columns.map(function (column) {
            const colHeaderId = column.headerId;
            const groupId = self._getGroupId(rowHeaderId, colHeaderId);
            const measure = column.measure;
            const originIndexes = column.originIndexes || [0];

            const value = self._getCellValue(groupId, measure, originIndexes);

            const measurement = {
                groupId: groupId,
                originIndexes: originIndexes,
                measure: measure,
                value: value,
                isBold: rowHeaderId !== self.rowRootId || colHeaderId !== self.colRootId,
            };
            return measurement;
        });

        rows.push({
            title: title,
            headerId: rowHeaderId,
            indent: indent,
            isLeaf: isLeaf,
            subGroupMeasurements: subGroupMeasurements
        });

        const subHeaderIds = header.sortedIds || [...header.directSubHeaders.values()];
        subHeaderIds.forEach(function (subHeaderId) {
            const subHeader = self.headers[subHeaderId];
            rows = rows.concat(self._getTableRows(subHeader, columns));
        });

        return rows;
    },
    /**
     * Returns the height of a given header tree
     *
     * @private
     * @param  {integer} headerId
     * @returns {integer}
     */
    _getTreeHeight: function (headerId) {
        const header = this.headers[headerId];
        var subTreeHeights = [...header.directSubHeaders.values()].map(this._getTreeHeight.bind(this));
        return Math.max(0, Math.max.apply(null, subTreeHeights)) + 1;
    },
    /**
     * @private
     * @returns {boolean}
     */
    _hasData: function () {
        const totalGroup = this.groups[this._getGroupId(this.rowRootId, this.colRootId)];
        return totalGroup.counts.some(count =>  count > 0);
    },
    /**
     * Initilize/Reinitialize this.headers, this.groups,
     * this.rowRootId, this.colRootId and other private variables.
     *
     * Subdivide the group 'Total' as many times it is necessary.
     *
     * A first subdivision with no groupBy (divisors.slice(0, 1)) is made in
     * order to see if there is data in the intersection of the group 'Total'
     * and the various origins. In case there is none, nonsupplementary rpc
     * will be done (see the code of subdivideGroup).
     * Once the promise resolves, this.headers, this.groups are correctly set.
     *
     * @private
     * @return {Promise}
     */
    _loadData: function () {
        const self = this;
        // initialize id machinery
        this._lastHeaderId = 0;
        this._lastGroupId = 0;
        this._mapToGroupId = {};
        this._mapFromGroupId = {};

        this.headers = {};
        this.rowRootId = this._makeHeader();
        this.colRootId = this._makeHeader();

        this.groups = {};
        const groupId = this._getGroupId(this.rowRootId, this.colRootId);
        const domains = this.data.domains.slice(0);
        // We do not have information on the total count of records.
        // So we set counts to Infinity at start (starting value needs to be
        // greater than 0).
        const counts = this.data.origins.map(() => Infinity);
        this._makeGroup(groupId, { domains, counts });

        const groupBys = this._getGroupBys();
        const leftDivisors = sections(groupBys.rowGroupBys);
        const rightDivisors = sections(groupBys.colGroupBys);
        const divisors = cartesian(leftDivisors, rightDivisors);

        return this._subdivideGroup(groupId, divisors.slice(0, 1)).then(function () {
            return self._subdivideGroup(groupId, divisors.slice(1));
        });
    },
    /**
     * Create a group and add it to this.groups. Returns the newly
     * created group.
     *
     * @param  {integer} groupId
     * @param  {Object[]} [options.measurements]
     * @param  {integer[]} [options.counts]
     * @param  {Array[]} [options.domains]
     * @return {Object}
     */
    _makeGroup: function (groupId, { measurements, counts, domains } = {}) {
        const group = {
            id: groupId,
            measurements: measurements || this.data.origins.map(() => this._getMeasurements({})),
            counts: counts || this.data.origins.map(() => 0),
            domains: domains || this.data.origins.map(() => [[0, '=', 1]]),
        };
        this.groups[groupId] = group;
        return group;
    },
    /**
     * Create a header and add it to this.headers. Returns the id
     * of the newly created header.
     *
     * @param  {integer} options.rootId
     * @param  {Array} options.values
     * @param  {string[]} options.labels
     * @return {integer}
     */
    _makeHeader: function ({rootId, values, labels} = {}) {
        const headerId = this._getNewHeaderId();
        this.headers[headerId] = {
            id: headerId,
            rootId: rootId || headerId,
            labels: labels || [],
            values: values || [],
            directSubHeaders: new Map(),
        };
        return headerId;
    },
    /**
     * Extract the information in the read_group results (groupSubdivisions)
     * and develop this.headers, colGroupTree, measurements, counts, and
     * groupDomains.
     * If a column needs to be sorted, the headers corresponding to the
     * group is sorted.
     *
     * @private
     * @param  {number} groupId
     * @param  {Object[]} groupSubdivisions
     */
    _prepareData: function (groupId, groupSubdivisions) {
        const self = this;
        const headers = this._getGroupHeaders(groupId);
        const groupRowValues = headers.rowHeader.values;
        const groupRowLabels = headers.rowHeader.labels;
        const groupColValues = headers.colHeader.values
        const groupColLabels = headers.colHeader.labels;

        groupSubdivisions.forEach(function (groupSubdivision) {
            groupSubdivision.subGroups.forEach(function (subGroup) {

                const rowValues = groupRowValues.concat(self._getGroupValues(subGroup, groupSubdivision.rowGroupBy));
                const rowLabels = groupRowLabels.concat(self._getGroupLabels(subGroup, groupSubdivision.rowGroupBy));

                const colValues = groupColValues.concat(self._getGroupValues(subGroup, groupSubdivision.colGroupBy));
                const colLabels = groupColLabels.concat(self._getGroupLabels(subGroup, groupSubdivision.colGroupBy));

                let rowHeaderId;
                let colHeaderId;

                if (!colValues.length && rowValues.length) {
                    // here the subgroup corresponds to a row header
                    rowHeaderId = self._addHeader(self.rowRootId, rowValues, rowLabels);
                    colHeaderId = self.colRootId;
                } else if (colValues.length && !rowValues.length) {
                    // here the subgroup corresponds to a col header
                    rowHeaderId = self.rowRootId;
                    colHeaderId = self._addHeader(self.colRootId, colValues, colLabels);
                } else {
                    rowHeaderId = self._findHeaderId(self.rowRootId, rowValues);
                    colHeaderId = self._findHeaderId(self.colRootId, colValues);
                }
                if (rowHeaderId * colHeaderId === 0) {
                    // the subgroup must not be present in the table since its supposed headers are
                    // not expanded
                    return;
                }

                const subGroupId = self._getGroupId(rowHeaderId, colHeaderId);
                let g = self.groups[subGroupId];
                if (!g) {
                    g = self._makeGroup(subGroupId);
                }

                const originIndex = groupSubdivision.originIndex;

                g.measurements[originIndex] = self._getMeasurements(subGroup);
                g.counts[originIndex] = subGroup.__count;
                // if __domain is not defined this means that we are in the
                // case where
                // groupSubdivision.rowGroupBy = groupSubdivision.rowGroupBy = []
                if (subGroup.__domain) {
                    g.domains[originIndex] = subGroup.__domain;
                }
            });
        });

        if (this.data.sortedColumn) {
            this.sortRows(this.data.sortedColumn);
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
     * Make any group in tree a leaf if it was a leaf in oldTree.
     *
     * @private
     * @param {Object} header
     * @param {Object} oldHeaders
     */
    _pruneSubHeaderTree: function (header, oldHeader, oldHeaders) {
        if (!oldHeader.directSubHeaders.size) {
            header.directSubHeaders.forEach(subHeaderId => {
                this._deleteSubHeaders(subHeaderId);
            })
            header.directSubHeaders.clear();
            delete header.sortedIds;
            return;
        }
        var self = this;
        header.directSubHeaders.forEach(function (subHeaderId, key) {
            const oldId = oldHeader.directSubHeaders.get(key);
            if (!oldId) {
                self._deleteSubHeaders(subHeaderId);
                header.directSubHeaders.delete(key);
            } else {
                const subHeader = self.headers[subHeaderId];
                const oldSubHeader = oldHeaders[oldId];
                self._pruneSubHeaderTree(subHeader, oldSubHeader, oldHeaders);
            }
        });
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
            var selected = _.where(this.fields[fieldName].selection, {0: value})[0];
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
     * and enrich the objects of this.headers, colGroupTree,
     * measurements, counts.
     *
     * @private
     * @param {number} groupId
     * @param {Array[]} divisors
     * @returns
     */
    _subdivideGroup: function (groupId, divisors) {
        var self = this;
        const group = this.groups[groupId]

        var proms = this.data.origins.reduce(
            function (acc, origin, originIndex) {
                // if no information on group content is available, we fetch data.
                // if group is known to be empty for the given origin,
                // we don't need to fetch data fot that origin.
                if (group.counts[originIndex] > 0) {
                    divisors.forEach(function (divisor) {
                        acc.push(self._getGroupSubdivision(groupId, originIndex, divisor[0], divisor[1]));
                    });
                }
                return acc;
            },
            []
        );
        return this._loadDataDropPrevious.add(Promise.all(proms)).then(function (groupSubdivisions) {
            if (groupSubdivisions.length) {
                self._prepareData(groupId, groupSubdivisions);
            }
        });
    },
});

return PivotModel;

});
