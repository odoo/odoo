/** @odoo-module **/

import { groupBy as arrayGroupBy, sortBy as arraySortBy } from "@web/core/utils/arrays";
import { registry } from "@web/core/registry";
import { ORM } from "../../core/orm_service";
import { parseDate, serializeDate, serializeDateTime } from "@web/core/l10n/dates";

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

const MEASURE_SPEC_REGEX = /(?<measure>\w+):(?<aggregateFunction>\w+)(\((?<fieldName>\w+)\))?/;
const DESCRIPTION_REGEX = fieldNameRegex("description", "label", "title", "subject", "message");
const EMAIL_REGEX = fieldNameRegex("email");
const PHONE_REGEX = fieldNameRegex("phone");
const URL_REGEX = fieldNameRegex("url");

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
            case "/web/dataset/search_read":
                return this._mockSearchReadController(params);
            case "web_read_group":
                return this._mockWebReadGroup(params);
            case "read_group":
                return this._mockReadGroup(params);
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
        const values = {};
        for (const { fieldName, type } of measures) {
            if (["float", "integer", "monetary"].includes(type)) {
                if (records.length) {
                    let value = 0;
                    for (const record of records) {
                        value += record[fieldName];
                    }
                    values[fieldName] = this._sanitizeNumber(value);
                } else {
                    values[fieldName] = null;
                }
            }
            if (type === "many2one") {
                const ids = new Set(records.map((r) => r[fieldName]));
                values.fieldName = ids.size || null;
            }
        }
        return values;
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
        if (["date", "datetime"].includes(type)) {
            const fmt = SampleServer.FORMATS[interval];
            return parseDate(value).toFormat(fmt);
        } else if (type === "many2one") {
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
            case "datetime":
                const datetime = this._getRandomDate();
                return field.type === "date" ? serializeDate(datetime): serializeDateTime(datetime);
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
                // I hoped we wouldn't have to implement such special cases, but here it is.
                // If this (mail) field is set, 'Warning' is displayed instead of the last
                // activity, and we don't want to see a bunch of 'Warning's in a list. In the
                // future, if we have to implement several special cases like that, we'll setup
                // a proper hook to allow external modules to define extensions of this function.
                // For now, as we have only one use case, I guess that doing it here is fine.
                if (fieldName === "activity_exception_decoration") {
                    return false;
                }
                if (field.selection.length > 0) {
                    return this._getRandomArrayEl(field.selection)[0];
                }
                return false;
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
     * Mocks calls to the read_group method.
     *
     * @param {Object} params
     * @param {string} params.model
     * @param {string[]} [params.fields] defaults to the list of all fields
     * @param {string[]} params.groupBy
     * @param {boolean} [params.lazy=true]
     * @returns {Object[]} Object with keys groups and length
     */
    _mockReadGroup(params) {
        const lazy = "lazy" in params ? params.lazy : true;
        const model = params.model;
        const fields = this.data[model].fields;
        const records = this.data[model].records;

        const normalizedGroupBys = [];
        let groupBy = [];
        if (params.groupBy.length) {
            groupBy = lazy ? [params.groupBy[0]] : params.groupBy;
        }
        for (const groupBySpec of groupBy) {
            let [fieldName, interval] = groupBySpec.split(":");
            interval = interval || "month";
            const { type, relation } = fields[fieldName];
            if (type) {
                const gb = { fieldName, type, interval, relation, alias: groupBySpec };
                normalizedGroupBys.push(gb);
            }
        }
        const groups = arrayGroupBy(records, (record) => {
            const vals = {};
            for (const gb of normalizedGroupBys) {
                const { fieldName, type } = gb;
                let value;
                if (["date", "datetime"].includes(type)) {
                    value = this._formatValue(record[fieldName], gb);
                } else {
                    value = record[fieldName];
                }
                vals[fieldName] = value;
            }
            return JSON.stringify(vals);
        });
        const measures = [];
        for (const measureSpec of params.fields || Object.keys(fields)) {
            const matches = measureSpec.match(MEASURE_SPEC_REGEX);
            const { fieldName, aggregateFunction, measure } = (matches && matches.groups) || {};
            if (!fieldName && !measure) {
                continue; // this is for _count measure
            }
            const fName = fieldName || measure;
            const { type } = fields[fName];
            if (
                !params.groupBy.includes(fName) &&
                type &&
                (type !== "many2one" || aggregateFunction !== "count_distinct")
            ) {
                measures.push({ fieldName: fName, type });
            }
        }

        let result = [];
        for (const id in groups) {
            const records = groups[id];
            const group = { __domain: [] };
            let countKey = `__count`;
            if (normalizedGroupBys.length && lazy) {
                countKey = `${normalizedGroupBys[0].fieldName}_count`;
            }
            group[countKey] = records.length;
            const firstElem = records[0];
            for (const gb of normalizedGroupBys) {
                const { alias, fieldName } = gb;
                group[alias] = this._formatValue(firstElem[fieldName], gb);
            }
            Object.assign(group, this._aggregateFields(measures, records));
            result.push(group);
        }
        if (normalizedGroupBys.length > 0) {
            const { alias, interval, type } = normalizedGroupBys[0];
            result = arraySortBy(result, (group) => {
                const val = group[alias];
                if (["date", "datetime"].includes(type)) {
                    return parseDate(val, { format: SampleServer.FORMATS[interval] });
                }
                return val;
            });
        }
        return result;
    }

    /**
     * Mocks calls to the read_progress_bar method.
     * @private
     * @param {Object} params
     * @param {string} params.model
     * @param {Object} params.kwargs
     * @return {Object}
     */
    _mockReadProgressBar(params) {
        const groupBy = params.kwargs.group_by;
        const progress_bar = params.kwargs.progress_bar;
        const groupByField = this.data[params.model].fields[groupBy];
        const data = {};
        for (const record of this.data[params.model].records) {
            let groupByValue = record[groupBy];
            if (groupByField.type === "many2one") {
                const relatedRecords = this.data[groupByField.relation].records;
                const relatedRecord = relatedRecords.find((r) => r.id === groupByValue);
                groupByValue = relatedRecord.display_name;
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
                for (const key in progress_bar.colors) {
                    data[groupByValue][key] = 0;
                }
            }
            const fieldValue = record[progress_bar.field];
            if (fieldValue in data[groupByValue]) {
                data[groupByValue][fieldValue]++;
            }
        }
        return data;
    }

    /**
     * Mocks calls to the /web/dataset/search_read route to return sample
     * records.
     * @private
     * @param {Object} params
     * @param {string} params.model
     * @param {string[]} params.fields
     * @returns {{ records: Object[], length: number }}
     */
    _mockSearchReadController(params) {
        const model = this.data[params.model];
        const rawRecords = model.records.slice(0, SampleServer.SEARCH_READ_LIMIT);
        const records = this._mockRead({
            model: params.model,
            args: [rawRecords.map((r) => r.id), params.fields],
        });
        return { records, length: records.length };
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
        let groups;
        if (this.existingGroups) {
            this._tweakExistingGroups(params);
            groups = this.existingGroups;
        } else {
            groups = this._mockReadGroup(params);
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
        if (!this.existingGroupsPopulated) {
            const groups = this.existingGroups;
            this.groupsInfo = groups;
            const groupBy = params.groupBy[0];
            const values = groups.map((g) => g[groupBy]);
            const groupByField = this.data[params.model].fields[groupBy];
            const groupedByM2O = groupByField.type === "many2one";
            if (groupedByM2O) {
                // re-populate co model with relevant records
                this.data[groupByField.relation].records = values.map((v) => {
                    return { id: v[0], display_name: v[1] };
                });
            }
            for (const r of this.data[params.model].records) {
                const value = getSampleFromId(r.id, values);
                r[groupBy] = groupedByM2O ? value[0] : value;
            }
            this.existingGroupsPopulated = true;
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
     * @param {string[]} params.fields
     * @param {string[]} params.groupBy
     * @returns {Object[]} groups with count and aggregate values updated
     *
     * TODO: rename
     */
    _tweakExistingGroups(params) {
        const groups = this.existingGroups;
        this._populateExistingGroups(params);

        // update count and aggregates for each group
        const groupBy = params.groupBy[0].split(":")[0];
        const groupByField = this.data[params.model].fields[groupBy];
        const groupedByM2O = groupByField.type === "many2one";
        const records = this.data[params.model].records;
        for (const g of groups) {
            const groupValue = groupedByM2O ? g[groupBy][0] : g[groupBy];
            const recordsInGroup = records.filter((r) => r[groupBy] === groupValue);
            g[`${groupBy}_count`] = recordsInGroup.length;
            for (const field of params.fields) {
                const fieldType = this.data[params.model].fields[field].type;
                if (["integer, float", "monetary"].includes(fieldType)) {
                    g[field] = recordsInGroup.reduce((acc, r) => acc + r[field], 0);
                }
            }
            g.__data = {
                records: this._mockRead({
                    model: params.model,
                    args: [recordsInGroup.map((r) => r.id), params.fields],
                }),
                length: recordsInGroup.length,
            };
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
        const { kwargs, method, model } = params;
        const { groupby: groupBy } = kwargs;
        return sampleServer.mockRpc({ method, model, ...kwargs, groupBy });
    };
    return new ORM(fakeRPC, user);
}
