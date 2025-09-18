// @ts-check

/** @module @web/model/sample_server - Fake ORM server generating realistic sample data for empty views */

import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import {
    cartesian,
    sortBy as arraySortBy,
    unique,
} from "@web/core/utils/collections/arrays";
import { ORM } from "@web/services/orm_service";

import { parseServerValue } from "./relational_model/utils";
import {
    DISPLAY_FORMATS,
    FORMATS,
    getSampleFromId,
    INTERVALS,
    MAIN_RECORDSET_SIZE,
    MAX_INTEGER,
    MAX_NUMBER_OPENED_GROUPS,
    MEASURE_SPEC_REGEX,
    SEARCH_READ_LIMIT,
    SUB_RECORDSET_SIZE,
} from "./sample_data";
import {
    generateFieldValue,
    getRandomInt,
    sanitizeNumber,
} from "./sample_field_generators";

/**
 * @typedef {{
 *   fieldName: string;
 *   func: string;
 *   name: string;
 * }} MeasureSpec
 *
 * @typedef {{
 *   fields: Record<string, any>;
 *   records: Record<string, any>[];
 * }} ModelData
 *
 * @typedef {{
 *   model: string;
 *   method?: string;
 *   route?: string;
 *   args?: any[];
 *   domain?: any[];
 *   groupBy?: string[];
 *   aggregates?: string[];
 *   specification?: Record<string, any>;
 *   recordIds?: number[];
 *   group_by?: string;
 *   progress_bar?: { field: string; colors: Record<string, string> };
 *   grouping_sets?: string[][];
 *   [key: string]: any;
 * }} MockRpcParams
 */

class UnimplementedRouteError extends Error {}

/**
 * @param {any[] | false} range
 * @param {any} field
 * @returns {string | false}
 */
function serializeGroupDateValue(range, field) {
    if (!range) {
        return false;
    }
    const dateValue = parseServerValue(field, range[0]);
    return field.type === "date"
        ? serializeDate(dateValue)
        : serializeDateTime(dateValue);
}

/**
 * Sample server class
 *
 * Represents a static instance of the server used when a RPC call sends
 * empty values/groups while the attribute 'sample' is set to true on the
 * view.
 *
 * This server will generate fake data and send them in the adequate format
 * according to the route/method used in the RPC.
 */
export class SampleServer {
    /**
     * @param {string} modelName
     * @param {Record<string, any>} fields
     */
    constructor(modelName, fields) {
        this.mainModel = modelName;
        this.data = {};
        this.data[modelName] = {
            fields,
            records: [],
        };
        // Generate relational fields' co models
        for (const fieldName in fields) {
            const field = fields[fieldName];
            if (["many2one", "one2many", "many2many"].includes(field.type)) {
                this.data[field.relation] = this.data[field.relation] || {
                    fields: {
                        display_name: { type: "char" },
                        id: { type: "integer" },
                        color: { type: "integer" },
                    },
                    records: [],
                };
            }
        }
        this.existingGroups = null;
        this.populated = false;
        this.existingGroupsPopulated = false;
    }

    //---------------------------------------------------------------------
    // Public
    //---------------------------------------------------------------------

    /**
     * Main entry point. Mocks a request to the server with sample data.
     *
     * @param {MockRpcParams} params
     * @returns {any}
     * @throws {Error} If called on a route/method we do not handle
     */
    mockRpc(params) {
        if (!(params.model in this.data)) {
            throw new Error(`SampleServer: unknown model ${params.model}`);
        }
        this._populateModels();
        switch (params.method || params.route) {
            case "web_search_read":
                return this._mockWebSearchReadUnity(params);
            case "web_read_group":
                return this._mockWebReadGroup(params);
            case "formatted_read_group":
                return this._mockFormattedReadGroup(params);
            case "formatted_read_grouping_sets":
                return this._mockFormattedReadGroupingSets(params);
            case "read_progress_bar":
                return this._mockReadProgressBar(params);
            case "read":
                return this._mockRead(params);
        }
        const method = params.method || params.route;
        const mockFunction =
            registry.category("sample_server").get(`${params.model}/${method}`, null) ||
            registry.category("sample_server").get(method, null);
        if (mockFunction) {
            return mockFunction.call(this, params);
        }
        console.warn(
            `SampleServer: unimplemented route "${params.method || params.route}"`,
        );
        throw new SampleServer.UnimplementedRouteError();
    }

