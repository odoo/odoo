// @ts-check
/** @odoo-module native */

import { isX2Many } from "@web/core/field_types";
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

import { parseServerValue } from "./relational_model/field_values.js";
import {
    DISPLAY_FORMATS,
    FORMATS,
    getSampleFromId,
    MAIN_RECORDSET_SIZE,
    MAX_INTEGER,
    MAX_NUMBER_OPENED_GROUPS,
    MEASURE_SPEC_REGEX,
    SEARCH_READ_LIMIT,
    SUB_RECORDSET_SIZE,
} from "./sample_data.js";
import {
    generateFieldValue,
    getRandomArrayEl,
    getRandomBool,
    getRandomInt,
    getRandomSubRecordId,
    sanitizeNumber,
} from "./sample_field_generators.js";

/**
 * @typedef {{
 * fieldName: string;
 * func: string;
 * name: string;
 * }} MeasureSpec
 * @typedef {{
 * fields: Record<string, any>;
 * records: Record<string, any>[];
 * }} ModelData
 * @typedef {{
 * model: string;
 * method?: string;
 * route?: string;
 * args?: any[];
 * domain?: any[];
 * groupBy?: string[];
 * aggregates?: string[];
 * specification?: Record<string, any>;
 * recordIds?: number[];
 * group_by?: string;
 * progress_bar?: { field: string; colors: Record<string, string> };
 * grouping_sets?: string[][];
 * [key: string]: any;
 * }} MockRpcParams
 */

registry
    .category("sample_server")
    .addValidation((entry) => typeof entry === "function");

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

export class SampleServer {
    /**
     * @param {string} modelName
     * @param {Record<string, any>} fields
     * @param {Record<string, Record<string, any>>} [relatedModels]
     */
    constructor(modelName, fields, relatedModels = {}) {
        this.mainModel = modelName;
        this.data = {};
        this.data[modelName] = {
            fields,
            records: [],
        };
        for (const fieldName of Object.keys(fields)) {
            const field = fields[fieldName];
            if (["many2one", "one2many", "many2many"].includes(field.type)) {
                this.data[field.relation] = this.data[field.relation] || {
                    fields: {
                        display_name: { type: "char" },
                        id: { type: "integer" },
                        color: { type: "integer" },
                        ...relatedModels[field.relation],
                    },
                    records: [],
                };
            }
        }
        this.existingGroups = null;
        this.populated = false;
    }

    /**
     * @param {MockRpcParams} params
     * @returns {any}
     * @throws {Error}
     */
    mockRpc(params) {
        if (!(params.model in this.data)) {
            throw new Error(`SampleServer: unknown model ${params.model}`);
        }
        this._createSampleRecords();
        switch (params.method || params.route) {
            case "web_search_read":
                return this._mockWebSearchReadUnity(params);
            case "web_read":
                return this._mockWebRead(params);
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

    /** @param {Record<string, any>[] | null} groups */
    setExistingGroups(groups) {
        this.existingGroups = groups;
    }

    /**
     * @param {any[]} array
     * @returns {any}
     */
    _getRandomArrayEl(array) {
        return getRandomArrayEl(array);
    }

    /** @returns {boolean} */
    _getRandomBool() {
        return getRandomBool();
    }

    /** @returns {number} */
    _getRandomSubRecordId() {
        return getRandomSubRecordId();
    }

    /**
     * @param {string} modelName
     * @param {string} fieldName
     * @param {number} [id]
     * @returns {any}
     */
    _generateFieldValue(modelName, fieldName, id) {
        const field = this.data[modelName].fields[fieldName];
        return generateFieldValue(modelName, fieldName, field, id, {
            getRandomBool: () => this._getRandomBool(),
            getRandomSubRecordId: () => this._getRandomSubRecordId(),
            getRandomArrayEl: (array) => this._getRandomArrayEl(array),
        });
    }

    /**
     * @param {number} max
     * @returns {number}
     */
    _getRandomInt(max) {
        return getRandomInt(max);
    }

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
                } else if (func === "max") {
                    group[name] = Math.max(...records.map((r) => r[fieldName]));
                } else if (func === "min") {
                    group[name] = Math.min(...records.map((r) => r[fieldName]));
                } else {
                    group[name] = 0;
                    for (const record of records) {
                        group[name] += record[fieldName];
                    }
                    if (func === "avg") {
                        group[name] /= records.length;
                    }
                }
                group[name] = sanitizeNumber(group[name]);
            } else if (func === "array_agg") {
                group[name] = records.map((r) => r[fieldName]);
            } else if (func === "__count") {
                group[name] = records.length;
            } else if (func === "count") {
                group[name] = records.filter(
                    (record) => record[fieldName] != null,
                ).length;
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
     * @param {string} modelName
     * @param {string} groupBySpec
     * @returns {{ fieldName: string, type: string, interval: string | undefined,
     * relation: string | undefined, alias: string, field: Record<string, any> } | undefined}
     */
    _resolveGroupBy(modelName, groupBySpec) {
        const [fieldName, interval] = groupBySpec.split(":");
        const field = this.data[modelName].fields[fieldName];
        if (!field?.type) {
            return undefined;
        }
        return {
            fieldName,
            type: field.type,
            interval,
            relation: field.relation,
            alias: groupBySpec,
            field,
        };
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
            return [value, rec ? rec.display_name : `Record ${value}`];
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
        const [ids, fieldNames] = params.args ?? [];
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
                    if (!relModel) {
                        record[fieldName] = false;
                        continue;
                    }
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
     * @param {string} model
     * @param {string[]} groupBy
     * @returns {any[]}
     */
    _normalizeGroupBys(model, groupBy) {
        const normalized = [];
        for (const groupBySpec of groupBy) {
            const gb = this._resolveGroupBy(model, groupBySpec);
            if (gb) {
                normalized.push(gb);
            }
        }
        return normalized;
    }

    /**
     * @param {Record<string, any>} record
     * @param {any[]} normalizedGroupBys
     * @returns {Record<string, any>[]}
     */
    _groupKeysOf(record, normalizedGroupBys) {
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
        return cartesian(...values).map((tuple) => {
            if (!Array.isArray(tuple)) {
                tuple = [tuple];
            }
            return Object.assign({}, ...tuple);
        });
    }

    /**
     * @param {string[]} aggregates
     * @returns {MeasureSpec[]}
     */
    _parseMeasures(aggregates) {
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
                throw new Error(`Invalid Aggregate "${measureSpec}" in SampleServer`);
            }
            const { fieldName, func } = matches.groups;
            measures.push({ fieldName, func, name: measureSpec });
        }
        return measures;
    }

