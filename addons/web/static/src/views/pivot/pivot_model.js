/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { cartesian, sections, sortBy, symmetricalDifference } from "@web/core/utils/arrays";
import { KeepLast } from "@web/core/utils/concurrency";
import { computeVariation } from "@web/core/utils/numbers";
import { DEFAULT_INTERVAL } from "@web/search/utils/dates";
import { Model } from "@web/views/helpers/model";
import { buildSampleORM } from "@web/views/helpers/sample_server";
import { computeReportMeasures, processMeasure } from "@web/views/helpers/utils";

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
 *      Each time a rendering or an export of the data has to be done, the pivot table is generated by the getTable function.
 */

/**
 * @typedef Meta
 * @property {Object} meta
 * @property {string[]} activeMeasures
 * @property {string[]} colGroupBys
 * @property {boolean} disableLinking
 * @property {Object} fields
 * @property {Object} measures
 * @property {string} resModel
 * @property {string[]} rowGroupBys
 * @property {string} title
 * @property {boolean} useSampleModel
 * @property {Object} widgets
 * @property {Map} customGroupBys
 * @property {string[]} expandedRowGroupBys
 * @property {string[]} expandedColGroupBys
 * @property {Object} sortedColumn
 */

/**
 * @typedef Data
 * @property {Object} colGroupTree
 * @property {Object} rowGroupTree
 * @property {Object} groupDomains
 * @property {Object} measurements
 * @property {Object} counts
 * @property {Object} numbering
 */

/**
 * @typedef SearchParams
 * @property {Array[]} domain
 * @property {Object} context
 * @property {string[]} groupBy
 * @property {Array[]} domains
 * @property {string[]} origins
 */

/**
 * @typedef Config
 * @property {Meta} meta
 * @property {Data} data
 * @property {SearchParams} searchParams
 */