    /**
     * @param {Record<string, any>[] | null} groups
     */
    setExistingGroups(groups) {
        this.existingGroups = groups;
    }

    //---------------------------------------------------------------------
    // Backward-compatible delegates (used by registry callbacks via .call)
    //---------------------------------------------------------------------

    /** @deprecated Use standalone generateFieldValue() from sample_field_generators */
    _generateFieldValue(modelName, fieldName) {
        const field = this.data[modelName]?.fields[fieldName];
        if (!field) {
            return false;
        }
        return generateFieldValue(modelName, fieldName, field, 1);
    }

    /** @deprecated Use standalone getRandomInt() from sample_field_generators */
    _getRandomInt(max) {
        return getRandomInt(max);
    }

    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    /**
     * @param {MeasureSpec[]} measures
     * @param {Record<string, any>[]} records
     * @returns {Record<string, any>}
     */
    _aggregateFields(measures, records) {
        const group = {};
        for (const { fieldName, func, name } of measures) {
            if (["sum", "sum_currency", "avg", "max", "min"].includes(func)) {
                if (!records.length) {
                    group[name] = false;
                } else {
                    group[name] = 0;
                    for (const record of records) {
                        group[name] += record[fieldName];
                    }
                }
                group[name] = sanitizeNumber(group[name]);
            } else if (func === "array_agg") {
                group[name] = records.map((r) => r[fieldName]);
            } else if (func === "__count") {
                group[name] = records.length;
            } else if (func === "count_distinct") {
                group[name] = unique(records.map((r) => r[fieldName])).filter(
                    Boolean,
                ).length;
            } else if (func === "bool_or") {
                group[name] = records.some((r) => Boolean(r[fieldName]));
            } else if (func === "bool_and") {
                group[name] = records.every((r) => Boolean(r[fieldName]));
            } else if (func === "array_agg_distinct") {
                group[name] = unique(records.map((r) => r[fieldName]));
            } else {
                throw new Error(`Aggregate "${func}" not implemented in SampleServer`);
            }
        }
        return group;
    }

    /**
     * @param {any} value
     * @param {any} options
     * @returns {any}
     */
    _formatValue(value, options) {
        if (!value) {
            return false;
        }
        const { type, interval, relation } = options;
        if (["date", "datetime"].includes(type) && value) {
            const deserialize = type === "date" ? deserializeDate : deserializeDateTime;
            const serialize = type === "date" ? serializeDate : serializeDateTime;
            const from = deserialize(value).startOf(interval);
            const fmt = FORMATS[interval];
            return [serialize(from), from.toFormat(fmt)];
        } else if (["many2one", "many2many"].includes(type)) {
            const rec = this.data[relation].records.find(({ id }) => id === value);
            return [value, rec.display_name];
        } else {
            return value;
        }
    }

    /**
     * @private
     * @param {MockRpcParams} params
     * @returns {any[]}
     */
    _mockRead(params) {
        const model = this.data[params.model];
        const ids = params.args[0];
        const fieldNames = params.args[1];
        const records = [];
        for (const r of model.records) {
            if (!ids.includes(r.id)) {
                continue;
            }
            const record = { id: r.id };
            for (const fieldName of fieldNames) {
                const field = model.fields[fieldName];
                if (!field) {
                    record[fieldName] = false;
                } else if (field.type === "many2one") {
                    const relModel = this.data[field.relation];
                    const relRecord = relModel.records.find(
                        (relR) => r[fieldName] === relR.id,
                    );
                    record[fieldName] = relRecord
                        ? [relRecord.id, relRecord.display_name]
                        : false;
                } else {
                    record[fieldName] = r[fieldName];
                }
            }
            records.push(record);
        }
        return records;
    }

