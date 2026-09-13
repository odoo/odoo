// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";
import {
    cartesian,
    sections,
    symmetricalDifference,
} from "@web/core/utils/collections/arrays";
import {
    InFlight,
    KeepLast,
    Mutex,
    SupersededError,
} from "@web/core/utils/concurrency";
import { Model } from "@web/model/model";
import { addPropertyFieldDefs } from "@web/model/property_fields";
import { DEFAULT_INTERVAL } from "@web/search/utils/dates";
import { aggregateSubdivisions } from "@web/views/pivot/pivot_aggregation";
import {
    computeReportMeasures,
    dropUnknownMeasures,
    processMeasure,
    visibleArchGroupBys,
} from "@web/views/view_measurements";

import { computeExportedTableWidth, formatPivotForExport } from "./pivot_export.js";
import {
    findGroup,
    getLeafCounts,
    getTreeHeight,
    hasData,
    removeMissingSubTrees,
    sortTree,
    stripSortedKeys,
} from "./pivot_group_tree.js";
import {
    getCellValue,
    getMeasurements,
    getMeasureSpecs,
    makeCellKey,
} from "./pivot_measurements.js";
import { getTableHeaders, getTableRows } from "./pivot_table.js";
import {
    getGroupBySpecs,
    getGroupDomain,
    normalize,
    sanitizeLabel,
    sanitizeValue,
} from "./pivot_value_utils.js";

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
 * @property {Map<string, any>} customGroupBys
 * @property {string[]} expandedRowGroupBys
 * @property {string[]} expandedColGroupBys
 * @property {Object} sortedColumn
 * @property {any[]} domain
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

/** @typedef {import("@web/model/types").SearchParams} SearchParams */

/**
 * @typedef Config
 * @property {any} metaData
 * @property {any} data
 */

const SUPERSEDED = Symbol("superseded");

const log = makeLogger("web.view.pivot");