export class PivotModel extends Model {
    /**
     * @override
     * @param {Object} params.meta
     * @param {string[]} params.meta.activeMeasures
     * @param {string[]} params.meta.colGroupBys
     * @param {Object} params.meta.fields
     * @param {Object[]} params.meta.measures
     * @param {string} params.meta.resModel
     * @param {string[]} params.meta.rowGroupBys
     * @param {string|null} params.meta.defaultOrder
     * @param {boolean} params.meta.disableLinking
     * @param {boolean} params.meta.useSampleModel
     * @param {Map} [params.meta.customGroupBys={}]
     * @param {string[]} [params.meta.expandedColGroupBys=[]]
     * @param {string[]} [params.meta.expandedRowGroupBys=[]]
     * @param {Object|null} [params.meta.sortedColumn=null]
     * @param {Object} [params.data] previously exported data
     */
    setup(params, { orm, user }) {
        this.realORM = orm;
        this.orm2Use = this.realORM;
        this.user = user;
        this.keepLast = new KeepLast();

        let sortedColumn = params.meta.sortedColumn || null;
        if (!sortedColumn && params.meta.defaultOrder) {
            const defaultOrder = params.meta.defaultOrder.split(" ");
            sortedColumn = {
                groupId: [[], []],
                measure: defaultOrder[0],
                order: defaultOrder[1] ? defaultOrder[1] : "asc",
            };
        }

        const meta = Object.assign({}, params.meta, {
            customGroupBys: params.meta.customGroupBys || new Map(),
            expandedRowGroupBys: params.meta.expandedRowGroupBys || [],
            expandedColGroupBys: params.meta.expandedColGroupBys || [],
            sortedColumn,
        });
        this.meta = this._buildMeta(meta);

        this.data = params.data || {
            colGroupTree: null,
            rowGroupTree: null,
            groupDomains: {},
            measurements: {},
            counts: {},
            numbering: {},
        };

        this.searchParams = {
            context: {},
            domain: [],
            groupBy: [],

            domains: null, // not the same as searchParams.domains from cp
            origins: null, // generated from searchParams.domains from cp
        };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a groupBy to rowGroupBys or colGroupBys according to provided type.
     *
     * @param {Object} params
     * @param {Array[]} params.groupId
     * @param {string} params.fieldName
     * @param {'row'|'col'} params.type
     * @param {boolean} [params.custom=false]
     * @param {string} [params.interval]
     */
    async addGroupBy(params) {
        const { groupId, fieldName, type, custom } = params;
        let { interval } = params;
        const meta = this._buildMeta();
        if (custom && !meta.customGroupBys.has(fieldName)) {
            const field = meta.fields[fieldName];
            if (!interval && ["date", "datetime"].includes(field.type)) {
                interval = DEFAULT_INTERVAL;
            }
            meta.customGroupBys.set(fieldName, {
                ...field,
                id: fieldName,
            });
        }

        let groupBy = fieldName;
        if (interval) {
            groupBy = `${groupBy}:${interval}`;
        }
        if (type === "row") {
            meta.expandedRowGroupBys.push(groupBy);
        } else {
            meta.expandedColGroupBys.push(groupBy);
        }
        const config = { meta, data: this.data, searchParams: this.searchParams };
        await this._expandGroup(groupId, type, config);
        this.meta = meta;
        this.notify();
    }
    /**
     * Close the group with id given by groupId. A type must be specified
     * in case groupId is [[], []] (the id of the group 'Total') because this
     * group is present in both colGroupTree and rowGroupTree.
     *
     * @param {Array[]} groupId
     * @param {'row'|'col'} type
     */
    closeGroup(groupId, type) {
        this._cancelPreviousOperation();
        let groupBys;
        let expandedGroupBys;
        let keyPart;
        let group;
        let tree;
        if (type === "row") {
            groupBys = this.meta.rowGroupBys;
            expandedGroupBys = this.meta.expandedRowGroupBys;
            tree = this.data.rowGroupTree;
            group = this._findGroup(this.data.rowGroupTree, groupId[0]);
            keyPart = 0;
        } else {
            groupBys = this.meta.colGroupBys;
            expandedGroupBys = this.meta.expandedColGroupBys;
            tree = this.data.colGroupTree;
            group = this._findGroup(this.data.colGroupTree, groupId[1]);
            keyPart = 1;
        }

        const groupIdPart = groupId[keyPart];
        const range = groupIdPart.map((_, index) => index);
        function keep(key) {
            const idPart = JSON.parse(key)[keyPart];
            return (
                range.some((index) => groupIdPart[index] !== idPart[index]) ||
                idPart.length === groupIdPart.length
            );
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
        this.data.measurements = omitKeys(this.data.measurements);
        this.data.counts = omitKeys(this.data.counts);
        this.data.groupDomains = omitKeys(this.data.groupDomains);

        group.directSubTrees.clear();
        delete group.sortedKeys;
        var newGroupBysLength = this._getTreeHeight(tree) - 1;
        if (newGroupBysLength <= groupBys.length) {
            expandedGroupBys.splice(0);
            groupBys.splice(newGroupBysLength);
        } else {
            expandedGroupBys.splice(newGroupBysLength - groupBys.length);
        }
        this.notify();
    }
    /**
     * Reload the view with the current rowGroupBys and colGroupBys
     * This is the easiest way to expand all the groups that are not expanded
     */
    async expandAll() {
        const config = { meta: this.meta, data: this.data, searchParams: this.searchParams };
        this.data = await this._loadData(config);
        this.notify();
    }
    /**
     * Expand a group by using groupBy to split it and trigger a re-rendering.
     *
     * @param {Object} group
     * @param {'row'|'col'} type
     */
    async expandGroup(groupId, type) {
        const config = { meta: this.meta, data: this.data, searchParams: this.searchParams };
        await this._expandGroup(groupId, type, config);
        this.notify();
    }
    /**
     * Export model data in a form suitable for an easy encoding of the pivot
     * table in excell.
     *
     * @returns {Object}
     */
    exportData() {
        const measureCount = this.meta.activeMeasures.length;
        const originCount = this.searchParams.origins.length;

        const table = this.getTable();

        // process headers
        const headers = table.headers;
        let colGroupHeaderRows;
        let measureRow = [];
        let originRow = [];

        function processHeader(header) {
            const inTotalColumn = header.groupId[1].length === 0;
            return {
                title: header.title,
                width: header.width,
                height: header.height,
                is_bold: !!header.measure && inTotalColumn,
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

        colGroupHeaderRows = colGroupHeaderRows.map((headerRow) => {
            return headerRow.map(processHeader);
        });

        // process rows
        const tableRows = table.rows.map((row) => {
            return {
                title: row.title,
                indent: row.indent,
                values: row.subGroupMeasurements.map((measurement) => {
                    let value = measurement.value;
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
            model: this.meta.resModel,
            title: this.meta.title,
            col_group_headers: colGroupHeaderRows,
            measure_headers: measureRow,
            origin_headers: originRow,
            rows: tableRows,
            measure_count: measureCount,
            origin_count: originCount,
        };
    }
    /**
     * Swap the pivot columns and the rows. It is a synchronous operation.
     */
    flip() {
        this._cancelPreviousOperation();

        // swap the data: the main column and the main row
        let temp = this.data.rowGroupTree;
        this.data.rowGroupTree = this.data.colGroupTree;
        this.data.colGroupTree = temp;

        // we need to update the record metadata: (expanded) row and col groupBys
        temp = this.meta.rowGroupBys;
        this.meta.rowGroupBys = this.meta.colGroupBys;
        this.meta.colGroupBys = temp;
        temp = this.meta.expandedColGroupBys;
        this.meta.expandedColGroupBys = this.meta.expandedRowGroupBys;
        this.meta.expandedRowGroupBys = temp;

        function twistKey(key) {
            return JSON.stringify(JSON.parse(key).reverse());
        }

        function twist(object) {
            const newObject = {};
            Object.keys(object).forEach((key) => {
                const value = object[key];
                newObject[twistKey(key)] = value;
            });
            return newObject;
        }

        this.data.measurements = twist(this.data.measurements);
        this.data.counts = twist(this.data.counts);
        this.data.groupDomains = twist(this.data.groupDomains);

        this.notify();
    }
    /**
     * Returns a domain representation of a group
     *
     * @param {Object} group
     * @param {Array} group.colValues
     * @param {Array} group.rowValues
     * @param {number} group.originIndex
     * @returns {Array[]}
     */
    getGroupDomain(group) {
        const config = { meta: this.meta, data: this.data, searchParams: this.searchParams };
        return this._getGroupDomain(group, config);
    }
    /**
     * Returns a description of the pivot table.
     *
     * @returns {Object}
     */
    getTable() {
        const headers = this._getTableHeaders();
        return {
            headers: headers,
            rows: this._getTableRows(this.data.rowGroupTree, headers[headers.length - 1]),
        };
    }
    /**
     * Returns the total number of columns of the pivot table.
     *
     * @returns {integer}
     */
    getTableWidth() {
        var leafCounts = this._getLeafCounts(this.data.colGroupTree);
        return leafCounts[JSON.stringify(this.data.colGroupTree.root.values)] + 2;
    }
    /**
     * @returns {boolean} true iff there's no data in the table
     */
    hasData() {
        const config = { meta: this.meta, data: this.data, searchParams: this.searchParams };
        return this._hasData(config);
    }
    /**
     * @override
     *
     * @param {Object} searchParams
     * @param {Object} params.context
     * @param {Array[]} params.domain
     * @param {string[]} params.groupBy
     * @param {string[]} params.measures
     * @param {Object} [params.domains]
     */
    async load(searchParams) {
        this.orm2Use = this.realORM;
        searchParams = JSON.parse(JSON.stringify(searchParams)); //This to prevent errors in the Dashboard

        const activeMeasures =
            processMeasure(searchParams.context.pivot_measures) || this.meta.activeMeasures;
        const meta = this._buildMeta({ activeMeasures });
        if (!this.reload) {
            meta.rowGroupBys =
                searchParams.context.pivot_row_groupby ||
                (searchParams.groupBy.length ? searchParams.groupBy : meta.rowGroupBys);
            this.reload = true;
        } else {
            meta.rowGroupBys = searchParams.groupBy.length
                ? searchParams.groupBy
                : searchParams.context.pivot_row_groupby || meta.rowGroupBys;
        }
        meta.colGroupBys = searchParams.context.pivot_column_groupby || this.meta.colGroupBys;

        const { domains, origins } = this._computeDerivedParams(searchParams);
        searchParams.domains = domains;
        searchParams.origins = origins;

        if (JSON.stringify(meta.rowGroupBys) !== JSON.stringify(this.meta.rowGroupBys)) {
            meta.expandedRowGroupBys = [];
        }
        if (JSON.stringify(meta.colGroupBys) !== JSON.stringify(this.meta.colGroupBys)) {
            meta.expandedColGroupBys = [];
        }

        meta.measures = computeReportMeasures(
            meta.fields,
            meta.fieldAttrs,
            meta.activeMeasures,
            meta.additionalMeasures
        );
        const config = { meta, data: this.data, searchParams };
        const data = await this._loadData(config);
        const oldConfig = { meta: this.meta, data: this.data, searchParams: this.searchParams };
        if (this._hasData(oldConfig)) {
            if (symmetricalDifference(meta.rowGroupBys, this.meta.rowGroupBys).length === 0) {
                this._pruneTree(data.rowGroupTree, this.data.rowGroupTree);
            }
            if (symmetricalDifference(meta.colGroupBys, this.meta.colGroupBys).length === 0) {
                this._pruneTree(data.colGroupTree, this.data.colGroupTree);
            }
        }
        this.data = data;
        this.meta = meta;
        this.searchParams = searchParams;
        this.notify();
    }
    /**
     * Sort the rows, depending on the values of a given column.  This is an
     * in-memory sort.
     *
     * @param {Object} sortedColumn
     * @param {number[]} sortedColumn.groupId
     */
    sortRows(sortedColumn) {
        this._cancelPreviousOperation();

        const config = { meta: this.meta, data: this.data, searchParams: this.searchParams };
        this._sortRows(sortedColumn, config);

        this.notify();
    }
    /**
     * Toggle the active state for a given measure, then reload the data
     * if this turns out to be necessary.
     *
     * @param {string} fieldName
     * @returns {Promise}
     */
    async toggleMeasure(fieldName) {
        const meta = this._buildMeta();
        const index = meta.activeMeasures.indexOf(fieldName);
        if (index !== -1) {
            this._cancelPreviousOperation();
            // in this case, we already have all data in memory, no need to
            // actually reload a lesser amount of information
            meta.activeMeasures.splice(index, 1);
        } else {
            meta.activeMeasures.push(fieldName);
            const config = { meta, data: this.data, searchParams: this.searchParams };
            this.data = await this._loadData(config);
        }
        this.meta = meta;
        this.notify();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add labels/values in the provided groupTree. A new leaf is created in
     * the groupTree with a root object corresponding to the group with given
     * labels/values.
     *
     * @private
     * @param {Object} groupTree, either this.data.rowGroupTree or this.data.colGroupTree
     * @param {string[]} labels
     * @param {Array} values
     */
    _addGroup(groupTree, labels, values) {
        let tree = groupTree;
        // we assume here that the group with value value.slice(value.length - 2) has already been added.
        values.slice(0, values.length - 1).forEach(function (value) {
            tree = tree.directSubTrees.get(value);
        });
        tree.directSubTrees.set(values[values.length - 1], {
            root: {
                labels: labels,
                values: values,
            },
            directSubTrees: new Map(),
        });
    }
    /**
     * Return a copy of this.meta, extended with optional params. This is useful
     * for async methods that need to modify this.meta, but it can't be done in
     * place directly for the model to be concurrency proof (so they work on a
     * copy and commit it at the end).
     *
     * @private
     * @param {Object} params
     * @returns {Object}
     */
    _buildMeta(params) {
        const meta = Object.assign({}, this.meta, params);
        meta.activeMeasures = [...meta.activeMeasures];
        meta.colGroupBys = [...meta.colGroupBys];
        meta.rowGroupBys = [...meta.rowGroupBys];
        meta.expandedColGroupBys = [...meta.expandedColGroupBys];
        meta.expandedRowGroupBys = [...meta.expandedRowGroupBys];
        meta.customGroupBys = new Map([...meta.customGroupBys]);
        // shallow copy sortedColumn because we never modify groupId in place
        meta.sortedColumn = meta.sortedColumn ? { ...meta.sortedColumn } : null;
        Object.defineProperty(meta, "fullColGroupBys", {
            get() {
                return meta.colGroupBys.concat(meta.expandedColGroupBys);
            },
        });
        Object.defineProperty(meta, "fullRowGroupBys", {
            get() {
                return meta.rowGroupBys.concat(meta.expandedRowGroupBys);
            },
        });
        return meta;
    }
    /**
     * Used in synchronous operations that need to prevent a possible previous
     * ongoing asynchronous operation that could commit new information leading
     * to a non valid state model.
     */
    _cancelPreviousOperation() {
        this.keepLast.add(Promise.resolve());
    }
    /**
     * Expand a group by using groupBy to split it.
     *
     * @private
     * @param {Object} group
     * @param {'row'|'col'} type
     * @param {Config} config
     */
    async _expandGroup(groupId, type, config) {
        const { meta } = config;
        const group = {
            rowValues: groupId[0],
            colValues: groupId[1],
            type: type,
        };
        const groupValues = type === "row" ? groupId[0] : groupId[1];
        const groupBys = type === "row" ? meta.fullRowGroupBys : meta.fullColGroupBys;
        if (groupValues.length >= groupBys.length) {
            throw new Error("Cannot expand group");
        }
        const groupBy = groupBys[groupValues.length];
        let leftDivisors;
        let rightDivisors;
        if (group.type === "row") {
            leftDivisors = [[groupBy]];
            rightDivisors = sections(meta.fullColGroupBys);
        } else {
            leftDivisors = sections(meta.fullRowGroupBys);
            rightDivisors = [[groupBy]];
        }
        const divisors = cartesian(leftDivisors, rightDivisors);
        delete group.type;
        await this._subdivideGroup(group, divisors, config);
    }
    /**
     * Find a group with given values in the provided groupTree, either
     * this.rowGrouptree or this.data.colGroupTree.
     *
     * @private
     * @param {Object} groupTree
     * @param {Array} values
     * @returns {Object}
     */
    _findGroup(groupTree, values) {
        let tree = groupTree;
        values.slice(0, values.length).forEach((value) => {
            tree = tree.directSubTrees.get(value);
        });
        return tree;
    }
    /**
     * In case originIndex is an array of length 1, thus a single origin
     * index, returns the given measure for a group determined by the id
     * groupId and the origin index.
     * If originIndexes is an array of length 2, we compute the variation
     * ot the measure values for the groups determined by groupId and the
     * different origin indexes.
     *
     * @private
     * @param {Array[]} groupId
     * @param {string} measure
     * @param {number[]} originIndexes
     * @param {Config} config
     * @returns {number}
     */
    _getCellValue(groupId, measure, originIndexes, config) {
        var key = JSON.stringify(groupId);
        if (!config.data.measurements[key]) {
            return;
        }
        var values = originIndexes.map((originIndex) => {
            return config.data.measurements[key][originIndex][measure];
        });
        if (originIndexes.length > 1) {
            return computeVariation(values[1], values[0]);
        } else {
            return values[0];
        }
    }
    /**
     * Returns a domain representation of a group
     *
     * @private
     * @param {Object} group
     * @param {Array} group.colValues
     * @param {Array} group.rowValues
     * @param {number} group.originIndex
     * @param {Config} config
     * @returns {Array[]}
     */
    _getGroupDomain(group, config) {
        const { data } = config;
        var key = JSON.stringify([group.rowValues, group.colValues]);
        return data.groupDomains[key][group.originIndex];
    }
    /**
     * Returns the group sanitized labels.
     *
     * @private
     * @param {Object} group
     * @param {string[]} groupBys
     * @param {Config} config
     * @returns {string[]}
     */
    _getGroupLabels(group, groupBys, config) {
        return groupBys.map((groupBy) => {
            return this._sanitizeLabel(group[groupBy], groupBy, config);
        });
    }
    /**
     * Returns a promise that returns the annotated read_group results
     * corresponding to a partition of the given group obtained using the given
     * rowGroupBy and colGroupBy.
     *
     * @private
     * @param {Object} group
     * @param {string[]} rowGroupBy
     * @param {string[]} colGroupBy
     * @param {Config} config
     */
    async _getGroupSubdivision(group, rowGroupBy, colGroupBy, config) {
        const groupDomain = this._getGroupDomain(group, config);
        const measureSpecs = this._getMeasureSpecs(config);
        const groupBy = rowGroupBy.concat(colGroupBy);
        const options = { lazy: false };
        const subGroups = await this.orm2Use.readGroup(
            config.meta.resModel,
            groupDomain,
            measureSpecs,
            groupBy,
            options,
            config.searchParams.context
        );
        return {
            group: group,
            subGroups: subGroups,
            rowGroupBy: rowGroupBy,
            colGroupBy: colGroupBy,
        };
    }
    /**
     * Returns the group sanitized values.
     *
     * @private
     * @param {Object} group
     * @param {string[]} groupBys
     * @returns {Array}
     */
    _getGroupValues(group, groupBys) {
        return groupBys.map((groupBy) => {
            return this._sanitizeValue(group[groupBy]);
        });
    }
    /**
     * Returns the leaf counts of each group inside the given tree.
     *
     * @private
     * @param {Object} tree
     * @returns {Object} keys are group ids
     */
    _getLeafCounts(tree) {
        const leafCounts = {};
        let leafCount;
        if (!tree.directSubTrees.size) {
            leafCount = 1;
        } else {
            leafCount = [...tree.directSubTrees.values()].reduce((acc, subTree) => {
                const subLeafCounts = this._getLeafCounts(subTree);
                Object.assign(leafCounts, subLeafCounts);
                return acc + leafCounts[JSON.stringify(subTree.root.values)];
            }, 0);
        }

        leafCounts[JSON.stringify(tree.root.values)] = leafCount;
        return leafCounts;
    }
    /**
     * Returns the group sanitized measure values for the measures in
     * this.meta.activeMeasures (that migth contain '__count', not really a fieldName).
     *
     * @private
     * @param {Object} group
     * @param {Config} config
     * @returns {Array}
     */
    _getMeasurements(group, config) {
        const { meta, searchParams } = config;
        return meta.activeMeasures.reduce((measurements, measureName) => {
            var measurement = group[measureName];
            if (measurement instanceof Array) {
                // case field is many2one and used as measure and groupBy simultaneously
                measurement = 1;
            }
            if (meta.measures[measureName].type === "boolean" && measurement instanceof Boolean) {
                measurement = measurement ? 1 : 0;
            }
            if (searchParams.origins.length > 1 && !measurement) {
                measurement = 0;
            }
            measurements[measureName] = measurement;
            return measurements;
        }, {});
    }
    /**
     * Returns a description of the measures row of the pivot table
     *
     * @private
     * @param {Object[]} columns for which measure cells must be generated
     * @returns {Object[]}
     */
    _getMeasuresRow(columns) {
        const sortedColumn = this.meta.sortedColumn || {};
        const measureRow = [];

        columns.forEach((column) => {
            this.meta.activeMeasures.forEach((measureName) => {
                const measureCell = {
                    groupId: column.groupId,
                    height: 1,
                    measure: measureName,
                    title: this.meta.measures[measureName].string,
                    width: 2 * this.searchParams.origins.length - 1,
                };
                if (
                    sortedColumn.measure === measureName &&
                    JSON.stringify(sortedColumn.groupId) === JSON.stringify(column.groupId) // FIXME
                ) {
                    measureCell.order = sortedColumn.order;
                }
                measureRow.push(measureCell);
            });
        });

        return measureRow;
    }
    /**
     * Returns the list of measure specs associated with meta.activeMeasures, i.e.
     * a measure 'fieldName' becomes 'fieldName:groupOperator' where
     * groupOperator is the value specified on the field 'fieldName' for
     * the key group_operator.
     *
     * @private
     * @param {Config} config
     * @return {string[]}
     */
    _getMeasureSpecs(config) {
        const { meta } = config;
        return meta.activeMeasures.reduce((acc, measure) => {
            if (measure === "__count") {
                acc.push(measure);
                return acc;
            }
            const field = this.meta.fields[measure];
            if (field.type === "many2one") {
                field.group_operator = "count_distinct";
            }
            if (field.group_operator === undefined) {
                throw new Error(
                    "No aggregate function has been provided for the measure '" + measure + "'"
                );
            }
            acc.push(measure + ":" + field.group_operator);
            return acc;
        }, []);
    }
    /**
     * Make sure that the labels of different many2one values are distinguished
     * by numbering them if necessary.
     *
     * @private
     * @param {Array} label
     * @param {string} fieldName
     * @param {Config} config
     * @returns {string}
     */
    _getNumberedLabel(label, fieldName, config) {
        const { data } = config;
        const id = label[0];
        const name = label[1];
        data.numbering[fieldName] = data.numbering[fieldName] || {};
        data.numbering[fieldName][name] = data.numbering[fieldName][name] || {};
        const numbers = data.numbering[fieldName][name];
        numbers[id] = numbers[id] || Object.keys(numbers).length + 1;
        return name + (numbers[id] > 1 ? "  (" + numbers[id] + ")" : "");
    }
    /**
     * Returns a description of the origins row of the pivot table
     *
     * @private
     * @param {Object[]} columns for which origin cells must be generated
     * @returns {Object[]}
     */
    _getOriginsRow(columns) {
        const sortedColumn = this.meta.sortedColumn || {};
        const originRow = [];

        columns.forEach((column) => {
            const groupId = column.groupId;
            const measure = column.measure;
            const isSorted =
                sortedColumn.measure === measure &&
                JSON.stringify(sortedColumn.groupId) === JSON.stringify(groupId); // FIXME
            const isSortedByOrigin = isSorted && !sortedColumn.originIndexes[1];
            const isSortedByVariation = isSorted && sortedColumn.originIndexes[1];

            this.searchParams.origins.forEach((origin, originIndex) => {
                const originCell = {
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
                    const variationCell = {
                        groupId: groupId,
                        height: 1,
                        measure: measure,
                        originIndexes: [originIndex - 1, originIndex],
                        title: this.env._t("Variation"),
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
    }
    /**
     * Returns the list of header rows of the pivot table: the col group rows
     * (depending on the col groupbys), the measures row and optionnaly the
     * origins row (if there are more than one origins).
     *
     * @private
     * @returns {Object[]}
     */
    _getTableHeaders() {
        const _t = this.env._t;
        const colGroupBys = this.meta.fullColGroupBys;
        const height = colGroupBys.length + 1;
        const measureCount = this.meta.activeMeasures.length;
        const originCount = this.searchParams.origins.length;
        const leafCounts = this._getLeafCounts(this.data.colGroupTree);
        let headers = [];
        const measureColumns = []; // used to generate the measure cells

        // 1) generate col group rows (total row + one row for each col groupby)
        const colGroupRows = new Array(height).fill(0).map(() => []);
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
            const group = tree.root;
            const rowIndex = group.values.length;
            const row = colGroupRows[rowIndex];
            const groupId = [[], group.values];
            const isLeaf = !tree.directSubTrees.size;
            const leafCount = leafCounts[JSON.stringify(tree.root.values)];
            const cell = {
                groupId: groupId,
                height: isLeaf ? colGroupBys.length + 1 - rowIndex : 1,
                isLeaf: isLeaf,
                isFolded: isLeaf && colGroupBys.length > group.values.length,
                label:
                    rowIndex === 0
                        ? undefined
                        : fields[colGroupBys[rowIndex - 1].split(":")[0]].string,
                title: group.labels[group.labels.length - 1] || _t("Total"),
                width: leafCount * measureCount * (2 * originCount - 1),
            };
            row.push(cell);
            if (isLeaf) {
                measureColumns.push(cell);
            }

            [...tree.directSubTrees.values()].forEach((subTree) => {
                generateTreeHeaders(subTree, fields);
            });
        }

        generateTreeHeaders(this.data.colGroupTree, this.meta.fields);
        // blank top right cell for 'Total' group (if there is more that one leaf)
        if (leafCounts[JSON.stringify(this.data.colGroupTree.root.values)] > 1) {
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
    }
    /**
     * Returns the list of body rows of the pivot table for a given tree.
     *
     * @private
     * @param {Object} tree
     * @param {Object[]} columns
     * @returns {Object[]}
     */
    _getTableRows(tree, columns) {
        let rows = [];
        const group = tree.root;
        const rowGroupId = [group.values, []];
        const title = group.labels[group.labels.length - 1] || this.env._t("Total");
        const indent = group.labels.length;
        const isLeaf = !tree.directSubTrees.size;
        const rowGroupBys = this.meta.fullRowGroupBys;

        const subGroupMeasurements = columns.map((column) => {
            const colGroupId = column.groupId;
            const groupIntersectionId = [rowGroupId[0], colGroupId[1]];
            const measure = column.measure;
            const originIndexes = column.originIndexes || [0];

            const value = this._getCellValue(groupIntersectionId, measure, originIndexes, {
                data: this.data,
            });

            const measurement = {
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
            label:
                indent === 0
                    ? undefined
                    : this.meta.fields[rowGroupBys[indent - 1].split(":")[0]].string,
            groupId: rowGroupId,
            indent: indent,
            isLeaf: isLeaf,
            isFolded: isLeaf && rowGroupBys.length > group.values.length,
            subGroupMeasurements: subGroupMeasurements,
        });

        const subTreeKeys = tree.sortedKeys || [...tree.directSubTrees.keys()];
        subTreeKeys.forEach((subTreeKey) => {
            const subTree = tree.directSubTrees.get(subTreeKey);
            rows = rows.concat(this._getTableRows(subTree, columns));
        });

        return rows;
    }
    /**
     * returns the height of a given groupTree
     *
     * @private
     * @param {Object} tree, a groupTree
     * @returns {number}
     */
    _getTreeHeight(tree) {
        const subTreeHeights = [...tree.directSubTrees.values()].map(
            this._getTreeHeight.bind(this)
        );
        return Math.max(0, Math.max.apply(null, subTreeHeights)) + 1;
    }
    /**
     * @private
     * @param {Config} config
     * @returns {boolean} true iff there's no data in the table
     */
    _hasData(config) {
        const { data } = config;
        return (data.counts[JSON.stringify([[], []])] || []).some((count) => {
            return count > 0;
        });
    }
    /**
     * Initialize/Reinitialize data.rowGroupTree, colGroupTree, measurements,
     * counts and subdivide the group 'Total' as many times it is necessary.
     * A first subdivision with no groupBy (divisors.slice(0, 1)) is made in
     * order to see if there is data in the intersection of the group 'Total'
     * and the various origins. In case there is none, non supplementary rpc
     * will be done (see the code of subdivideGroup).
     *
     * @private
     * @param {Config} config
     */
    async _loadData(config) {
        config.data = {}; // data will be completely recomputed
        const { data, meta, searchParams } = config;
        data.rowGroupTree = { root: { labels: [], values: [] }, directSubTrees: new Map() };
        data.colGroupTree = { root: { labels: [], values: [] }, directSubTrees: new Map() };
        data.measurements = {};
        data.counts = {};
        data.groupDomains = {};
        data.numbering = {};
        const key = JSON.stringify([[], []]);
        data.groupDomains[key] = searchParams.domains.slice(0);

        const group = { rowValues: [], colValues: [] };
        const leftDivisors = sections(meta.fullRowGroupBys);
        const rightDivisors = sections(meta.fullColGroupBys);
        const divisors = cartesian(leftDivisors, rightDivisors);

        await this._subdivideGroup(group, divisors.slice(0, 1), config);
        await this._subdivideGroup(group, divisors.slice(1), config);

        if (meta.useSampleModel && !this._hasData(config)) {
            const fakeORM = buildSampleORM(meta.resModel, meta.fields, this.user);
            this.orm2Use = fakeORM;
            return this._loadData(config);
        } else if (this.orm2Use.rpc.name !== "fakeRPC") {
            meta.useSampleModel = false;
        }
        return config.data;
    }
    /**
     * Extract the information in the read_group results (groupSubdivisions)
     * and develop this.data.rowGroupTree, colGroupTree, measurements, counts, and
     * groupDomains.
     * If a column needs to be sorted, the rowGroupTree corresponding to the
     * group is sorted.
     *
     * @private
     * @param {Object} group
     * @param {Object[]} groupSubdivisions
     * @param {Config} config
     */
    _prepareData(group, groupSubdivisions, config) {
        const { data, meta, searchParams } = config;
        const groupRowValues = group.rowValues;
        let groupRowLabels = [];
        let rowSubTree = data.rowGroupTree;
        let root;
        if (groupRowValues.length) {
            // we should have labels information on hand! regretful!
            rowSubTree = this._findGroup(data.rowGroupTree, groupRowValues);
            root = rowSubTree.root;
            groupRowLabels = root.labels;
        }

        const groupColValues = group.colValues;
        let groupColLabels = [];
        if (groupColValues.length) {
            root = this._findGroup(data.colGroupTree, groupColValues).root;
            groupColLabels = root.labels;
        }

        groupSubdivisions.forEach((groupSubdivision) => {
            groupSubdivision.subGroups.forEach((subGroup) => {
                const rowValues = groupRowValues.concat(
                    this._getGroupValues(subGroup, groupSubdivision.rowGroupBy)
                );
                const rowLabels = groupRowLabels.concat(
                    this._getGroupLabels(subGroup, groupSubdivision.rowGroupBy, config)
                );

                const colValues = groupColValues.concat(
                    this._getGroupValues(subGroup, groupSubdivision.colGroupBy)
                );
                const colLabels = groupColLabels.concat(
                    this._getGroupLabels(subGroup, groupSubdivision.colGroupBy, config)
                );

                if (!colValues.length && rowValues.length) {
                    this._addGroup(data.rowGroupTree, rowLabels, rowValues);
                }
                if (colValues.length && !rowValues.length) {
                    this._addGroup(data.colGroupTree, colLabels, colValues);
                }

                const key = JSON.stringify([rowValues, colValues]);
                const originIndex = groupSubdivision.group.originIndex;

                if (!(key in data.measurements)) {
                    data.measurements[key] = searchParams.origins.map(() => {
                        return this._getMeasurements({}, config);
                    });
                }
                data.measurements[key][originIndex] = this._getMeasurements(subGroup, config);

                if (!(key in data.counts)) {
                    data.counts[key] = searchParams.origins.map(function () {
                        return 0;
                    });
                }
                data.counts[key][originIndex] = subGroup.__count;

                if (!(key in data.groupDomains)) {
                    data.groupDomains[key] = searchParams.origins.map(function () {
                        return Domain.FALSE.toList();
                    });
                }
                // if __domain is not defined this means that we are in the
                // case where
                // groupSubdivision.rowGroupBy = groupSubdivision.rowGroupBy = []
                if (subGroup.__domain) {
                    data.groupDomains[key][originIndex] = subGroup.__domain;
                }
            });
        });

        if (meta.sortedColumn) {
            this._sortRows(meta.sortedColumn, config);
        }
    }
    /**
     * Determine this.searchParams.domains and this.searchParams.origins from
     * this.searchParams.domains.
     *
     * @private
     */
    _computeDerivedParams(params) {
        const domains = params.domains.reverse();
        return {
            domains: domains.map((d) => d.arrayRepr),
            origins: domains.map((d) => d.description || ""),
        };
    }
    /**
     * Make any group in tree a leaf if it was a leaf in oldTree.
     *
     * @private
     * @param {Object} tree
     * @param {Object} oldTree
     */
    _pruneTree(tree, oldTree) {
        if (!oldTree.directSubTrees.size) {
            tree.directSubTrees.clear();
            delete tree.sortedKeys;
            return;
        }
        [...tree.directSubTrees.keys()].forEach((subTreeKey) => {
            const subTree = tree.directSubTrees.get(subTreeKey);
            if (!oldTree.directSubTrees.has(subTreeKey)) {
                subTree.directSubTrees.clear();
                delete subTreeKey.sortedKeys;
            } else {
                const oldSubTree = oldTree.directSubTrees.get(subTreeKey);
                this._pruneTree(subTree, oldSubTree);
            }
        });
    }
    /**
     * Extract from a groupBy value a label.
     *
     * @private
     * @param {any} value
     * @param {string} groupBy
     * @param {Config} config
     * @returns {string}
     */
    _sanitizeLabel(value, groupBy, config) {
        const { meta } = config;
        const fieldName = groupBy.split(":")[0];
        if (value === false) {
            return this.env._t("Undefined");
        }
        if (value instanceof Array) {
            return this._getNumberedLabel(value, fieldName, config);
        }
        if (fieldName && meta.fields[fieldName] && meta.fields[fieldName].type === "selection") {
            const selected = meta.fields[fieldName].selection.find((o) => o[0] === value);
            return selected ? selected[1] : value; // selected should be truthy normally ?!
        }
        return value;
    }
    /**
     * Extract from a groupBy value the raw value of that groupBy (discarding
     * a label if any)
     *
     * @private
     * @param {any} value
     * @returns {any}
     */
    _sanitizeValue(value) {
        if (value instanceof Array) {
            return value[0];
        }
        return value;
    }
    /**
     * Get all partitions of a given group using the provided list of divisors
     * and enrich the objects of this.data.rowGroupTree, colGroupTree,
     * measurements, counts.
     *
     * @private
     * @param {Object} group
     * @param {Array[]} divisors
     * @param {Config} config
     */
    async _subdivideGroup(group, divisors, config) {
        const { data, searchParams } = config;
        const key = JSON.stringify([group.rowValues, group.colValues]);

        const proms = searchParams.origins.reduce((acc, origin, originIndex) => {
            // if no information on group content is available, we fetch data.
            // if group is known to be empty for the given origin,
            // we don't need to fetch data for that origin.
            if (!data.counts[key] || data.counts[key][originIndex] > 0) {
                const subGroup = {
                    rowValues: group.rowValues,
                    colValues: group.colValues,
                    originIndex: originIndex,
                };
                divisors.forEach((divisor) => {
                    acc.push(this._getGroupSubdivision(subGroup, divisor[0], divisor[1], config));
                });
            }
            return acc;
        }, []);
        const groupSubdivisions = await this.keepLast.add(Promise.all(proms));
        if (groupSubdivisions.length) {
            this._prepareData(group, groupSubdivisions, config);
        }
    }
    /**
     * Sort the rows, depending on the values of a given column.  This is an
     * in-memory sort.
     *
     * @private
     * @param {Object} sortedColumn
     * @param {number[]} sortedColumn.groupId
     * @param {Config} config
     */
    _sortRows(sortedColumn, config) {
        const meta = config.meta || this.meta;
        const data = config.data || this.data;
        const colGroupValues = sortedColumn.groupId[1];
        sortedColumn.originIndexes = sortedColumn.originIndexes || [0];
        meta.sortedColumn = sortedColumn;

        const sortFunction = (tree) => {
            return (subTreeKey) => {
                const subTree = tree.directSubTrees.get(subTreeKey);
                const groupIntersectionId = [subTree.root.values, colGroupValues];
                const value =
                    this._getCellValue(
                        groupIntersectionId,
                        sortedColumn.measure,
                        sortedColumn.originIndexes,
                        { data }
                    ) || 0;
                return sortedColumn.order === "asc" ? value : -value;
            };
        };

        this._sortTree(sortFunction, data.rowGroupTree);
    }
    /**
     * Sort recursively the subTrees of tree using sortFunction.
     * In the end each node of the tree has its direct children sorted
     * according to the criterion reprensented by sortFunction.
     *
     * @private
     * @param {Function} sortFunction
     * @param {Object} tree
     */
    _sortTree(sortFunction, tree) {
        tree.sortedKeys = sortBy([...tree.directSubTrees.keys()], sortFunction(tree));
        [...tree.directSubTrees.values()].forEach((subTree) => {
            this._sortTree(sortFunction, subTree);
        });
    }
}
PivotModel.services = ["orm", "user"];