    /**
     * @param {MockRpcParams} params
     * @returns {any[]}
     */
    _mockFormattedReadGroup(params) {
        const model = params.model;
        const groupBy = params.groupBy;
        const fields = this.data[model].fields;
        const records = this.data[model].records;
        const normalizedGroupBys = [];

        for (const groupBySpec of groupBy) {
            const [fieldName, interval] = groupBySpec.split(":");
            const { type, relation } = fields[fieldName];
            if (type) {
                normalizedGroupBys.push({
                    fieldName,
                    type,
                    interval,
                    relation,
                    alias: groupBySpec,
                });
            }
        }

        const groupsFromRecord = (record) => {
            const values = [];
            for (const gb of normalizedGroupBys) {
                const { fieldName, type, alias } = gb;
                let fieldVals;
                if (["date", "datetime"].includes(type)) {
                    fieldVals = [this._formatValue(record[fieldName], gb)];
                } else if (type === "many2many") {
                    fieldVals = record[fieldName].length ? record[fieldName] : [false];
                } else {
                    fieldVals = [record[fieldName]];
                }
                values.push(fieldVals.map((val) => ({ [alias]: val })));
            }
            const cart = cartesian(...values);
            return cart.map((tuple) => {
                if (!Array.isArray(tuple)) {
                    tuple = [tuple];
                }
                return Object.assign({}, ...tuple);
            });
        };

        const groups = {};
        for (const record of records) {
            const recordGroups = groupsFromRecord(record);
            for (const group of recordGroups) {
                const groupId = JSON.stringify(group);
                if (!(groupId in groups)) {
                    groups[groupId] = [];
                }
                groups[groupId].push(record);
            }
        }

        const aggregates = params.aggregates || [];
        const measures = [];
        for (const measureSpec of aggregates) {
            if (measureSpec === "__count") {
                measures.push({
                    fieldName: "__count",
                    func: "__count",
                    name: measureSpec,
                });
                continue;
            }
            const matches = measureSpec.match(MEASURE_SPEC_REGEX);
            if (!matches) {
                throw new Error(
                    `Invalidate Aggregate "${measureSpec}" in SampleServer`,
                );
            }
            const { fieldName, func } = matches.groups;
            measures.push({ fieldName, func, name: measureSpec });
        }

        let result = [];
        for (const id in groups) {
            const records = groups[id];
            const group = { __extra_domain: [] };
            const firstElem = records[0];
            const parsedId = JSON.parse(id);
            for (const gb of normalizedGroupBys) {
                const { alias, fieldName, type } = gb;
                if (type === "many2many") {
                    group[alias] = this._formatValue(parsedId[fieldName], gb);
                } else {
                    group[alias] = this._formatValue(firstElem[fieldName], gb);
                }
            }
            Object.assign(group, this._aggregateFields(measures, records));
            result.push(group);
        }
        if (normalizedGroupBys.length > 0) {
            const { alias, type } = normalizedGroupBys[0];
            result = arraySortBy(result, (group) => {
                const val = group[alias];
                if (type === "datetime") {
                    return deserializeDateTime(val);
                } else if (type === "date") {
                    return deserializeDate(val);
                }
                return val;
            });
        }
        return result;
    }

    /**
     * @param {MockRpcParams} params
     * @returns {any[][]}
     */
    _mockFormattedReadGroupingSets(params) {
        const res = [];
        for (const groupBy of params.grouping_sets) {
            res.push(this._mockFormattedReadGroup({ ...params, groupBy }));
        }
        return res;
    }

    /**
     * @private
     * @param {MockRpcParams} params
     * @returns {any}
     */
    _mockReadProgressBar(params) {
        const groupBy = params.group_by;
        const progressBar = params.progress_bar;
        const groups = this._mockFormattedReadGroup({
            model: params.model,
            domain: params.domain,
            groupBy: [groupBy, progressBar.field],
            aggregates: ["__count"],
        });
        const data = {};
        for (const group of groups) {
            let groupByValue = group[groupBy];
            if (Array.isArray(groupByValue)) {
                groupByValue = groupByValue[0];
            }
            if (!(groupByValue in data)) {
                if (groupByValue === true) {
                    groupByValue = "True";
                } else if (groupByValue === false) {
                    groupByValue = "False";
                }
            }
            if (!(groupByValue in data)) {
                data[groupByValue] = {};
                for (const key in progressBar.colors) {
                    data[groupByValue][key] = 0;
                }
            }
            data[groupByValue][group[progressBar.field]] += group.__count;
        }
        return data;
    }

