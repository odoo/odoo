// @ts-check

/** @module @web/views/pivot/pivot_model - Pivot table data loading, group tree expansion, measure aggregation, and cell computation */

import { Domain } from "@web/core/domain";
import {
    cartesian,
    sections,
    symmetricalDifference,
} from "@web/core/utils/collections/arrays";
import { KeepLast, Race } from "@web/core/utils/concurrency";
import { addPropertyFieldDefs, Model } from "@web/model/model";
import { DEFAULT_INTERVAL } from "@web/search/utils/dates";
import { computeReportMeasures, processMeasure } from "@web/views/view_measurements";

import { formatPivotForExport } from "./pivot_export";
import {
    addGroup,
    findGroup,
    getLeafCounts,
    getTreeHeight,
    hasData,
    pruneTree,
    sortTree,
} from "./pivot_group_tree";
import {
    getCellValue,
    getCurrencyIds,
    getMeasurements,
    getMeasureSpecs,
} from "./pivot_measurements";
import { getTableHeaders, getTableRows } from "./pivot_table";
import {
    getGroupBySpecs,
    getGroupDomain,
    getGroupLabels,
    getGroupValues,
} from "./pivot_value_utils";

/**
 * Pivot Model
 *
 * The pivot model keeps an in-memory representation of the pivot table that is
 * displayed on the screen.  The exact layout of this representation is not so
 * simple, because a pivot table is at its core a 2-dimensional object, but
 * with a 'list' component: some rows/cols can be expanded so we zoom into the
 * structure.
 *
 * However, we need to be able to manipulate the data in a somewhat efficient
 * way, and to transform it into a list of lines to be displayed by the renderer.
 *
 * Basicaly the pivot table presents aggregated values for various groups of records
 * in one domain.
 *
 * Let us consider a simple example and let us fix the vocabulary:
 * __________________________________________________________________________
 * |                    |   Total                                           |
 * |                    |___________________________________________________|
 * |                    |   Sale Team 1   |  Sale Team 2   |                |
 * |                    |_________________|________________|________________|
 * |                    |   Sales total   |  Sales total   |  Sales total   |
 * |____________________|_________________|________________|________________|
 * | Total              |      110        |       30       |      140       |
 * |    Europe          |       35        |       30       |       65       |
 * |        Brussels    |       15        |       30       |       45       |
 * |        Paris       |       20        |        0       |       20       |
 * |    North America   |       75        |                |       75       |
 * |        Washington  |       75        |                |       75       |
 * |____________________|_________________|________________|________________|
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
 * The domain considered is 'sale_date in June 2020'.
 *
 * In the model,
 *
 *      - rowGroupBys is the list [continent_id, city_id]
 *      - colGroupBys is the list [sale_team_id]
 *      - measures is the list [sales_total]
 *      - domain is the domain expression for say sale_date in June 2020:
 *          [['sale_date', >=, 2020-06-01], ['sale_date', '<=', 2020-06-30]]
 *
 * DATA:
 *
 * Recall that a group is constituted by records that have the same (raw) values
 * for a list of fields. Thus the group itself is identified by this list.
 *
 * In the above table, the following groups are found:
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
 * For each list of fields possible, one read_group is done
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
 *                  ['sale_date', >=, 2020-06-01], ['sale_date', '<=', 2020-06-30],
 *                  ['continent_id', '=', 1],
 *                  ['sale_team_id', '=', 1]
 *                ]
 * }
 *
 * Thus the above group g is fully determined by [[v1,...,vi], [w1,...,wj]].
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
 *                      labels: [label1,...,labedll]
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
 *              and objects values are of the form {m1: x1,...,mk: xk}
 *              The structure looks like
 *
 *              {
 *                  JSON.stringify([[], []]): {m1: x1,...,mk: xk}
 *                  ....
 *                  JSON.stringify([[v1,...,vi], [w1,...,wj]]): {m1: y1,...,mk: yk},
 *                  ....
 *                  JSON.stringify([[v1,...,vn], [w1,...,wm]]): {m1: z1,...,mk: zk},
 *              }
 *              Thus the structure contains all information for all groups on measure values.
 *
 *
 *              this.measurments["[[], []]"]['foo'] gives the value of the measure 'foo' for the group 'Total'.
 *
 *              In the example:
 *                  {
 *                      "[[], []]": {'sales_total': 140}           (total/total)
 *                      ...
 *                      "[[1, 2], [2]]": {'sales_total': 0}        (Europe/Paris/Sale Team 2)
 *                      ...
 *                  }
 *
 *      - counts: contains information on the number of records in each groups
 *              The structure is similar to the above but the values are numbers (counts)
 *      - groupDomains:
 *              The structure is similar to the above but the values are domains
 *
 *      With this light data structures, all manipulation done by the model are eased and redundancies are limited.
 *      Each time a rendering or an export of the data has to be done, the pivot table is generated by the getTable function.
 */