    /**
     * @param {Record<string, any>[]} groups
     * @param {any} firstGroupBy
     * @returns {Record<string, any>[]}
     */
    _sortGroups(groups, firstGroupBy) {
        const { alias, type } = firstGroupBy;
        return arraySortBy(groups, (group) => {
            const val = group[alias];
            if (type === "datetime") {
                return deserializeDateTime(Array.isArray(val) ? val[0] : val);
            } else if (type === "date") {
                return deserializeDate(Array.isArray(val) ? val[0] : val);
            }
            return val;
        });
    }

    /**
     * @param {MockRpcParams} params
     * @returns {any[]}
     */
    _mockFormattedReadGroup(params) {
        const model = params.model;
        const records = this.data[model].records;
        const normalizedGroupBys = this._normalizeGroupBys(model, params.groupBy);

        /** @type {Record<string, Record<string, any>[]>} */
        const buckets = {};
        for (const record of records) {
            for (const key of this._groupKeysOf(record, normalizedGroupBys)) {
                const groupId = JSON.stringify(key);
                buckets[groupId] = buckets[groupId] || [];
                buckets[groupId].push(record);
            }
        }

        const measures = this._parseMeasures(params.aggregates || []);
        let result = [];
        for (const id of Object.keys(buckets)) {
            const bucket = buckets[id];
            /** @type {Record<string, any>} */
            const group = { __extra_domain: [] };
            const parsedId = JSON.parse(id);
            for (const gb of normalizedGroupBys) {
                const { alias, fieldName, type } = gb;
                group[alias] =
                    type === "many2many"
                        ? this._formatValue(parsedId[alias], gb)
                        : this._formatValue(bucket[0][fieldName], gb);
            }
            Object.assign(group, this._aggregateFields(measures, bucket));
            result.push(group);
        }
        if (normalizedGroupBys.length) {
            result = this._sortGroups(result, normalizedGroupBys[0]);
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
            if (typeof groupByValue === "boolean") {
                groupByValue = groupByValue ? "True" : "False";
            }
            if (!(groupByValue in data)) {
                data[groupByValue] = {};
                for (const key of Object.keys(progressBar.colors)) {
                    data[groupByValue][key] = 0;
                }
            }
            const bucket = group[progressBar.field];
            if (bucket in data[groupByValue]) {
                data[groupByValue][bucket] += group.__count;
            }
        }
        return data;
    }