    /**
     * @private
     * @param {MockRpcParams} params
     * @returns {{ records: Record<string, any>[]; length: number }}
     */
    _mockWebSearchReadUnity(params) {
        const fields = Object.keys(params.specification);
        const model = this.data[params.model];
        let rawRecords = model.records;
        if ("recordIds" in params) {
            rawRecords = model.records.filter((record) =>
                params.recordIds.includes(record.id),
            );
        } else {
            rawRecords = rawRecords.slice(0, SEARCH_READ_LIMIT);
        }
        const records = this._mockRead({
            model: params.model,
            args: [rawRecords.map((r) => r.id), fields],
        });
        const result = { records, length: records.length };
        for (const fieldName in params.specification) {
            const field = this.data[params.model].fields[fieldName];
            if (field.type === "many2one") {
                for (const record of result.records) {
                    record[fieldName] = record[fieldName]
                        ? {
                              id: record[fieldName][0],
                              display_name: record[fieldName][1],
                          }
                        : false;
                }
            }
            if (field.type === "one2many" || field.type === "many2many") {
                const relFields = Object.keys(
                    params.specification[fieldName].fields || {},
                );
                if (relFields.length) {
                    const relIds = result.records.map((r) => r[fieldName]).flat();
                    const relRecords = {};
                    const _relRecords = this._mockRead({
                        model: field.relation,
                        args: [relIds, relFields],
                    });
                    for (const relRecord of _relRecords) {
                        relRecords[relRecord.id] = relRecord;
                    }
                    for (const record of result.records) {
                        record[fieldName] = record[fieldName].map(
                            (resId) => relRecords[resId],
                        );
                    }
                }
            }
        }
        return result;
    }

    /**
     * @private
     * @param {MockRpcParams} params
     * @returns {{ groups: Record<string, any>[]; length: number }}
     */
    _mockWebReadGroup(params) {
        const aggregates = [...params.aggregates, "__count"];
        if (params.unfold_read_specification) {
            aggregates.push("id:array_agg");
        }
        let groups;
        if (this.existingGroups) {
            this._tweakExistingGroups({ ...params, aggregates });
            groups = this.existingGroups;
        } else {
            groups = this._mockFormattedReadGroup({ ...params, aggregates });
        }
        const openAllGroups = params.auto_unfold && !this.existingGroups;
        let nbOpenedGroup = 0;
        if (params.unfold_read_specification) {
            for (const group of groups) {
                if (openAllGroups || "__records" in group) {
                    if (nbOpenedGroup < MAX_NUMBER_OPENED_GROUPS) {
                        nbOpenedGroup++;
                        group.__records = this._mockWebSearchReadUnity({
                            model: params.model,
                            specification: params.unfold_read_specification,
                            recordIds: group["id:array_agg"],
                        }).records;
                    }
                }
                delete group["id:array_agg"];
            }
        }
        return {
            groups,
            length: groups.length,
        };
    }

    /**
     * @private
     * @param {MockRpcParams} params
     */
    _populateExistingGroups(params) {
        const groups = this.existingGroups;
        const groupBy = params.groupBy[0].split(":")[0];
        const groupByField = this.data[params.model].fields[groupBy];
        const groupedByM2O = groupByField.type === "many2one";
        if (groupedByM2O) {
            this.data[groupByField.relation].records = groups.map((g) => ({
                id: g[groupBy][0],
                display_name: g[groupBy][1],
            }));
        }
        for (const r of this.data[params.model].records) {
            const group = getSampleFromId(r.id, groups);
            if (["date", "datetime"].includes(groupByField.type)) {
                r[groupBy] = serializeGroupDateValue(
                    group[params.groupBy[0]],
                    groupByField,
                );
            } else if (groupByField.type === "many2one") {
                r[groupBy] = group[params.groupBy[0]]
                    ? group[params.groupBy[0]][0]
                    : false;
            } else {
                r[groupBy] = group[params.groupBy[0]];
            }
        }
    }