/**
 * @template {object} [E=import("@web/env").OdooEnv]
 * @extends {Model<E>}
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
     * @param {Map<string, any>} [params.metaData.customGroupBys={}]
     * @param {string[]} [params.metaData.expandedColGroupBys=[]]
     * @param {string[]} [params.metaData.expandedRowGroupBys=[]]
     * @param {Object|null} [params.metaData.sortedColumn=null]
     * @param {Object} [params.data]
     */
    setup(params) {
        this.keepLast = new KeepLast({ rejectSuperseded: true });
        this.expandMutex = new Mutex();
        this.loads = new InFlight();
        /** @type {(...args: any[]) => any} */
        const _loadData = this._loadData.bind(this);
        /** @type {any} */
        this._loadData = (...args) => this.loads.track(_loadData(...args));

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

        this.reload = false;
        this.lastPivotMeasuresKey = undefined;
        this.nextActiveMeasures = null;
        this.measureToggleEpoch = 0;
    }

    /**
     * @param {Object} params
     * @param {Array[]} params.groupId
     * @param {string} params.fieldName
     * @param {'row'|'col'} params.type
     * @param {boolean} [params.custom=false]
     * @param {string} [params.interval]
     */
    async addGroupBy(params) {
        if (this.loads.isBusy) {
            return;
        }

        const { groupId, fieldName, type, custom } = params;
        let { interval } = params;
        await this.expandMutex.exec(async () => {
            if (this.loads.isBusy) {
                return;
            }
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
            if (!(await this._expandGroup(groupId, type, config))) {
                return;
            }
            const mergedMetaData = this._buildMetaData();
            mergedMetaData.customGroupBys = metaData.customGroupBys;
            mergedMetaData.expandedRowGroupBys = metaData.expandedRowGroupBys;
            mergedMetaData.expandedColGroupBys = metaData.expandedColGroupBys;
            if (mergedMetaData.sortedColumn) {
                this._sortRows(mergedMetaData.sortedColumn, {
                    metaData: mergedMetaData,
                    data: this.data,
                });
            }
            this.metaData = mergedMetaData;
            this.notify();
        });
    }
    /**
     * @param {Array[]} groupId
     * @param {'row'|'col'} type
     */
    async closeGroup(groupId, type) {
        if (this.loads.isBusy) {
            return;
        }

        await this.expandMutex.exec(() => {
            if (this.loads.isBusy) {
                return;
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
            if (!group) {
                return;
            }

            const groupIdPart = groupId[keyPart];
            const range = groupIdPart.map((_, index) => index);
            const keepByKey = new Map();
            function keep(key) {
                let kept = keepByKey.get(key);
                if (kept === undefined) {
                    const idPart = JSON.parse(key)[keyPart];
                    kept =
                        range.some((index) => groupIdPart[index] !== idPart[index]) ||
                        idPart.length === groupIdPart.length;
                    keepByKey.set(key, kept);
                }
                return kept;
            }
            function omitKeys(object) {
                const newObject = {};
                for (const key of Object.keys(object)) {
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
        });
    }
    async expandAll() {
        if (this.loads.isBusy) {
            return;
        }
        const config = { metaData: this.metaData, data: this.data };
        if (await this._loadData(config, false)) {
            this.notify();
        }
    }
    /**
     * @param {string} groupId
     * @param {'row'|'col'} type
     */
    async expandGroup(groupId, type) {
        if (this.loads.isBusy) {
            return;
        }

        await this.expandMutex.exec(async () => {
            if (this.loads.isBusy) {
                return;
            }
            const config = { metaData: this.metaData, data: this.data };
            if (await this._expandGroup(/** @type {any} */ (groupId), type, config)) {
                this.notify();
            }
        });
    }
    /** @returns {Object} */
    exportData() {
        return formatPivotForExport(this.getTable(), this.metaData);
    }
    async flip() {
        await this.loads.whenIdle();
        await this.expandMutex.exec(async () => {
            await this.loads.whenIdle();
            let temp = this.data.rowGroupTree;
            this.data.rowGroupTree = this.data.colGroupTree;
            this.data.colGroupTree = temp;

            stripSortedKeys(this.data.rowGroupTree);
            stripSortedKeys(this.data.colGroupTree);

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

            this.metaData.sortedColumn = null;

            this.notify();
        });
    }
    /**
     * @param {Object} group
     * @returns {Array[]}
     */
    getGroupDomain(group) {
        const config = { metaData: this.metaData, data: this.data };
        return getGroupDomain(group, config);
    }
    /** @returns {Object} */
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
    /** @returns {number} */
    getTableWidth() {
        const leafCounts = getLeafCounts(this.data.colGroupTree);
        const leafCount =
            leafCounts[JSON.stringify(this.data.colGroupTree.root.values)];
        return computeExportedTableWidth(
            leafCount,
            this.metaData.activeMeasures.length,
        );
    }
    /** @returns {boolean} */
    hasData() {
        return hasData(this.data);
    }
    /** @param {Object} context */
    _dropArchGroupBysHiddenByContext(context) {
        if (this._archGroupBysResolved) {
            return;
        }
        this._archGroupBysResolved = true;
        const { fieldAttrs, rowGroupBys, colGroupBys } = this.metaData;
        this.metaData.rowGroupBys = visibleArchGroupBys(
            rowGroupBys,
            fieldAttrs,
            context,
        );
        this.metaData.colGroupBys = visibleArchGroupBys(
            colGroupBys,
            fieldAttrs,
            context,
        );
    }

    /**
     * @override
     * @param {SearchParams} searchParams
     */
    load(searchParams) {
        return this.loads.track(this._loadSearchParams(searchParams));
    }

    /** @param {SearchParams} searchParams */
    async _loadSearchParams(searchParams) {
        this.searchParams = searchParams;
        const rawPivotMeasures = searchParams.context.pivot_measures;
        const pivotMeasuresKey = JSON.stringify(rawPivotMeasures ?? null);
        let processedMeasures = null;
        if (pivotMeasuresKey !== this.lastPivotMeasuresKey) {
            processedMeasures = processMeasure(rawPivotMeasures);
        }
        const activeMeasures = processedMeasures || this.metaData.activeMeasures;
        this._dropArchGroupBysHiddenByContext(searchParams.context);
        const metaData = this._buildMetaData({ activeMeasures });
        if (!this.reload) {
            metaData.rowGroupBys = [
                ...(searchParams.context.pivot_row_groupby ||
                    (searchParams.groupBy.length
                        ? searchParams.groupBy
                        : metaData.rowGroupBys)),
            ];
        } else {
            metaData.rowGroupBys = [
                ...(searchParams.groupBy.length
                    ? searchParams.groupBy
                    : searchParams.context.pivot_row_groupby || metaData.rowGroupBys),
            ];
        }
        metaData.colGroupBys = [
            ...(searchParams.context.pivot_column_groupby || this.metaData.colGroupBys),
        ];

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
        metaData.activeMeasures = dropUnknownMeasures(
            metaData.activeMeasures,
            metaData.measures,
        );
        const config = { metaData, data: this.data };
        log.pipeline("load", () => ({
            resModel: metaData.resModel,
            reload: this.reload,
        }));
        let generation;
        const properties = this._keepLastAdd(
            addPropertyFieldDefs(
                this.orm,
                metaData.resModel,
                searchParams.context,
                metaData.fields,
                new Set([...metaData.rowGroupBys, ...metaData.colGroupBys]),
                () => generation === this.keepLast.generation,
            ),
        );
        generation = this.keepLast.generation;
        if (
            (await properties) === SUPERSEDED ||
            generation !== this.keepLast.generation
        ) {
            log.logic("property load superseded");
            return;
        }
        const endLoad = log.perf(`loadData ${metaData.resModel}`);
        const loaded = await this._loadData(config);
        endLoad({ loaded });
        if (loaded) {
            this.reload = true;
            this.lastPivotMeasuresKey = pivotMeasuresKey;
        }
    }
    /** @param {Object} sortedColumn */
    sortRows(sortedColumn) {
        if (this.loads.isBusy) {
            return;
        }

        const config = { metaData: this.metaData, data: this.data };
        this._sortRows(sortedColumn, config);

        this.notify();
    }
    /**
     * @param {string} fieldName
     * @returns {Promise}
     */
    async toggleMeasure(fieldName) {
        this.nextActiveMeasures = this.nextActiveMeasures || [
            ...this.metaData.activeMeasures,
        ];
        const activeMeasures = this.nextActiveMeasures;
        const epoch = ++this.measureToggleEpoch;
        const index = activeMeasures.indexOf(fieldName);
        try {
            if (index !== -1) {
                activeMeasures.splice(index, 1);
                while (this.loads.isBusy) {
                    await this.loads.whenIdle();
                }
                /** @type {any} */
                const metaData = this._buildMetaData();
                metaData.activeMeasures = activeMeasures;
                if (metaData.sortedColumn?.measure === fieldName) {
                    metaData.sortedColumn = null;
                }
                this.metaData = metaData;
            } else {
                activeMeasures.push(fieldName);
                const metaData = this._buildMetaData();
                metaData.activeMeasures = activeMeasures;
                const config = { metaData, data: this.data };
                if (!(await this._loadData(config))) {
                    return;
                }
                this.useSampleModel = false;
            }
            this.notify();
        } finally {
            if (epoch === this.measureToggleEpoch) {
                this.nextActiveMeasures = null;
            }
        }
    }

    /**
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
     * @protected
     * @param {Array[]} groupId
     * @param {'row'|'col'} type
     * @param {Config} config
     * @returns {Promise<boolean>}
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
        return this._subdivideGroup(group, divisors, config);
    }

    /**
     * @protected
     * @param {Promise<any>} promise
     * @returns {Promise<any>}
     */
    async _keepLastAdd(promise) {
        try {
            return await this.keepLast.add(promise);
        } catch (error) {
            if (error instanceof SupersededError) {
                return SUPERSEDED;
            }
            throw error;
        }
    }

    async _getGroupsSubdivision(params, groupInfo) {
        const { resModel, groupDomain, groupingSets, measureSpecs, kwargs } = params;
        const endSets = log.perf(`formattedReadGroupingSets ${resModel}`);
        const result = await this.orm.formattedReadGroupingSets(
            resModel,
            groupDomain,
            groupingSets,
            measureSpecs,
            kwargs,
        );
        endSets({ groupingSets: groupingSets.length, measures: measureSpecs.length });
        return groupInfo.map((info) => ({
            ...info,
            subGroups: result[info.subGroupIndex],
        }));
    }

    /**
     * @protected
     * @param {Config} config
     * @param {boolean} prune
     * @returns {Promise<boolean>}
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

        if (!(await this._subdivideGroup(group, divisors, config))) {
            return false;
        }

        if (prune && hasData(data) && hasData(this.data)) {
            if (
                symmetricalDifference(metaData.rowGroupBys, this.metaData.rowGroupBys)
                    .length === 0
            ) {
                removeMissingSubTrees(data.rowGroupTree, this.data.rowGroupTree);
            }
            if (
                symmetricalDifference(metaData.colGroupBys, this.metaData.colGroupBys)
                    .length === 0
            ) {
                removeMissingSubTrees(data.colGroupTree, this.data.colGroupTree);
            }
        }

        this.data = config.data;
        this.metaData = config.metaData;
        return true;
    }
    /**
     * @protected
     * @param {{ rowValues: any[], colValues: any[] }} group
     * @param {Object[]} groupSubdivisions
     * @param {Config} config
     */
    _prepareData(group, groupSubdivisions, config) {
        return aggregateSubdivisions(group, groupSubdivisions, config, {
            sortRows: (sortedColumn, cfg) => this._sortRows(sortedColumn, cfg),
            prepareGroupLabels: (grp, groupBys, cfg) =>
                this._getGroupLabels(grp, groupBys, cfg),
            prepareGroupValues: (grp, groupBys) => this._getGroupValues(grp, groupBys),
            prepareMeasureSpecs: (cfg) => this._getMeasureSpecs(cfg),
            prepareMeasurements: (subGroup, cfg, specs) =>
                this._getMeasurements(subGroup, cfg, specs),
        });
    }

    /**
     * @protected
     * @param {Config} config
     * @returns {string[]}
     */
    _getMeasureSpecs(config) {
        return getMeasureSpecs(config);
    }

    /**
     * @protected
     * @param {Record<string, any>} group
     * @param {string[]} groupBys
     * @returns {any[]}
     */
    _getGroupValues(group, groupBys) {
        return groupBys.map((gb) => this._sanitizeValue(group[this._normalize(gb)]));
    }

    /**
     * @protected
     * @param {Record<string, any>} group
     * @param {string[]} groupBys
     * @param {Config} config
     * @returns {any[]}
     */
    _getGroupLabels(group, groupBys, config) {
        return groupBys.map((gb) => {
            const groupBy = this._normalize(gb);
            return this._sanitizeLabel(group[groupBy], groupBy, config);
        });
    }

    /**
     * @protected
     * @param {string} groupBy
     * @returns {string}
     */
    _normalize(groupBy) {
        return normalize(groupBy, this.metaData.fields);
    }

    /**
     * @protected
     * @param {any} value
     * @returns {any}
     */
    _sanitizeValue(value) {
        return sanitizeValue(value);
    }

    /**
     * @protected
     * @param {any} value
     * @param {string} groupBy
     * @param {Config} config
     * @returns {string | number}
     */
    _sanitizeLabel(value, groupBy, config) {
        return sanitizeLabel(value, groupBy, config);
    }

    /**
     * @protected
     * @param {[any[], any[]]} groupId
     * @param {string} measureName
     * @param {Config} config
     * @returns {number|undefined}
     */
    _getCellValue(groupId, measureName, config) {
        const data = config.data || this.data;
        const cellKey = makeCellKey(
            JSON.stringify(groupId[0]),
            JSON.stringify(groupId[1]),
        );
        return getCellValue(cellKey, measureName, data);
    }

    /**
     * @protected
     * @param {Object} subGroup
     * @param {Config} config
     * @param {string[]} measureSpecs
     * @returns {Record<string, any>}
     */
    _getMeasurements(subGroup, config, measureSpecs) {
        return getMeasurements(subGroup, config, measureSpecs);
    }
    /**
     * @protected
     * @param {Object} group
     * @param {Array[]} divisors
     * @param {Config} config
     * @returns {Promise<boolean>}
     */
    async _subdivideGroup(group, divisors, config) {
        const { data } = config;
        const key = JSON.stringify([group.rowValues, group.colValues]);

        if (!(key in data.counts) || data.counts[key] > 0) {
            const subGroup = {
                rowValues: group.rowValues,
                colValues: group.colValues,
            };
            const groupDomainValue = getGroupDomain(subGroup, config);
            const measureSpecsList = this._getMeasureSpecs(config);
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
            const groupSubdivisions = await this._keepLastAdd(
                this._getGroupsSubdivision(params, groupInfo),
            );
            if (groupSubdivisions === SUPERSEDED) {
                return false;
            }
            if (groupSubdivisions.length) {
                this._prepareData(group, groupSubdivisions, config);
            }
        }
        return true;
    }
    /**
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
            const value =
                this._getCellValue(
                    [subTree.root.values, colGroupValues],
                    sortedColumn.measure,
                    config,
                ) || 0;
            return sortedColumn.order === "asc" ? value : -value;
        };

        sortTree(sortFunction, data.rowGroupTree);
    }
}
