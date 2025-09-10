import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { ORM } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { cartesian, sortBy as arraySortBy, unique } from "@web/core/utils/arrays";
import { parseServerValue } from "./relational_model/utils";

class UnimplementedRouteError extends Error {}

/**
 * Helper function returning the value from a list of sample strings
 * corresponding to the given ID.
 * @param {number} id
 * @param {string[]} sampleTexts
 * @returns {string}
 */
function getSampleFromId(id, sampleTexts) {
    return sampleTexts[(id - 1) % sampleTexts.length];
}

function serializeGroupDateValue(range, field) {
    if (!range) {
        return false;
    }
    const dateValue = parseServerValue(field, range[0]);
    return field.type === "date" ? serializeDate(dateValue) : serializeDateTime(dateValue);
}

/**
 * Helper function returning a regular expression specifically matching
 * a given 'term' in a fieldName. For example `fieldNameRegex('abc')`:
 * will match:
 * - "abc"
 * - "field_abc__def"
 * will not match:
 * - "aabc"
 * - "abcd_ef"
 * @param {...string} term
 * @returns {RegExp}
 */
function fieldNameRegex(...terms) {
    return new RegExp(`\\b((\\w+)?_)?(${terms.join("|")})(_(\\w+)?)?\\b`);
}

const MEASURE_SPEC_REGEX = /(?<fieldName>\w+):(?<func>\w+)/;
const DESCRIPTION_REGEX = fieldNameRegex("description", "label", "title", "subject", "message");
const EMAIL_REGEX = fieldNameRegex("email");
const PHONE_REGEX = fieldNameRegex("phone");
const URL_REGEX = fieldNameRegex("url");
const MAX_NUMBER_OPENED_GROUPS = 10;

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
     * @param {Object} fields
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
        // On some models, empty grouped Kanban or List view still contain
        // real (empty) groups. In this case, we re-use the result of the
        // web_read_group rpc to tweak sample data s.t. those real groups
        // contain sample records.
        this.existingGroups = null;
        // Sample records generation is only done if necessary, so we delay
        // it to the first "mockRPC" call. These flags allow us to know if
        // the records have been generated or not.
        this.populated = false;
        this.existingGroupsPopulated = false;
    }

    //---------------------------------------------------------------------
    // Public
    //---------------------------------------------------------------------

    /**
     * This is the main entry point of the SampleServer. Mocks a request to
     * the server with sample data.
     * @param {Object} params
     * @returns {any} the result obtained with the sample data
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
        // this rpc can't be mocked by the SampleServer itself, so check if there is an handler
        // in the registry: either specific for this model (with key 'model/method'), or
        // global (with key 'method')
        const method = params.method || params.route;
        // This allows to register mock version of methods or routes,
        // for all models:
        // registry.category("sample_server").add('some_route', () => "abcd");
        // for a specific model (e.g. 'res.partner'):
        // registry.category("sample_server").add('res.partner/some_method', () => 23);
        const mockFunction =
            registry.category("sample_server").get(`${params.model}/${method}`, null) ||
            registry.category("sample_server").get(method, null);
        if (mockFunction) {
            return mockFunction.call(this, params);
        }
        console.log(`SampleServer: unimplemented route "${params.method || params.route}"`);
        throw new SampleServer.UnimplementedRouteError();
    }

    setExistingGroups(groups) {
        this.existingGroups = groups;
    }

    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    /**
     * @param {Object[]} measures, each measure has the form { fieldName, type }
     * @param {Object[]} records
     * @returns {Object}
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
                group[name] = this._sanitizeNumber(group[name]);
            } else if (func === "array_agg") {
                group[name] = records.map((r) => r[fieldName]);
            } else if (func === "__count") {
                group[name] = records.length;
            } else if (func === "count_distinct") {
                group[name] = unique(records.map((r) => r[fieldName])).filter(Boolean).length;
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
     * @param {Object} options
     * @param {string} [options.interval]
     * @param {string} [options.relation]
     * @param {string} [options.type]
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
            const fmt = SampleServer.FORMATS[interval];
            return [serialize(from), from.toFormat(fmt)];
        } else if (["many2one", "many2many"].includes(type)) {
            const rec = this.data[relation].records.find(({ id }) => id === value);
            return [value, rec.display_name];
        } else {
            return value;
        }
    }

    /**
     * Generates field values based on heuristics according to field types
     * and names.
     *
     * @private
     * @param {string} modelName
     * @param {string} fieldName
     * @param {number} id the record id
     * @returns {any} the field value
     */
    _generateFieldValue(modelName, fieldName, id) {
        const field = this.data[modelName].fields[fieldName];
        switch (field.type) {
            case "boolean":
                return fieldName === "active" ? true : this._getRandomBool();
            case "char":
            case "text":
                if (["display_name", "name"].includes(fieldName)) {
                    if (SampleServer.PEOPLE_MODELS.includes(modelName)) {
                        return getSampleFromId(id, SampleServer.SAMPLE_PEOPLE);
                    } else if (modelName === "res.country") {
                        return getSampleFromId(id, SampleServer.SAMPLE_COUNTRIES);
                    }
                }
                if (fieldName === "display_name") {
                    return getSampleFromId(id, SampleServer.SAMPLE_TEXTS);
                } else if (["name", "reference"].includes(fieldName)) {
                    return `REF${String(id).padStart(4, "0")}`;
                } else if (DESCRIPTION_REGEX.test(fieldName)) {
                    return getSampleFromId(id, SampleServer.SAMPLE_TEXTS);
                } else if (EMAIL_REGEX.test(fieldName)) {
                    const emailName = getSampleFromId(id, SampleServer.SAMPLE_PEOPLE)
                        .replace(/ /, ".")
                        .toLowerCase();
                    return `${emailName}@sample.demo`;
                } else if (PHONE_REGEX.test(fieldName)) {
                    return `+1 555 754 ${String(id).padStart(4, "0")}`;
                } else if (URL_REGEX.test(fieldName)) {
                    return `http://sample${id}.com`;
                }
                return false;
            case "date":
            case "datetime": {
                const datetime = this._getRandomDate();
                return field.type === "date"
                    ? serializeDate(datetime)
                    : serializeDateTime(datetime);
            }
            case "float":
                return this._getRandomFloat(SampleServer.MAX_FLOAT);
            case "integer": {
                let max = SampleServer.MAX_INTEGER;
                if (fieldName.includes("color")) {
                    max = this._getRandomBool() ? SampleServer.MAX_COLOR_INT : 0;
                }
                return this._getRandomInt(max);
            }
            case "monetary":
                return this._getRandomInt(SampleServer.MAX_MONETARY);
            case "many2one":
                if (field.relation === "res.currency") {
                    /** @todo return session.company_currency_id */
                    return 1;
                }
                if (field.relation === "ir.attachment") {
                    return false;
                }
                return this._getRandomSubRecordId();
            case "one2many":
            case "many2many": {
                const ids = [this._getRandomSubRecordId(), this._getRandomSubRecordId()];
                return [...new Set(ids)];
            }
            case "selection": {
                return this._getRandomSelectionValue(modelName, field);
            }
            default:
                return false;
        }
    }

    /**
     * @private
     * @param {any[]} array
     * @returns {any}
     */
    _getRandomArrayEl(array) {
        return array[Math.floor(Math.random() * array.length)];
    }

    /**
     * @private
     * @returns {boolean}
     */
    _getRandomBool() {
        return Math.random() < 0.5;
    }

    /**
     * @private
     * @returns {DateTime}
     */
    _getRandomDate() {
        const delta = Math.floor((Math.random() - Math.random()) * SampleServer.DATE_DELTA);
        return luxon.DateTime.local().plus({ hours: delta });
    }

    /**
     * @private
     * @param {number} max
     * @returns {number} float in [O, max[
     */
    _getRandomFloat(max) {
        return this._sanitizeNumber(Math.random() * max);
    }

    /**
     * @private
     * @param {number} max
     * @returns {number} int in [0, max[
     */
    _getRandomInt(max) {
        return Math.floor(Math.random() * max);
    }

    /**
     * @private
     * @returns {string}
     */
    _getRandomSelectionValue(modelName, field) {
        if (field.selection.length > 0) {
            return this._getRandomArrayEl(field.selection)[0];
        }
        return false;
    }

    /**
     * @private
     * @returns {number} id in [1, SUB_RECORDSET_SIZE]
     */
    _getRandomSubRecordId() {
        return Math.floor(Math.random() * SampleServer.SUB_RECORDSET_SIZE) + 1;
    }

    /**
     * Mocks calls to the read method.
     * @private
     * @param {Object} params
     * @param {string} params.model
     * @param {Array[]} params.args (args[0] is the list of ids, args[1] is
     *   the list of fields)
     * @returns {Object[]}
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
                    record[fieldName] = false; // unknown field
                } else if (field.type === "many2one") {
                    const relModel = this.data[field.relation];
                    const relRecord = relModel.records.find((relR) => r[fieldName] === relR.id);
                    record[fieldName] = relRecord ? [relRecord.id, relRecord.display_name] : false;
                } else {
                    record[fieldName] = r[fieldName];
                }
            }
            records.push(record);
        }
        return records;
    }

    /**
     * Mocks calls to the base method of formatted_read_group method.
     *
     * @param {Object} params
     * @param {string} params.model
     * @param {string[]} params.groupBy
     * @param {string[]} params.aggregates
     * @returns {Object[]} Object with keys groups and length
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
                const gb = { fieldName, type, interval, relation, alias: groupBySpec };
                normalizedGroupBys.push(gb);
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
                measures.push({ fieldName: "__count", func: "__count", name: measureSpec });
                continue;
            }
            const matches = measureSpec.match(MEASURE_SPEC_REGEX);
            if (!matches) {
                throw new Error(`Invalidate Aggregate "${measureSpec}" in SampleServer`);
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
     * Mocks calls to the base method of formatted_read_grouping_sets method.
     *
     * @param {Object} params
     * @param {string} params.model
     * @param {string[][]} params.grouping_sets
     * @param {string[]} params.aggregates
     * @returns {Object[]} Object with keys groups and length
     */
    _mockFormattedReadGroupingSets(params) {
        const res = [];
        for (const groupBy of params.grouping_sets) {
            res.push(this._mockFormattedReadGroup({ ...params, groupBy }));
        }
        return res;
    }

    /**
     * Mocks calls to the read_progress_bar method.
     * @private
     * @param {Object} params
     * @param {string} params.model
     * @param {string} params.group_by
     * @param {Object} params.progress_bar
     * @return {Object}
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

            // special case for bool values: rpc call response with capitalized strings
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

    _mockWebSearchReadUnity(params) {
        const fields = Object.keys(params.specification);
        const model = this.data[params.model];
        let rawRecords = model.records;
        if ("recordIds" in params) {
            rawRecords = model.records.filter((record) => params.recordIds.includes(record.id));
        } else {
            rawRecords = rawRecords.slice(0, SampleServer.SEARCH_READ_LIMIT);
        }
        const records = this._mockRead({
            model: params.model,
            args: [rawRecords.map((r) => r.id), fields],
        });
        const result = { records, length: records.length };
        // populate many2one and x2many values
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
                const relFields = Object.keys(params.specification[fieldName].fields || {});
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
                        record[fieldName] = record[fieldName].map((resId) => relRecords[resId]);
                    }
                }
            }
        }
        return result;
    }

    /**
     * Mocks calls to the web_read_group method to return groups populated
     * with sample records. Only handles the case where the real call to
     * web_read_group returned groups, but none of these groups contain
     * records. In this case, we keep the real groups, and populate them
     * with sample records.
     * @private
     * @param {Object} params
     * @param {Object} [result] the result of a real call to web_read_group
     * @returns {{ groups: Object[], length: number }}
     */
    _mockWebReadGroup(params) {
        const aggregates = [...params.aggregates, "__count"];
        if (params.auto_unfold && params.unfold_read_specification) {
            aggregates.push("id:array_agg");
        }
        let groups;
        if (this.existingGroups) {
            this._tweakExistingGroups({ ...params, aggregates });
            groups = this.existingGroups;
        } else {
            groups = this._mockFormattedReadGroup({ ...params, aggregates });
        }
        // Don't care another params - and no subgroup:
        // order / opening_info / unfold_read_default_limit / groupby_read_specification
        let nbOpenedGroup = 0;
        if (params.auto_unfold && params.unfold_read_specification) {
            for (const group of groups) {
                if (nbOpenedGroup < MAX_NUMBER_OPENED_GROUPS) {
                    nbOpenedGroup++;
                    group["__records"] = this._mockWebSearchReadUnity({
                        model: params.model,
                        specification: params.unfold_read_specification,
                        recordIds: group["id:array_agg"],
                    }).records;
                }
                delete group["id:array_agg"];
            }
        }
        if (params.opening_info) {
            params.opening_info.forEach((info, i) => {
                if (!info.folded) {
                    groups[i].__records ||= [];
                }
            });
        }

        return {
            groups,
            length: groups.length,
        };
    }

    /**
     * Updates the sample data such that the existing groups (in database)
     * also exists in the sample, and such that there are sample records in
     * those groups.
     * @private
     * @param {Object[]} groups empty groups returned by the server
     * @param {Object} params
     * @param {string} params.model
     * @param {string[]} params.groupBy
     */
    _populateExistingGroups(params) {
        const groups = this.existingGroups;
        const groupBy = params.groupBy[0].split(":")[0];
        const groupByField = this.data[params.model].fields[groupBy];
        const groupedByM2O = groupByField.type === "many2one";
        if (groupedByM2O) {
            // re-populate co model with relevant records
            this.data[groupByField.relation].records = groups.map((g) => ({
                id: g[groupBy][0],
                display_name: g[groupBy][1],
            }));
        }
        for (const r of this.data[params.model].records) {
            const group = getSampleFromId(r.id, groups);
            if (["date", "datetime"].includes(groupByField.type)) {
                r[groupBy] = serializeGroupDateValue(group[params.groupBy[0]], groupByField);
            } else if (groupByField.type === "many2one") {
                r[groupBy] = group[params.groupBy[0]] ? group[params.groupBy[0]][0] : false;
            } else {
                r[groupBy] = group[params.groupBy[0]];
            }
        }
    }

    /**
     * Generates sample records for the models in this.data. Records will be
     * generated once, and subsequent calls to this function will be skipped.
     * @private
     */
    _populateModels() {
        if (!this.populated) {
            for (const modelName in this.data) {
                const model = this.data[modelName];
                const fieldNames = Object.keys(model.fields).filter((f) => f !== "id");
                const size =
                    modelName === this.mainModel
                        ? SampleServer.MAIN_RECORDSET_SIZE
                        : SampleServer.SUB_RECORDSET_SIZE;
                for (let id = 1; id <= size; id++) {
                    const record = { id };
                    for (const fieldName of fieldNames) {
                        record[fieldName] = this._generateFieldValue(modelName, fieldName, id);
                    }
                    model.records.push(record);
                }
            }
            this.populated = true;
        }
    }

    /**
     * Rounds the given number value according to the configured precision.
     * @private
     * @param {number} value
     * @returns {number}
     */
    _sanitizeNumber(value) {
        return parseFloat(value.toFixed(SampleServer.FLOAT_PRECISION));
    }

    /**
     * A real (web_)read_group call has been done, and it has returned groups,
     * but they are all empty. This function updates the sample data such
     * that those group values exist and those groups contain sample records.
     * @private
     * @param {Object[]} groups empty groups returned by the server
     * @param {Object} params
     * @param {string} params.model
     * @param {string[]} params.aggregates
     * @param {string[]} params.groupBy
     * @returns {Object[]} groups with count and aggregate values updated
     *
     * TODO: rename
     */
    _tweakExistingGroups(params) {
        const groups = this.existingGroups;
        this._populateExistingGroups(params);

        // update count and aggregates for each group
        const fullGroupBy = params.groupBy[0];
        const groupBy = fullGroupBy.split(":")[0];
        const groupByField = this.data[params.model].fields[groupBy];
        const records = this.data[params.model].records;
        for (const g of groups) {
            const recordsInGroup = records.filter((r) => {
                if (["date", "datetime"].includes(groupByField.type)) {
                    return r[groupBy] === serializeGroupDateValue(g[fullGroupBy], groupByField);
                } else if (groupByField.type === "many2one") {
                    return (!r[groupBy] && !g[fullGroupBy]) || r[groupBy] === g[fullGroupBy][0];
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
                        this.data[params.model].fields[fieldName].type
                    )
                ) {
                    g[aggregateSpec] = recordsInGroup.reduce((acc, r) => acc + r[fieldName], 0);
                }
            }
        }
    }
}