/**
 * @typedef Meta
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
 * @property {Array} domain
 */

/**
 * @typedef Data
 * @property {Object} colGroupTree
 * @property {Object} rowGroupTree
 * @property {Object} groupDomains
 * @property {Object} measurements
 * @property {Object} currencyIds
 * @property {Object} counts
 * @property {Object} numbering
 */

/**
 * @typedef {import("@web/search/search_model").SearchParams} SearchParams
 */

/**
 * @typedef Config
 * @property {any} metaData
 * @property {any} data
 */

export class PivotModel extends Model {
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.metaData
     * @param {string[]} params.metaData.activeMeasures
     * @param {string[]} params.metaData.colGroupBys
     * @param {Object} params.metaData.fields
     * @param {Object[]} params.metaData.measures
     * @param {string} params.metaData.resModel
     * @param {string[]} params.metaData.rowGroupBys
     * @param {string|null} params.metaData.defaultOrder
     * @param {boolean} params.metaData.disableLinking
     * @param {boolean} params.metaData.useSampleModel
     * @param {Map} [params.metaData.customGroupBys={}]
     * @param {string[]} [params.metaData.expandedColGroupBys=[]]
     * @param {string[]} [params.metaData.expandedRowGroupBys=[]]
     * @param {Object|null} [params.metaData.sortedColumn=null]
     * @param {Object} [params.data] previously exported data
     */
    setup(params) {
        // concurrency management
        this.keepLast = new KeepLast();
        this.race = new Race();
        /** @type {(...args: any[]) => any} */
        const _loadData = this._loadData.bind(this);
        /** @type {any} */
        this._loadData = (...args) => this.race.add(_loadData(...args));

        let sortedColumn = params.metaData.sortedColumn || null;
        if (!sortedColumn && params.metaData.defaultOrder) {
            const defaultOrder = params.metaData.defaultOrder.split(" ");
            sortedColumn = {
                groupId: [[], []],
                measure: defaultOrder[0],
                order: defaultOrder[1] ? defaultOrder[1] : "asc",
            };
        }

        this.searchParams = {
            context: {},
            domain: [],
            groupBy: [],
        };
        this.data = params.data || {
            colGroupTree: null,
            rowGroupTree: null,
            groupDomains: {},
            measurements: {},
            currencyIds: {},
            counts: {},
            numbering: {},
        };
        const metaData = {
            ...params.metaData,
            customGroupBys: params.metaData.customGroupBys || new Map(),
            expandedRowGroupBys: params.metaData.expandedRowGroupBys || [],
            expandedColGroupBys: params.metaData.expandedColGroupBys || [],
            sortedColumn,
        };
        this.metaData = this._buildMetaData(metaData);

        this.reload = false; // used to discriminate between the first load and subsequent reloads
        this.nextActiveMeasures = null; // allows to toggle several measures consecutively
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
        if (this.race.getCurrentProm()) {
            return; // we are currently reloaded the table
        }

        const { groupId, fieldName, type, custom } = params;
        let { interval } = params;
        const metaData = this._buildMetaData();
        if (custom && !metaData.customGroupBys.has(fieldName)) {
            const field = metaData.fields[fieldName];
            if (!interval && ["date", "datetime"].includes(field.type)) {
                interval = DEFAULT_INTERVAL;
            }
            metaData.customGroupBys.set(fieldName, {
                ...field,
                id: fieldName,
            });
        }

        let groupBy = fieldName;
        if (interval) {
            groupBy = `${groupBy}:${interval}`;
        }
        if (type === "row") {
            metaData.expandedRowGroupBys.push(groupBy);
        } else {
            metaData.expandedColGroupBys.push(groupBy);
        }
        const config = { metaData, data: this.data };
        await this._expandGroup(groupId, type, config);
        this.metaData = metaData;
        this.notify();
    }
    /**
     * Close the group with id given by groupId.
     *
     * @param {Array[]} groupId
     * @param {'row'|'col'} type
     */
    closeGroup(groupId, type) {
        if (this.race.getCurrentProm()) {
            return; // we are currently reloading the table
        }

        let groupBys;
        let expandedGroupBys;
        let keyPart;
        let group;
        let tree;
        if (type === "row") {
            groupBys = this.metaData.rowGroupBys;
            expandedGroupBys = this.metaData.expandedRowGroupBys;
            tree = this.data.rowGroupTree;
            group = findGroup(this.data.rowGroupTree, groupId[0]);
            keyPart = 0;
        } else {
            groupBys = this.metaData.colGroupBys;
            expandedGroupBys = this.metaData.expandedColGroupBys;
            tree = this.data.colGroupTree;
            group = findGroup(this.data.colGroupTree, groupId[1]);
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
        this.data.currencyIds = omitKeys(this.data.currencyIds);
        this.data.counts = omitKeys(this.data.counts);
        this.data.groupDomains = omitKeys(this.data.groupDomains);

        group.directSubTrees.clear();
        delete group.sortedKeys;
        const newGroupBysLength = getTreeHeight(tree) - 1;
        if (newGroupBysLength <= groupBys.length) {
            expandedGroupBys.splice(0);
            groupBys.splice(newGroupBysLength);
        } else {
            expandedGroupBys.splice(newGroupBysLength - groupBys.length);
        }
        this.notify();
    }
    /**
     * Reload the view with the current rowGroupBys and colGroupBys.
     */
    async expandAll() {
        const config = { metaData: this.metaData, data: this.data };
        await this._loadData(config, false);
        this.notify();
    }
    /**
     * Expand a group by using groupBy to split it and trigger a re-rendering.
     *
     * @param {string} groupId
     * @param {'row'|'col'} type
     */
    async expandGroup(groupId, type) {
        if (this.race.getCurrentProm()) {
            return; // we are currently reloaded the table
        }

        const config = { metaData: this.metaData, data: this.data };
        await this._expandGroup(/** @type {any} */ (groupId), type, config);
        this.notify();
    }
    /**
     * Export model data in a form suitable for an easy encoding of the pivot
     * table in excell.
     *
     * @returns {Object}
     */
    exportData() {
        return formatPivotForExport(this.getTable(), this.metaData);
    }
    /**
     * Swap the pivot columns and the rows.
     */
    async flip() {
        await this.race.getCurrentProm();

        // swap the data: the main column and the main row
        let temp = this.data.rowGroupTree;
        this.data.rowGroupTree = this.data.colGroupTree;
        this.data.colGroupTree = temp;

        // we need to update the record metaData: (expanded) row and col groupBys
        temp = this.metaData.rowGroupBys;
        this.metaData.rowGroupBys = this.metaData.colGroupBys;
        this.metaData.colGroupBys = temp;
        temp = this.metaData.expandedColGroupBys;
        this.metaData.expandedColGroupBys = this.metaData.expandedRowGroupBys;
        this.metaData.expandedRowGroupBys = temp;

        function twistKey(key) {
            return JSON.stringify(JSON.parse(key).reverse());
        }

        function twist(object) {
            const newObject = {};
            for (const key of Object.keys(object)) {
                newObject[twistKey(key)] = object[key];
            }
            return newObject;
        }

        this.data.measurements = twist(this.data.measurements);
        this.data.currencyIds = twist(this.data.currencyIds);
        this.data.counts = twist(this.data.counts);
        this.data.groupDomains = twist(this.data.groupDomains);

        this.notify();
    }
    /**
     * Returns a domain representation of a group.
     *
     * @param {Object} group
     * @returns {Array[]}
     */
    getGroupDomain(group) {
        const config = { metaData: this.metaData, data: this.data };
        return getGroupDomain(group, config);
    }
    /**
     * Returns a description of the pivot table.
     *
     * @returns {Object}
     */
    getTable() {
        const headers = getTableHeaders(this.data, this.metaData);
        return {
            headers,
            rows: getTableRows(
                this.data.rowGroupTree,
                headers.at(-1),
                this.data,
                this.metaData,
            ),
        };
    }
    /**
     * Returns the total number of columns of the pivot table.
     *
     * @returns {number}
     */
    getTableWidth() {
        const leafCounts = getLeafCounts(this.data.colGroupTree);
        return leafCounts[JSON.stringify(this.data.colGroupTree.root.values)] + 2;
    }
    /**
     * @returns {boolean} true iff there's no data in the table
     */
    hasData() {
        return hasData(this.data);
    }
    /**
     * @override
     * @param {SearchParams} searchParams
     */
    async load(searchParams) {
        this.searchParams = searchParams;
        const processedMeasures = processMeasure(searchParams.context.pivot_measures);
        const activeMeasures = processedMeasures || this.metaData.activeMeasures;
        const metaData = this._buildMetaData({ activeMeasures });
        if (!this.reload) {
            metaData.rowGroupBys =
                searchParams.context.pivot_row_groupby ||
                (searchParams.groupBy.length
                    ? searchParams.groupBy
                    : metaData.rowGroupBys);
            this.reload = true;
        } else {
            metaData.rowGroupBys = searchParams.groupBy.length
                ? searchParams.groupBy
                : searchParams.context.pivot_row_groupby || metaData.rowGroupBys;
        }
        metaData.colGroupBys =
            searchParams.context.pivot_column_groupby || this.metaData.colGroupBys;

        if (
            JSON.stringify(metaData.rowGroupBys) !==
            JSON.stringify(this.metaData.rowGroupBys)
        ) {
            metaData.expandedRowGroupBys = [];
        }
        if (
            JSON.stringify(metaData.colGroupBys) !==
            JSON.stringify(this.metaData.colGroupBys)
        ) {
            metaData.expandedColGroupBys = [];
        }

        const allActivesMeasures = new Set(this.metaData.activeMeasures);
        if (processedMeasures) {
            processedMeasures.forEach((e) => allActivesMeasures.add(e));
        }

        metaData.measures = computeReportMeasures(
            metaData.fields,
            metaData.fieldAttrs,
            [...allActivesMeasures],
        );
        const config = { metaData, data: this.data };
        await addPropertyFieldDefs(
            this.orm,
            metaData.resModel,
            searchParams.context,
            metaData.fields,
            new Set([...metaData.rowGroupBys, ...metaData.colGroupBys]),
        );
        return this._loadData(config);
    }
    /**
     * Sort the rows, depending on the values of a given column.
     *
     * @param {Object} sortedColumn
     */
    sortRows(sortedColumn) {
        if (this.race.getCurrentProm()) {
            return; // we are currently reloaded the table
        }

        const config = { metaData: this.metaData, data: this.data };
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
        const metaData = this._buildMetaData();
        this.nextActiveMeasures = this.nextActiveMeasures || metaData.activeMeasures;
        metaData.activeMeasures = this.nextActiveMeasures;
        const index = metaData.activeMeasures.indexOf(fieldName);
        if (index !== -1) {
            metaData.activeMeasures.splice(index, 1);
            await Promise.resolve(this.race.getCurrentProm());
            this.metaData = metaData;
        } else {
            metaData.activeMeasures.push(fieldName);
            const config = { metaData, data: this.data };
            await this._loadData(config);
            this.useSampleModel = false;
        }
        this.nextActiveMeasures = null;
        this.notify();
    }

    //--------------------------------------------------------------------------
    // Protected
    //--------------------------------------------------------------------------

    /**
     * Return a copy of this.metaData, extended with optional params.
     *
     * @protected
     * @param {Object} params
     * @returns {Object}
     */
    _buildMetaData(params) {
        const metaData = { ...this.metaData, ...params };
        metaData.activeMeasures = [...metaData.activeMeasures];
        metaData.colGroupBys = [...metaData.colGroupBys];
        metaData.rowGroupBys = [...metaData.rowGroupBys];
        metaData.expandedColGroupBys = [...metaData.expandedColGroupBys];
        metaData.expandedRowGroupBys = [...metaData.expandedRowGroupBys];
        metaData.customGroupBys = new Map([...metaData.customGroupBys]);
        metaData.sortedColumn = metaData.sortedColumn
            ? { ...metaData.sortedColumn }
            : null;
        metaData.domain = this.searchParams.domain;
        Object.defineProperty(metaData, "fullColGroupBys", {
            get() {
                return [...metaData.colGroupBys, ...metaData.expandedColGroupBys];
            },
        });
        Object.defineProperty(metaData, "fullRowGroupBys", {
            get() {
                return [...metaData.rowGroupBys, ...metaData.expandedRowGroupBys];
            },
        });
        return metaData;
    }
    /**
     * Expand a group by using groupBy to split it.
     *
     * @protected
     * @param {Array[]} groupId
     * @param {'row'|'col'} type
     * @param {Config} config
     */
    async _expandGroup(groupId, type, config) {
        const { metaData } = config;
        const group = {
            rowValues: groupId[0],
            colValues: groupId[1],
            type: type,
        };
        const groupValues = type === "row" ? groupId[0] : groupId[1];
        const groupBys =
            type === "row" ? metaData.fullRowGroupBys : metaData.fullColGroupBys;
        if (groupValues.length >= groupBys.length) {
            throw new Error("Cannot expand group");
        }
        const groupBy = groupBys[groupValues.length];
        let leftDivisors;
        let rightDivisors;
        if (group.type === "row") {
            leftDivisors = [[groupBy]];
            rightDivisors = sections(metaData.fullColGroupBys);
        } else {
            leftDivisors = sections(metaData.fullRowGroupBys);
            rightDivisors = [[groupBy]];
        }
        const divisors = cartesian(leftDivisors, rightDivisors);
        delete group.type;
        await this._subdivideGroup(group, divisors, config);
    }

    async _getGroupsSubdivision(params, groupInfo) {
        const { resModel, groupDomain, groupingSets, measureSpecs, kwargs } = params;
        const result = await this.orm.formattedReadGroupingSets(
            resModel,
            groupDomain,
            groupingSets,
            measureSpecs,
            kwargs,
        );
        return groupInfo.map((info) => ({
            ...info,
            subGroups: result[info.subGroupIndex],
        }));
    }

    /**
     * Initialize/Reinitialize data and subdivide the group 'Total'.
     *
     * @protected
     * @param {Config} config
     * @param {boolean} prune
     */
    async _loadData(config, prune = true) {
        config.data = /** @type {any} */ ({});
        const { data, metaData } = config;
        data.rowGroupTree = {
            root: { labels: [], values: [] },
            directSubTrees: new Map(),
        };
        data.colGroupTree = {
            root: { labels: [], values: [] },
            directSubTrees: new Map(),
        };
        data.measurements = {};
        data.currencyIds = {};
        data.counts = {};
        data.groupDomains = {};
        data.numbering = {};
        const key = JSON.stringify([[], []]);
        data.groupDomains[key] = metaData.domain;

        const group = { rowValues: [], colValues: [] };
        const leftDivisors = sections(metaData.fullRowGroupBys);
        const rightDivisors = sections(metaData.fullColGroupBys);
        const divisors = cartesian(leftDivisors, rightDivisors);

        await this._subdivideGroup(group, divisors, config);

        // keep folded groups folded after the reload if the structure of the table is the same
        if (prune && hasData(data) && hasData(this.data)) {
            if (
                symmetricalDifference(metaData.rowGroupBys, this.metaData.rowGroupBys)
                    .length === 0
            ) {
                pruneTree(data.rowGroupTree, this.data.rowGroupTree);
            }
            if (
                symmetricalDifference(metaData.colGroupBys, this.metaData.colGroupBys)
                    .length === 0
            ) {
                pruneTree(data.colGroupTree, this.data.colGroupTree);
            }
        }

        this.data = config.data;
        this.metaData = config.metaData;
    }
    /**
     * Extract the information in the read_group results and develop
     * rowGroupTree, colGroupTree, measurements, counts, and groupDomains.
     *
     * @protected
     * @param {Object} group
     * @param {Object[]} groupSubdivisions
     * @param {Config} config
     */
    _prepareData(group, groupSubdivisions, config) {
        const { data, metaData } = config;
        const groupRowValues = group.rowValues;
        let groupRowLabels = [];
        if (groupRowValues.length) {
            const rowSubTree = findGroup(data.rowGroupTree, groupRowValues);
            groupRowLabels = rowSubTree.root.labels;
        }

        const groupColValues = group.colValues;
        let groupColLabels = [];
        if (groupColValues.length) {
            groupColLabels = findGroup(data.colGroupTree, groupColValues).root.labels;
        }

        groupSubdivisions.forEach((groupSubdivision) => {
            groupSubdivision.subGroups.forEach((subGroup) => {
                const rowValues = [
                    ...groupRowValues,
                    ...getGroupValues(
                        subGroup,
                        groupSubdivision.rowGroupBy,
                        metaData.fields,
                    ),
                ];
                const rowLabels = [
                    ...groupRowLabels,
                    ...getGroupLabels(
                        subGroup,
                        groupSubdivision.rowGroupBy,
                        config,
                        metaData.fields,
                    ),
                ];

                const colValues = [
                    ...groupColValues,
                    ...getGroupValues(
                        subGroup,
                        groupSubdivision.colGroupBy,
                        metaData.fields,
                    ),
                ];
                const colLabels = [
                    ...groupColLabels,
                    ...getGroupLabels(
                        subGroup,
                        groupSubdivision.colGroupBy,
                        config,
                        metaData.fields,
                    ),
                ];

                if (!colValues.length && rowValues.length) {
                    addGroup(data.rowGroupTree, rowLabels, rowValues);
                }
                if (colValues.length && !rowValues.length) {
                    addGroup(data.colGroupTree, colLabels, colValues);
                }

                const key = JSON.stringify([rowValues, colValues]);

                data.measurements[key] = getMeasurements(subGroup, config);
                data.currencyIds[key] = getCurrencyIds(subGroup, config);
                data.counts[key] = subGroup.__count;

                if (subGroup.__domain) {
                    data.groupDomains[key] = subGroup.__domain;
                } else {
                    data.groupDomains[key] = Domain.FALSE.toList();
                }
            });
        });

        if (metaData.sortedColumn) {
            this._sortRows(metaData.sortedColumn, config);
        }
    }
    /**
     * Get all partitions of a given group and enrich data structures.
     *
     * @protected
     * @param {Object} group
     * @param {Array[]} divisors
     * @param {Config} config
     */
    async _subdivideGroup(group, divisors, config) {
        const { data } = config;
        const key = JSON.stringify([group.rowValues, group.colValues]);

        if (!data.counts[key] || data.counts[key] > 0) {
            const subGroup = {
                rowValues: group.rowValues,
                colValues: group.colValues,
            };
            const groupDomainValue = getGroupDomain(subGroup, config);
            const measureSpecsList = getMeasureSpecs(config);
            if (!measureSpecsList.includes("__count")) {
                measureSpecsList.push("__count");
            }
            const resModel = config.metaData.resModel;
            const kwargs = { context: this.searchParams.context };
            const groupingSets = [];
            const groupInfo = [];
            divisors.forEach((divisor) => {
                const groupBy = getGroupBySpecs(
                    divisor[0],
                    divisor[1],
                    config.metaData.fields,
                );
                const sortedKey = JSON.stringify(groupBy.toSorted());
                let index = groupingSets.findIndex(
                    (value) => JSON.stringify(value.toSorted()) === sortedKey,
                );
                if (index === -1) {
                    index = groupingSets.length;
                    groupingSets.push(groupBy);
                }
                groupInfo.push({
                    group: subGroup,
                    rowGroupBy: divisor[0],
                    colGroupBy: divisor[1],
                    subGroupIndex: index,
                });
            });

            const params = {
                resModel,
                groupDomain: groupDomainValue,
                measureSpecs: measureSpecsList,
                kwargs,
                groupingSets,
            };
            const groupSubdivisions = await this.keepLast.add(
                this._getGroupsSubdivision(params, groupInfo),
            );
            if (groupSubdivisions.length) {
                this._prepareData(group, groupSubdivisions, config);
            }
        }
    }
    /**
     * Sort the rows, depending on the values of a given column.
     *
     * @protected
     * @param {Object} sortedColumn
     * @param {Config} config
     */
    _sortRows(sortedColumn, config) {
        const metaData = config.metaData || this.metaData;
        const data = config.data || this.data;
        const colGroupValues = sortedColumn.groupId[1];
        metaData.sortedColumn = sortedColumn;

        const sortFunction = (tree) => (subTreeKey) => {
            const subTree = tree.directSubTrees.get(subTreeKey);
            const groupIntersectionId = [subTree.root.values, colGroupValues];
            const value =
                getCellValue(groupIntersectionId, sortedColumn.measure, data) || 0;
            return sortedColumn.order === "asc" ? value : -value;
        };

        sortTree(sortFunction, data.rowGroupTree);
    }
}