    /**
     * Generates sample records for all models in this.data.
     * @private
     */
    _populateModels() {
        if (!this.populated) {
            for (const modelName in this.data) {
                const model = this.data[modelName];
                const fieldNames = Object.keys(model.fields).filter((f) => f !== "id");
                const size =
                    modelName === this.mainModel
                        ? MAIN_RECORDSET_SIZE
                        : SUB_RECORDSET_SIZE;
                for (let id = 1; id <= size; id++) {
                    const record = { id };
                    for (const fieldName of fieldNames) {
                        record[fieldName] = generateFieldValue(
                            modelName,
                            fieldName,
                            model.fields[fieldName],
                            id,
                        );
                    }
                    model.records.push(record);
                }
            }
            this.populated = true;
        }
    }

    /**
     * @private
     * @param {MockRpcParams} params
     */
    _tweakExistingGroups(params) {
        const groups = this.existingGroups;
        this._populateExistingGroups(params);

        const fullGroupBy = params.groupBy[0];
        const groupBy = fullGroupBy.split(":")[0];
        const groupByField = this.data[params.model].fields[groupBy];
        const records = this.data[params.model].records;
        for (const g of groups) {
            const recordsInGroup = records.filter((r) => {
                if (["date", "datetime"].includes(groupByField.type)) {
                    return (
                        r[groupBy] ===
                        serializeGroupDateValue(g[fullGroupBy], groupByField)
                    );
                } else if (groupByField.type === "many2one") {
                    return (
                        (!r[groupBy] && !g[fullGroupBy]) ||
                        r[groupBy] === g[fullGroupBy][0]
                    );
                }
                return r[groupBy] === g[fullGroupBy];
            });
            for (const aggregateSpec of params.aggregates || []) {
                if (aggregateSpec === "__count") {
                    g.__count = recordsInGroup.length;
                    continue;
                }
                const [fieldName, func] = aggregateSpec.split(":");
                if (func === "array_agg") {
                    g[aggregateSpec] = recordsInGroup.map((r) => r[fieldName]);
                } else if (
                    ["integer, float", "monetary"].includes(
                        this.data[params.model].fields[fieldName].type,
                    )
                ) {
                    g[aggregateSpec] = recordsInGroup.reduce(
                        (acc, r) => acc + r[fieldName],
                        0,
                    );
                }
            }
        }
    }
}

// Static properties — re-exported from sample_data for backward compatibility
SampleServer.FORMATS = FORMATS;
SampleServer.INTERVALS = INTERVALS;
SampleServer.DISPLAY_FORMATS = DISPLAY_FORMATS;
SampleServer.MAIN_RECORDSET_SIZE = MAIN_RECORDSET_SIZE;
SampleServer.SUB_RECORDSET_SIZE = SUB_RECORDSET_SIZE;
SampleServer.SEARCH_READ_LIMIT = SEARCH_READ_LIMIT;
SampleServer.MAX_INTEGER = MAX_INTEGER;
SampleServer.UnimplementedRouteError = UnimplementedRouteError;

/**
 * Build an ORM instance backed by a SampleServer for fake data rendering.
 *
 * @param {string} resModel
 * @param {{[key: string]: any}} fields
 * @param {any} user
 * @returns {any}
 */
export function buildSampleORM(resModel, fields, user) {
    const sampleServer = new SampleServer(resModel, fields);
    const fakeRPC = async (/** @type {any} */ _, /** @type {any} */ params) => {
        const { args, kwargs, method, model } = params;
        const { groupby: groupBy } = kwargs;
        return sampleServer.mockRpc({
            method,
            model,
            args,
            ...kwargs,
            groupBy,
        });
    };
    /** @type {any} */
    const sampleORM = new /** @type {any} */ (ORM)(user);
    sampleORM.rpc = fakeRPC;
    sampleORM.isSample = true;
    sampleORM.cache = () => sampleORM;
    sampleORM.setGroups = (/** @type {any} */ groups) =>
        sampleServer.setExistingGroups(groups);
    return sampleORM;
}