SampleServer.FORMATS = {
    day: "yyyy-MM-dd",
    week: "'W'WW kkkk",
    month: "MMMM yyyy",
    quarter: "'Q'q yyyy",
    year: "y",
};
SampleServer.INTERVALS = {
    day: (dt) => dt.plus({ days: 1 }),
    week: (dt) => dt.plus({ weeks: 1 }),
    month: (dt) => dt.plus({ months: 1 }),
    quarter: (dt) => dt.plus({ months: 3 }),
    year: (dt) => dt.plus({ years: 1 }),
};
SampleServer.DISPLAY_FORMATS = Object.assign({}, SampleServer.FORMATS, { day: "dd MMM yyyy" });

SampleServer.MAIN_RECORDSET_SIZE = 16;
SampleServer.SUB_RECORDSET_SIZE = 5;
SampleServer.SEARCH_READ_LIMIT = 10;

SampleServer.MAX_FLOAT = 100;
SampleServer.MAX_INTEGER = 50;
SampleServer.MAX_COLOR_INT = 7;
SampleServer.MAX_MONETARY = 100000;
SampleServer.DATE_DELTA = 24 * 60; // in hours -> 60 days
SampleServer.FLOAT_PRECISION = 2;

SampleServer.SAMPLE_COUNTRIES = ["Belgium", "France", "Portugal", "Singapore", "Australia"];
SampleServer.SAMPLE_PEOPLE = [
    "John Miller",
    "Henry Campbell",
    "Carrie Helle",
    "Wendi Baltz",
    "Thomas Passot",
];
SampleServer.SAMPLE_TEXTS = [
    "Laoreet id",
    "Volutpat blandit",
    "Integer vitae",
    "Viverra nam",
    "In massa",
];
SampleServer.PEOPLE_MODELS = [
    "res.users",
    "res.partner",
    "hr.employee",
    "mail.followers",
    "mailing.contact",
];

SampleServer.UnimplementedRouteError = UnimplementedRouteError;

export function buildSampleORM(resModel, fields, user) {
    const sampleServer = new SampleServer(resModel, fields);
    const fakeRPC = async (_, params) => {
        const { args, kwargs, method, model } = params;
        const { groupby: groupBy } = kwargs;
        return sampleServer.mockRpc({ method, model, args, ...kwargs, groupBy });
    };
    const sampleORM = new ORM(user);
    sampleORM.rpc = fakeRPC;
    sampleORM.isSample = true;
    sampleORM.cache = () => sampleORM;
    sampleORM.setGroups = (groups) => sampleServer.setExistingGroups(groups);
    return sampleORM;
}