    /**
     * @private
     * @param {MockRpcParams} params
     * @returns {Record<string, any>[]}
     */
    _mockWebRead(params) {
        return this._mockWebSearchReadUnity({
            ...params,
            recordIds: params.args[0],
        }).records;
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
        for (const fieldName of Object.keys(params.specification)) {
            const field = this.data[params.model].fields[fieldName];
            if (!field) {
                continue;
            }
            if (field.type === "many2one") {
                const relFields = Object.keys(
                    params.specification[fieldName].fields || {},
                ).filter((relField) => relField !== "display_name");
                const relRecords = {};
                if (relFields.length) {
                    const relIds = result.records
                        .map((record) => record[fieldName] && record[fieldName][0])
                        .filter((id) => id);
                    for (const relRecord of this._mockRead({
                        model: field.relation,
                        args: [relIds, relFields],
                    })) {
                        relRecords[relRecord.id] = relRecord;
                    }
                }
                for (const record of result.records) {
                    record[fieldName] = record[fieldName]
                        ? {
                              ...relRecords[record[fieldName][0]],
                              id: record[fieldName][0],
                              display_name: record[fieldName][1],
                          }
                        : false;
                }
            }
            if (isX2Many(field)) {
                const relFields = Object.keys(
                    params.specification[fieldName].fields || {},
                );
                if (relFields.length) {
                    const relIds = result.records.flatMap((r) => r[fieldName]);
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
            this._updateExistingGroupAggregates({ ...params, aggregates });
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
        if (params.groupby_read_specification && params.groupBy?.length) {
            const groupBy = params.groupBy[0];
            const readSpec = params.groupby_read_specification[groupBy];
            const field = this.data[params.model].fields[groupBy.split(":")[0]];
            if (readSpec && field?.relation) {
                for (const group of groups) {
                    const value = group[groupBy.split(":")[0]];
                    group.__values = Array.isArray(value)
                        ? this._mockWebSearchReadUnity({
                              model: field.relation,
                              specification: readSpec.fields || {},
                              recordIds: [value[0]],
                          }).records[0] || { id: false }
                        : { id: false };
                }
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
    _updateRecordsWithGroups(params) {
        const groups = this.existingGroups;
        const gb = this._resolveGroupBy(params.model, params.groupBy[0]);
        if (!gb) {
            return;
        }
        const { fieldName, alias, field } = gb;
        if (gb.type === "many2one") {
            this.data[gb.relation].records = groups
                .filter((g) => g[fieldName])
                .map((g) => ({
                    id: g[fieldName][0],
                    display_name: g[fieldName][1],
                }));
        }
        for (const r of this.data[params.model].records) {
            const group = getSampleFromId(r.id, groups);
            if (["date", "datetime"].includes(gb.type)) {
                r[fieldName] = serializeGroupDateValue(group[alias], field);
            } else if (gb.type === "many2one") {
                r[fieldName] = group[alias] ? group[alias][0] : false;
            } else {
                r[fieldName] = group[alias];
            }
        }
    }

    /** @private */
    _createSampleRecords() {
        if (!this.populated) {
            for (const modelName of Object.keys(this.data)) {
                const model = this.data[modelName];
                const fieldNames = Object.keys(model.fields).filter((f) => f !== "id");
                const size =
                    modelName === this.mainModel
                        ? MAIN_RECORDSET_SIZE
                        : SUB_RECORDSET_SIZE;
                for (let id = 1; id <= size; id++) {
                    const record = { id };
                    for (const fieldName of fieldNames) {
                        record[fieldName] = this._generateFieldValue(
                            modelName,
                            fieldName,
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
    _updateExistingGroupAggregates(params) {
        const groups = this.existingGroups;
        const gb = this._resolveGroupBy(params.model, params.groupBy[0]);
        if (!gb) {
            return;
        }
        this._updateRecordsWithGroups(params);

        const { fieldName: groupBy, alias, field } = gb;
        const records = this.data[params.model].records;
        for (const g of groups) {
            const recordsInGroup = records.filter((/** @type {any} */ r) => {
                if (["date", "datetime"].includes(gb.type)) {
                    return r[groupBy] === serializeGroupDateValue(g[alias], field);
                } else if (gb.type === "many2one") {
                    return (
                        (!r[groupBy] && !g[alias]) ||
                        (g[alias] && r[groupBy] === g[alias][0])
                    );
                }
                return r[groupBy] === g[alias];
            });
            Object.assign(
                g,
                this._aggregateFields(
                    this._parseMeasures(params.aggregates || []),
                    recordsInGroup,
                ),
            );
        }
    }
}

SampleServer.FORMATS = FORMATS;
SampleServer.DISPLAY_FORMATS = DISPLAY_FORMATS;
SampleServer.MAIN_RECORDSET_SIZE = MAIN_RECORDSET_SIZE;
SampleServer.SUB_RECORDSET_SIZE = SUB_RECORDSET_SIZE;
SampleServer.MAX_INTEGER = MAX_INTEGER;
SampleServer.UnimplementedRouteError = UnimplementedRouteError;

/**
 * @param {string} resModel
 * @param {{[key: string]: any}} fields
 * @param {any} orm
 * @returns {any}
 */
export function makeSampleORM(resModel, fields, orm, relatedModels) {
    const sampleServer = new SampleServer(resModel, fields, relatedModels);
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
    const sampleORM = Object.create(orm);
    sampleORM.rpc = fakeRPC;
    sampleORM.isSample = true;
    sampleORM.cache = () => sampleORM;
    sampleORM.setGroups = (/** @type {any} */ groups) =>
        sampleServer.setExistingGroups(groups);
    return sampleORM;
}
