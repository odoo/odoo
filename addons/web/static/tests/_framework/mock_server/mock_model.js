import { createJobScopedGetter } from "@odoo/hoot";
import { Domain } from "@web/core/domain";
import {
    deserializeDate,
    deserializeDateTime,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { ensureArray, intersection, isIterable, unique } from "@web/core/utils/arrays";
import { deepCopy, isObject, pick } from "@web/core/utils/objects";
import * as fields from "./mock_fields";
import { MockServer } from "./mock_server";
import {
    MockServerError,
    getKwArgs,
    getRecordQualifier,
    makeKwArgs,
    makeServerError,
    safeSplit,
} from "./mock_server_utils";

const {
    DEFAULT_FIELD_VALUES,
    DEFAULT_RELATIONAL_FIELD_VALUES,
    DEFAULT_SELECTION_FIELD_VALUES,
    isComputed,
} = fields;

/**
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 *
 * @typedef {import("./mock_fields").FieldDefinition} FieldDefinition
 *
 * @typedef {import("./mock_fields").FieldType} FieldType
 *
 * @typedef {FieldDefinition["type"]} FieldType
 *
 * @typedef {{
 *  domain?: DomainListRepr;
 *  fields?: Record<string, any>;
 *  groupby: string[];
 *  lazy?: boolean;
 *  limit?: number;
 *  offset?: number;
 *  orderby?: string;
 * }} GroupByParams
 *
 * @typedef {import("./mock_fields").GroupOperator} GroupOperator
 *
 * @typedef {typeof Model} ModelConstructor
 *
 * @typedef {{
 *  create_date: string;
 *  display_name: string;
 *  id: number | false;
 *  name: string;
 *  write_date: string;
 *  [key: string]: any;
 * }} ModelRecord
 *
 * @typedef {{
 *  __domain: string;
 *  __count: number;
 *  __range: Record<string, any>;
 *  [key: string]: any;
 * }} ModelRecordGroup
 *
 * @typedef {{
 *  domain?: DomainListRepr;
 *  fields?: string[];
 *  limit?: number;
 *  modelName: string;
 *  offset?: number;
 *  order?: string;
 * }} SearchParams
 *
 * @typedef {"activity"
 *  | "calendar"
 *  | "cohort"
 *  | "form"
 *  | "gantt"
 *  | "graph"
 *  | "grid"
 *  | "hierarchy"
 *  | "kanban"
 *  | "list"
 *  | "map"
 *  | "pivot"
 *  | "search"
 * } ViewType
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

/**
 * @template [T={}]
 * @typedef {{
 *  args?: any[];
 *  context?: Record<string, any>;
 *  [key: string]: any;
 * } & Partial<T>} KwArgs
 */

const READ_GROUP_NUMBER_GRANULARITY = [
    "year_number",
    "quarter_number",
    "month_number",
    "iso_week_number",
    "day_of_year",
    "day_of_month",
    "day_of_week",
    "hour_number",
    "minute_number",
    "second_number",
];

const DATE_FORMAT = {
    day: (date) => date.toFormat("yyyy-MM-dd"),
    day_of_week: (date) => date.weekday,
    day_of_month: (date) => date.day,
    day_of_year: (date) => date.ordinal,
    week: (date) => `W${date.toFormat("WW kkkk")}`,
    iso_week_number: (date) => date.weekNumber,
    month_number: (date) => date.month,
    quarter: (date) => `Q${date.toFormat("q yyyy")}`,
    quarter_number: (date) => date.quarter,
    year: (date) => date.toFormat("yyyy"),
    year_number: (date) => date.year,
};

const DATETIME_FORMAT = {
    ...DATE_FORMAT,
    second_number: (date) => date.second,
    minute_number: (date) => date.minute,
    // The year is added to the format because is needed to correctly compute the
    // domain and the range (startDate and endDate).
    hour: (date) => date.toFormat("HH:00 dd MMM yyyy"),
    hour_number: (date) => date.hour,
};

/**
 * @param {Model} model
 * @param {ModelRecord} record
 * @param {Record<string, any>} [context]
 */
const applyDefaults = ({ _fields }, record, context) => {
    for (const fieldName in _fields) {
        if (fieldName === "id" || record[fieldName] !== undefined) {
            continue;
        }
        if (fieldName === "active") {
            record[fieldName] = true;
            continue;
        }
        if (fieldName === "create_uid") {
            record.create_uid = MockServer.current.env.uid;
            continue;
        }
        const fieldDef = _fields[fieldName];
        if (context && `default_${fieldName}` in context) {
            record[fieldName] = context[`default_${fieldName}`];
        } else if ("default" in fieldDef) {
            record[fieldName] =
                typeof fieldDef.default === "function"
                    ? fieldDef.default(record)
                    : fieldDef.default;
        } else if (isX2MField(fieldDef)) {
            record[fieldName] = [];
        } else {
            record[fieldName] = DEFAULT_FIELD_VALUES[fieldDef.type]();
        }
    }
};

/**
 * @template T
 * @param {T[]} target
 * @param  {...T[]} arrays
 */
const assignArray = (target, ...arrays) => {
    for (const array of arrays) {
        for (let i = 0; i < array.length; i++) {
            target[i] = array[i];
        }
    }
    target.length = Math.max(...arrays.map((array) => array.length));
    return target;
};

/**
 *
 * @param {string} name
 * @returns
 */
const constructorToModelName = (name) => name.replace(/([a-z])([A-Z])/g, "$1.$2").toLowerCase();

/**
 * Converts an Object representing a record to actual return Object of the
 * python `onchange` method.
 * Specifically, it reads `display_name` on many2one's and transforms raw id
 * list in orm command lists for x2many's.
 * For x2m fields that add or update records (ORM commands 0 and 1), it is
 * recursive.
 *
 * @param {Model} model
 * @param {ModelRecord} values
 * @param {Record<string, any>} specification
 */
const convertToOnChange = (model, values, specification) => {
    for (const [fname, val] of Object.entries(values)) {
        const field = model._fields[fname];
        if (isM2OField(field.type) && typeof val === "number") {
            values[fname] = getRelation(field).web_read(val, specification[fname].fields || {})[0];
        } else if (isX2MField(field)) {
            const coModel = getRelation(field);
            for (const cmd of val) {
                switch (cmd[0]) {
                    case 0: // CREATE
                    case 1: // UPDATE
                        cmd[2] = convertToOnChange(
                            coModel,
                            cmd[2],
                            specification[fname].fields || {}
                        );
                        break;
                    case 4: // LINK_TO
                        cmd[2] = coModel.web_read(cmd[1], specification[fname].fields || {})[0];
                }
            }
        } else if (field.type === "reference" && val) {
            const [modelName, id] = getReferenceValue(val);
            const result = model.env[modelName].web_read(id, specification[fname].fields || {});
            values[fname] = { ...result[0], id: { id, model: modelName } };
        }
    }
    return values;
};

/**
 * @param {string} modelName
 * @param {string} fieldName
 */
const fieldNotFoundError = (modelName, fieldName, consequence) => {
    let message = `cannot find a definition for field "${fieldName}" in model "${modelName}"`;
    if (consequence) {
        message += `: ${consequence}`;
    }
    return new MockServerError(message);
};

/**
 * @param {Model} model
 * @param {number | false} viewId
 * @param {ViewType} viewType
 */
const findView = (model, viewId, viewType) => {
    const key = model._getViewKey(viewType, viewId);
    if (model._views[key]) {
        return [model._views[key], viewId];
    }
    for (const [viewKey, viewArch] of Object.entries(model._views)) {
        const [type, id] = safeSplit(viewKey);
        if (type === viewType) {
            return [viewArch, Number(id) || false];
        }
    }
    return ["", false];
};

/**
 * @param {Record<string, FieldDefinition>} fields
 * @param {string} groupByField
 * @param {unknown} val
 */
const formatFieldValue = (fields, groupByField, val) => {
    if (val === false || val === undefined) {
        return false;
    }
    const [fieldName, aggregateFunction = "month"] = safeSplit(groupByField, ":");
    const { type } = fields[fieldName];
    if (type === "date") {
        const date = deserializeDate(String(val));
        return aggregateFunction in DATE_FORMAT
            ? DATE_FORMAT[aggregateFunction](date)
            : date.toFormat("MMMM yyyy");
    } else if (type === "datetime") {
        const date = deserializeDateTime(val);
        return aggregateFunction in DATETIME_FORMAT
            ? DATETIME_FORMAT[aggregateFunction](date)
            : date.toFormat("MMMM yyyy");
    } else if (Array.isArray(val)) {
        return val.length !== 0 && (isX2MField(type) ? val : val[0]);
    } else {
        return val;
    }
};

/**
 * Extract a sorting value for date/datetime fields from read_group __range
 * The start of the range for the shortest granularity is taken since it is
 * the most specific for a given group.
 *
 * @param {{ __range: Record<string, { from?: string | false; to?: string | false }> }} group
 * @param {string} fieldName
 */
const getDateSortingValue = (group, fieldName) => {
    // extract every range start related to fieldName
    let max = null;
    for (const groupedBy in group.__range) {
        if (groupedBy.startsWith(fieldName)) {
            const value = group.__range[groupedBy].from;
            if (!value) {
                return false;
            }
            const ts = new Date(value).getTime();
            if (ts > max) {
                max = ts;
            }
        }
    }
    // return false or the latest range start (related to the shortest
    // granularity (i.e. day, week, ...))
    return max ?? false;
};

/**
 * Extract a sorting value for date/datetime fields from read_group when the
 * date is groupby by a date number (month_number, year_number, ...)
 * The value for the shortest granularity is taken since it is the most specific
 * for a given group.
 *
 * @param {{ __range: Record<string, { from?: string | false; to?: string | false }> }} group
 * @param {string} fieldName
 * @returns {number | false}
 */
const getDateNumberSortingValue = (group, fieldName) => {
    let max = -1;
    let value = false;
    for (const groupedBy in group) {
        if (groupedBy.startsWith(fieldName)) {
            const [, granularity] = groupedBy.split(":");
            const index = READ_GROUP_NUMBER_GRANULARITY.indexOf(granularity);
            if (index !== -1 && index > max) {
                max = index;
                value = group[groupedBy];
            }
        }
    }
    return value;
};

/**
 * Returns the field by which a given model must be ordered.
 * It is either:
 * - the field matching 'fieldNameSpec' (if any, else an error is thrown).
 * - if no field spec is given : the 'sequence' field (if any), or the 'id' field.
 *
 * @param {Model} model
 * @param {string} [fieldNameSpec]
 */
const getOrderByField = ({ _fields, _name }, fieldNameSpec) => {
    const fieldName = fieldNameSpec?.split(":")[0] || ("sequence" in _fields ? "sequence" : "id");
    if (!(fieldName in _fields)) {
        throw fieldNotFoundError(_name, fieldName, "could not order records");
    }
    return _fields[fieldName];
};

/**
 * @param {unknown} value
 */
const getReferenceValue = (value) => {
    const [modelName, id] = safeSplit(value);
    return [modelName, JSON.parse(id)];
};

/**
 * @param {FieldDefinition} field
 * @param {ModelRecord} record
 */
const getRelation = (field, record = {}) => {
    let relation;
    if (field.relation) {
        relation = field.relation;
    } else if (field.type === "many2one_reference") {
        relation = record[field.model_field];
    }
    const comodel = relation || record[field.model_name_ref_fname];
    return comodel && MockServer.env[comodel];
};

/**
 * @param {Node | string} [node]
 * @returns {string}
 */
const getTag = (node) => {
    if (typeof node === "string") {
        return node;
    } else if (node) {
        return getTag(node.nodeName.toLowerCase());
    } else {
        return node;
    }
};

/**
 * @param {Model} model
 * @param {[number | false, ViewType]} args
 * @param {KwArgs<{ options: { toolbar?: boolean } }>} [kwargs={}]
 */
const getView = (model, args, kwargs) => {
    // find the arch
    let [requestViewId, viewType] = args;
    if (!requestViewId) {
        const contextKey = viewType + "_view_ref";
        if (contextKey in kwargs.context) {
            requestViewId = kwargs.context[contextKey];
        }
    }
    const [arch, viewId] = findView(model, requestViewId, getTag(viewType));
    if (!arch) {
        throw viewNotFoundError(model._name, viewType, viewId);
    }
    const view = parseView(model, {
        arch,
        context: kwargs.context,
    });
    if (kwargs.options.toolbar) {
        view.toolbar = model._toolbar;
    }
    if (viewId !== undefined) {
        view.id = viewId;
    }
    return view;
};

/**
 * @param {Model} model
 * @param {ViewType} viewType
 * @param {Record<string, Set<string>>} models
 */
const getViewFields = (model, viewType, models) => {
    switch (viewType) {
        case "form":
        case "kanban":
        case "list": {
            for (const fieldNames of Object.values(models)) {
                fieldNames.add("id");
                fieldNames.add("write_date");
            }
            break;
        }
        case "graph": {
            for (const { name, type } of Object.values(model._fields)) {
                if (["float", "integer"].includes(type)) {
                    models[model._name].add(name);
                }
            }
            break;
        }
        case "pivot": {
            for (const { name, type } of Object.values(model._fields)) {
                if (
                    [
                        "boolean",
                        "char",
                        "date",
                        "datetime",
                        "many2many",
                        "many2one",
                        "many2one_reference",
                        "selection",
                    ].includes(type)
                ) {
                    models[model._name].add(name);
                }
            }
            break;
        }
        case "search": {
            models[model._name] = new Set(Object.keys(model._fields));
            break;
        }
    }
    return models;
};

/**
 * @param {FieldDefinition | FieldType} field
 */
const isDateField = (field) => {
    const fieldType = typeof field === "string" ? field : field.type;
    return fieldType === "date" || fieldType === "datetime";
};

/**
 * @param {FieldDefinition | FieldType} field
 */
const isM2OField = (field) => {
    const fieldType = typeof field === "string" ? field : field.type;
    return fieldType === "many2one" || fieldType === "many2one_reference";
};

/**
 * @param {ViewType} viewType
 */
const isRelationalView = (viewType) => ["form", "kanban", "list"].includes(viewType);

/**
 * @param {[number, number?, any?]} command
 */
const isValidCommand = (command) => {
    const [action, id, data] = command;
    if (!command.length) {
        return false;
    }
    if (action < 0 || action > 6) {
        return false;
    }
    if (command.length > 1 && !(id === false || Number.isInteger(id))) {
        return false;
    }
    if (command.length > 2 && typeof data !== "object") {
        return false;
    }
    return command.length <= 3;
};

/**
 * @param {ModelRecord} record
 * @param {FieldDefinition} fieldDef
 * @param {unknown} value
 */
const isValidFieldValue = (record, fieldDef) => {
    const value = record[fieldDef.name];
    if (value === false) {
        // False is the accepted default for all field types
        return true;
    }
    switch (fieldDef.type) {
        case "binary":
        case "char":
        case "html":
        case "json":
        case "text": {
            return typeof value === "string";
        }
        case "boolean": {
            return typeof value === "boolean";
        }
        case "date": {
            return DATE_REGEX.test(value);
        }
        case "datetime": {
            return DATE_TIME_REGEX.test(value);
        }
        case "float":
        case "monetary": {
            return typeof value === "number";
        }
        case "integer": {
            return Number.isInteger(value);
        }
        case "many2many":
        case "one2many": {
            return (
                Array.isArray(value) &&
                value.every((id) => {
                    if (Array.isArray(id)) {
                        return isValidCommand(id);
                    } else {
                        return isValidId(id, fieldDef, record);
                    }
                })
            );
        }
        case "many2one":
        case "many2one_reference": {
            return isValidId(value, fieldDef, record);
        }
        case "properties": {
            return isObject(value);
        }
        case "properties_definition": {
            return value.every(
                (def) => typeof def.name === "string" && typeof def.type === "string"
            );
        }
        case "reference": {
            const [modelName, id] = getReferenceValue(value);
            return (
                fieldDef.selection.some(([value]) => value === modelName) &&
                isValidId(id, { ...fieldDef, relation: modelName }, record)
            );
        }
        case "selection": {
            return fieldDef.selection.some(([value]) => value === value);
        }
        default: {
            return true;
        }
    }
};

/**
 * @param {number | false} id
 * @param {FieldDefinition} field
 * @param {ModelRecord} [record]
 */
const isValidId = (id, field, record) => {
    if (id === false) {
        return true;
    }
    if (!Number.isInteger(id)) {
        return false;
    }
    const rel = getRelation(field, record);
    return rel && rel.some((record) => record.id === id);
};

/**
 * @param {Element} element
 * @param {string} modelName
 */
const isViewEditable = (element, modelName) => {
    switch (getTag(element)) {
        case "form":
            return true;
        case "list":
            return element.getAttribute("editable") || element.getAttribute("multi_edit");
        case "field": {
            const fname = element.getAttribute("name");
            const field = MockServer.env[modelName]._fields[fname];
            return !field.readonly && !/^(true|1)$/i.test(element.getAttribute("readonly"));
        }
        default:
            return false;
    }
};

/**
 * @param {FieldDefinition | FieldType} field
 */
const isX2MField = (field) => {
    const fieldType = typeof field === "string" ? field : field.type;
    return fieldType === "many2many" || fieldType === "one2many";
};

/**
 * Sorts the given list of records *IN PLACE* by the given field name. The
 * 'orderby' field name and sorting direction are determined by the optional
 * `orderBy` param, else the default orderBy field is applied (with "ASC").
 * @see {@link getOrderByField}
 *
 * @param {Model} model
 * @param {string} [orderBy] defaults to Model._order
 * @returns {ModelRecord[]}
 */
const orderByField = (model, orderBy, records) => {
    if (!records) {
        records = model;
    }
    if (!orderBy) {
        orderBy = model._order;
    }
    const orderBys = safeSplit(orderBy);
    const [fieldNameSpec, direction = "ASC"] = safeSplit(orderBys.pop(), " ");
    const field = getOrderByField(model.env[model._name], fieldNameSpec);

    // Prepares a values map if needed to easily retrieve the ordering
    // factor associated to a certain id or value.
    let valuesMap;
    if (field.type in DEFAULT_RELATIONAL_FIELD_VALUES) {
        let valueLength;
        const coModel = getRelation(field);
        const coField = getOrderByField(coModel);
        if (isX2MField(field)) {
            // O2M & M2M use the joined list of comodel field values
            // -> they need to be sorted
            orderByField(coModel);
            if (["float", "integer"].includes(coField.type)) {
                // Value needs to be padded for numeric types because of
                // the way stringified numbers are sorted.
                valueLength = coModel.reduce(
                    (longest, record) => Math.max(longest, String(record[coField.name]).length),
                    0
                );
            }
        }
        valuesMap = new Map(
            coModel.map((record) => {
                const value = record[coField.name];
                if (valueLength) {
                    const strValue = String(value);
                    return [record.id, strValue.padStart(valueLength, "0")];
                } else {
                    return [record.id, value];
                }
            })
        );
    } else if (field.type in DEFAULT_SELECTION_FIELD_VALUES) {
        // Selection order is determined by the index of each value
        valuesMap = new Map(field.selection.map((v, i) => [v[0], i]));
    }

    // Actual sorting
    const sortedRecords = records.sort((r1, r2) => {
        let v1 = r1[field.name];
        let v2 = r2[field.name];
        switch (field.type) {
            case "boolean": {
                v1 = Number(v1);
                v2 = Number(v2);
                break;
            }
            case "many2one":
            case "many2one_reference": {
                v1 &&= valuesMap.get(v1[0]);
                v2 &&= valuesMap.get(v2[0]);
                break;
            }
            case "many2many":
            case "one2many": {
                // Co-records have already been sorted -> comparing the joined
                // list of each of them will yield the proper result.
                v1 &&= v1.map((id) => valuesMap.get(id)).join("");
                v2 &&= v2.map((id) => valuesMap.get(id)).join("");
                break;
            }
            case "date":
            case "datetime": {
                if (r1.__range && r2.__range) {
                    v1 = getDateSortingValue(r1, field.name);
                    v2 = getDateSortingValue(r2, field.name);
                } else {
                    v1 = getDateNumberSortingValue(r1, field.name);
                    v2 = getDateNumberSortingValue(r2, field.name);
                }
                break;
            }
            case "reference":
            case "selection": {
                v1 &&= valuesMap.get(v1);
                v2 &&= valuesMap.get(v2);
                break;
            }
        }
        let result;
        if (v1 === false) {
            result = 1;
        } else if (v2 === false) {
            result = -1;
        } else {
            if (!["boolean", "number", "string"].includes(typeof v1) || typeof v1 !== typeof v2) {
                throw new MockServerError(
                    `cannot order by field "${field.name}" in model "${
                        model._name
                    }": values must be of the same primitive type (got ${typeof v1} and ${typeof v2})`
                );
            }
            result = v1 > v2 ? 1 : v1 < v2 ? -1 : 0;
        }
        return direction === "DESC" ? -result : result;
    });

    // Goes to the next level of orderBy (if any)
    if (orderBys.length) {
        return orderByField(model, orderBys.join(","), sortedRecords);
    }

    return sortedRecords;
};

/**
 * @param {Model} model
 * @param {{
 *  arch: string | Node;
 *  editable?: boolean;
 *  fields: Record<string, FieldDefinition>;
 *  modelName: string;
 *  processedNodes?: Node[];
 * }} params
 */
const parseView = (model, params) => {
    const processedNodes = params.processedNodes || [];
    const { arch } = params;
    const level = params.level || 0;
    const editable = params.editable || true;
    const fields = deepCopy(model._fields);

    const { _onChanges } = model;
    const fieldNodes = {};
    const groupbyNodes = {};
    const relatedModels = { [model._name]: new Set() };
    const doc =
        typeof arch === "string"
            ? domParser.parseFromString(arch, "text/xml").documentElement
            : arch;
    const viewType = getTag(doc);
    const isEditable = editable && isViewEditable(doc, model._name);

    traverseElement(doc, (node) => {
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return false;
        }
        ["required", "readonly", "invisible", "column_invisible"].forEach((attr) => {
            if (/^(true|1)$/i.test(node.getAttribute(attr))) {
                node.setAttribute(attr, "True");
            }
        });
        const isField = getTag(node) === "field";
        const isGroupby = getTag(node) === "groupby";
        if (isField) {
            const fieldName = node.getAttribute("name");
            fieldNodes[fieldName] = {
                node,
                isInvisible: /^(true|1)$/i.test(node.getAttribute("invisible")),
                isEditable: isEditable && isViewEditable(node, model._name),
            };
            const field = fields[fieldName];
            if (!field) {
                throw fieldNotFoundError(model._name, fieldName);
            }
        } else if (isGroupby && !processedNodes.includes(node)) {
            const groupbyName = node.getAttribute("name");
            fieldNodes[groupbyName] = { node };
            groupbyNodes[groupbyName] = node;
        }
        if (isGroupby && !processedNodes.includes(node)) {
            return false;
        }
        return !isField;
    });
    for (const fieldName in fieldNodes) {
        relatedModels[model._name].add(fieldName);
    }
    for (const [name, { node, isInvisible, isEditable }] of Object.entries(fieldNodes)) {
        const field = fields[name];
        if (isEditable && (isM2OField(field) || isX2MField(field))) {
            const canCreate = node.getAttribute("can_create");
            node.setAttribute("can_create", canCreate || "true");
            const canWrite = node.getAttribute("can_write");
            node.setAttribute("can_write", canWrite || "true");
        }
        if (isX2MField(field)) {
            const relModel = getRelation(field);
            // inline subviews: in forms if field is visible and has no widget (1st level only)
            if (
                viewType === "form" &&
                level === 0 &&
                !node.getAttribute("widget") &&
                !isInvisible
            ) {
                const inlineViewTypes = [...node.childNodes].map(getTag);
                const missingViewtypes = [];
                const nodeMode = getTag(node.getAttribute("mode"));
                if (!intersection(inlineViewTypes, safeSplit(nodeMode || "kanban,list")).length) {
                    // TODO: use a kanban view by default in mobile
                    missingViewtypes.push(safeSplit(nodeMode || "list")[0]);
                }
                for (const type of missingViewtypes) {
                    // in a lot of tests, we don't need the form view, so it doesn't even exist
                    let [arch] = findView(relModel, false, type);
                    if (!arch) {
                        arch = /* xml */ `<${type} />`;
                    }
                    node.appendChild(domParser.parseFromString(arch, "text/xml").documentElement);
                }
            }
            for (const childNode of node.childNodes) {
                if (childNode.nodeType === Node.ELEMENT_NODE) {
                    // this is hackhish, but parseView modifies the subview document in place
                    const { models } = parseView(relModel, {
                        arch: childNode,
                        editable: isEditable,
                        level: level + 1,
                        processedNodes,
                    });
                    for (const [modelName, fields] of Object.entries(models)) {
                        relatedModels[modelName] ||= new Set();
                        for (const field of fields) {
                            relatedModels[modelName].add(field);
                        }
                    }
                }
            }
        }
        // add onchanges
        if (isRelationalView(viewType) && name in _onChanges) {
            node.setAttribute("on_change", "1");
        }
    }
    for (const [name, node] of Object.entries(groupbyNodes)) {
        const field = fields[name];
        if (!isM2OField(field)) {
            throw new MockServerError("cannot group: 'groupby' can only target many2one fields");
        }
        field.views = {};
        const coModel = getRelation(field);
        processedNodes.push(node);
        // postprocess simulation
        const { models } = parseView(coModel, {
            arch: node,
            editable: false,
            processedNodes,
        });
        for (const [modelName, fields] of Object.entries(models)) {
            relatedModels[modelName] ||= new Set();
            for (const field of fields) {
                relatedModels[modelName].add(field);
            }
        }
    }
    const processedArch = xmlSerializer.serializeToString(doc);
    const fieldsInView = {};
    for (const field of Object.values(fields)) {
        if (field.name in fieldNodes) {
            fieldsInView[field.name] = field;
        }
    }
    return {
        arch: processedArch,
        model: model._name,
        models: getViewFields(model, viewType, relatedModels),
        type: viewType,
    };
};

/**
 * Equivalent to the server '_search_panel_domain_image' method.
 *
 * @param {Model} model
 * @param {DomainListRepr} domain
 * @param {string} fieldName
 * @param {boolean} setCount
 */
const searchPanelDomainImage = (model, fieldName, domain, setCount = false, limit = false) => {
    const field = model._fields[fieldName];
    let groupIdName;
    if (isM2OField(field)) {
        groupIdName = (value) => value || [false, undefined];
        // read_group does not take care of the condition [fieldName, '!=', false]
        // in the domain defined below!!!
    } else if (field.type === "selection") {
        const selection = {};
        for (const [value, label] of model._fields[fieldName].selection) {
            selection[value] = label;
        }
        groupIdName = (value) => [value, selection[value]];
    }
    domain = new Domain([...domain, [fieldName, "!=", false]]).toList();
    const groups = model.read_group(domain, [fieldName], [fieldName], makeKwArgs({ limit }));
    /** @type {Map<number, Record<string, any>>} */
    const domainImage = new Map();
    for (const group of groups) {
        const [id, display_name] = groupIdName(group[fieldName]);
        const values = { id, display_name };
        if (setCount) {
            values.__count = group[fieldName + "_count"];
        }
        domainImage.set(id, values);
    }
    return domainImage;
};

/**
 * Equivalent to the server '_search_panel_field_image' method.
 * @see {@link searchPanelDomainImage}
 *
 * @param {Model} model
 * @param {string} fieldName
 * @param {KwArgs<{
 *  enable_counters: boolean;
 *  extra_domain: DomainListRepr;
 *  limit: number;
 *  only_counters: boolean;
 *  set_limit: number;
 * }>} [kwargs={}]
 */
const searchPanelFieldImage = (model, fieldName, kwargs) => {
    const enableCounters = kwargs.enable_counters;
    const onlyCounters = kwargs.only_counters;
    const extraDomain = kwargs.extra_domain || [];
    const normalizedExtra = new Domain(extraDomain).toList();
    const noExtra = JSON.stringify(normalizedExtra) === "[]";
    const modelDomain = kwargs.model_domain || [];
    const countDomain = new Domain([...modelDomain, ...extraDomain]).toList();

    const limit = kwargs.limit;
    const setLimit = kwargs.set_limit;

    if (onlyCounters) {
        return searchPanelDomainImage(model, fieldName, countDomain, true);
    }

    const modelDomainImage = searchPanelDomainImage(
        model,
        fieldName,
        modelDomain,
        enableCounters && noExtra,
        setLimit && limit
    );
    if (enableCounters && !noExtra) {
        const countDomainImage = searchPanelDomainImage(model, fieldName, countDomain, true);
        for (const [id, values] of modelDomainImage.entries()) {
            const element = countDomainImage.get(id);
            values.__count = element ? element.__count : 0;
        }
    }

    return modelDomainImage;
};

/**
 * Equivalent to the server '_search_panel_global_counters' method.
 *
 * @param {Map<number, Record<string, any>>} valuesRange
 * @param {"parent_id" | false} parentName
 */
const searchPanelGlobalCounters = (valuesRange, parentName) => {
    const localCounters = [...valuesRange.keys()].map((id) => valuesRange.get(id).__count);
    for (let [id, values] of valuesRange.entries()) {
        const count = localCounters[id];
        if (count) {
            let parent_id = values[parentName];
            while (parent_id) {
                values = valuesRange.get(parent_id);
                values.__count += count;
                parent_id = values[parentName];
            }
        }
    }
};

/**
 * Equivalent to the server '_search_panel_sanitized_parent_hierarchy' method.
 *
 * @param {Model} model
 * @param {"parent_id" | false} parentName
 * @param {number[]} ids
 */
const searchPanelSanitizedParentHierarchy = (model, parentName, ids) => {
    const allowedRecords = {};
    for (const record of model) {
        allowedRecords[record.id] = record;
    }
    const recordsToKeep = {};
    for (const id of ids) {
        const ancestorChain = {};
        let recordId = id;
        let chainIsFullyIncluded = true;
        while (chainIsFullyIncluded && recordId) {
            const knownStatus = recordsToKeep[recordId];
            if (knownStatus !== undefined) {
                chainIsFullyIncluded = knownStatus;
                break;
            }
            const record = allowedRecords[recordId];
            if (record) {
                ancestorChain[recordId] = record;
                recordId = record[parentName] && record[parentName][0];
            } else {
                chainIsFullyIncluded = false;
            }
        }
        for (const id in ancestorChain) {
            recordsToKeep[id] = chainIsFullyIncluded;
        }
    }
    return model.filter((rec) => recordsToKeep[rec.id]);
};

/**
 * Equivalent to the server '_search_panel_selection_range' method.
 *
 * @param {Model} model
 * @param {string} fieldName
 * @param {KwArgs} [kwargs={}]
 */
const searchPanelSelectionRange = (model, fieldName, kwargs) => {
    const enableCounters = kwargs.enable_counters;
    const expand = kwargs.expand;
    let domainImage;
    if (enableCounters || !expand) {
        domainImage = searchPanelFieldImage(model, fieldName, {
            ...kwargs,
            only_counters: expand,
        });
    }
    if (!expand) {
        return [...domainImage.values()];
    }
    const selection = model._fields[fieldName].selection;
    const selectionRange = [];
    for (const [value, label] of selection) {
        const values = {
            id: value,
            display_name: label,
        };
        if (enableCounters) {
            values.__count = domainImage.get(value) ? domainImage.get(value).__count : 0;
        }
        selectionRange.push(values);
    }
    return selectionRange;
};

/**
 * @param {ModelRecord} record
 */
const toIdDisplayName = (record) => record && [record.id, record.display_name];

/**
 * @param {Node} node
 * @param {(node: Node) => boolean} callback
 */
const traverseElement = (node, callback) => {
    if (callback(node)) {
        for (const child of node.childNodes) {
            traverseElement(child, callback);
        }
    }
};

/**
 * Fill all inverse fields of the relational fields present in the record
 * to be created/updated.
 *
 * @param {Model} model
 * @param {ModelRecord} record record that have been created/updated.
 * @param {ModelRecord} [originalRecord] record before update.
 */
const updateComodelRelationalFields = (model, record, originalRecord) => {
    for (const fname in record) {
        const field = model._fields[fname];
        const coModel = getRelation(field, record);
        const inverseFieldName =
            field.inverse_fname_by_model_name && field.inverse_fname_by_model_name[coModel?._name];
        if (!inverseFieldName) {
            // field has no inverse, skip it.
            continue;
        }
        const relatedRecordIds = ensureArray(record[fname]);
        const comodelInverseField = coModel._fields[inverseFieldName];
        // we only want to set a value for comodel inverse field if the model field has a value.
        if (record[fname]) {
            for (const relatedRecordId of relatedRecordIds) {
                let inverseFieldNewValue = record.id;
                const relatedRecord = coModel.find((record) => record.id === relatedRecordId);
                const relatedFieldValue = relatedRecord && relatedRecord[inverseFieldName];
                if (
                    relatedFieldValue === undefined ||
                    relatedFieldValue === record.id ||
                    (field.type !== "one2many" && relatedFieldValue.includes(record.id))
                ) {
                    // related record does not exist or the related value is already up to date.
                    continue;
                }
                if (Array.isArray(relatedFieldValue)) {
                    inverseFieldNewValue = [...relatedFieldValue, record.id];
                }
                const data = { [inverseFieldName]: inverseFieldNewValue };
                if (comodelInverseField.type === "many2one_reference") {
                    data[comodelInverseField.model_name_ref_fname] = model._name;
                }
                coModel._write(data, relatedRecordId);
            }
        } else if (field.type === "many2one_reference") {
            // we need to clean the many2one_field as well.
            const model_many2one_field =
                comodelInverseField.inverse_fname_by_model_name[model._name];
            model._write({ [model_many2one_field]: false }, record.id);
        }
        // it's an update, get the records that were originally referenced but are not
        // anymore and update their relational fields.
        if (originalRecord) {
            const originalRecordIds = ensureArray(originalRecord[fname]);
            // search read returns [id, name], let's ensure the removedRecordIds are integers.
            const removedRecordIds = originalRecordIds.filter(
                (recordId) => Number.isInteger(recordId) && !relatedRecordIds.includes(recordId)
            );
            for (const removedRecordId of removedRecordIds) {
                const removedRecord = coModel.find((record) => record.id === removedRecordId);
                if (!removedRecord) {
                    continue;
                }
                let inverseFieldNewValue = false;
                if (Array.isArray(removedRecord[inverseFieldName])) {
                    inverseFieldNewValue = removedRecord[inverseFieldName].filter(
                        (id) => id !== record.id
                    );
                }
                coModel._write(
                    {
                        [inverseFieldName]: inverseFieldNewValue.length
                            ? inverseFieldNewValue
                            : false,
                    },
                    removedRecordId
                );
            }
        }
    }
};

/**
 * @param {string} modelName
 * @param {ViewType} viewType
 * @param {number | false} viewId
 */
const viewNotFoundError = (modelName, viewType, viewId, consequence) => {
    let message = `cannot find an arch for view "${viewType}" with ID ${viewId} in model "${modelName}"`;
    if (consequence) {
        message += `: ${consequence}`;
    }
    return new MockServerError(message);
};

// Other constants
const AGGREGATE_FUNCTION_REGEX = /(\w+)(?::(\w+)(?:\((\w+)\))?)?/;
const DATE_REGEX = /\d{4}-\d{2}-\d{2}/;
const DATE_TIME_REGEX = /\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?/;
/** @type {GroupOperator[]} */
const VALID_AGGREGATE_FUNCTIONS = [
    "array_agg",
    "avg",
    "bool_and",
    "bool_or",
    "count",
    "count_distinct",
    "max",
    "min",
    "sum",
];

const domParser = new DOMParser();
const xmlSerializer = new XMLSerializer();
let modelInstanceLock = false;

/**
 * Local model used by the {@link MockServer} to store the definition of a model.
 * A set of fields is available by default on each model ({@link id}, {@link name},
 * {@link display_name} and {@link created_at}).
 *
 * After declaring a model definition, you must use the {@link defineModels} function
 * to register it on the current/future {@link MockServer} instance.
 *
 * This class cannot be instantiated outside of the {@link Model.definition} static
 * getter.
 *
 * @extends {Array<ModelRecord>}
 */
export class Model extends Array {
    static definitionGetter = null;

    static get definition() {
        if (!this.definitionGetter) {
            this.definitionGetter = createJobScopedGetter((previous) => {
                modelInstanceLock = true;
                const model = new this();
                modelInstanceLock = false;

                // Inheritted properties
                if (previous) {
                    model._computes = { ...previous._computes };
                    model._fetch = previous._fetch;
                    model._fields = { ...previous._fields };
                    model._inherit = previous._inherit;
                    model._name = previous._name;
                    model._onChanges = { ...previous._onChanges };
                    model._order = previous._order;
                    model._parent_name = previous._parent_name;
                    model._rec_name = previous._rec_name;
                    model._records = JSON.parse(JSON.stringify(previous._records));
                    model._related = new Set(previous._related);
                    model._toolbar = JSON.parse(JSON.stringify(previous._toolbar));
                    model._views = { ...previous._views };
                }

                // Records
                assignArray(model, model._records);

                // Name
                model._name ||= constructorToModelName(this.name) || "anonymous";

                // Fields
                for (const [key, value] of Object.entries(model)) {
                    if (value?.[fields.FIELD_SYMBOL]) {
                        model._fields[key] = value;
                        delete model[key];
                    }
                }
                if (!model._rec_name && "name" in model._fields) {
                    model._rec_name = "name";
                }

                // Views
                for (const [key, value] of Object.entries(model._views)) {
                    const [viewType, viewId] = safeSplit(key);
                    const actualKey = model._getViewKey(viewType, viewId);

                    delete model._views[key];
                    model._views[actualKey] = value || `<${viewType} />`;
                }

                return model;
            });
        }
        return this.definitionGetter();
    }

    static get _fields() {
        return this.definition._fields;
    }
    static set _fields(value) {
        this.definition._fields = value;
    }

    static get _filters() {
        return this.definition._filters;
    }
    static set _filters(value) {
        this.definition._filters = value;
    }

    static get _inherit() {
        return this.definition._inherit;
    }
    static set _inherit(value) {
        this.definition._inherit = value;
    }

    static get _name() {
        return this.definition._name;
    }
    static set _name(value) {
        this.definition._name = value;
    }

    static get _onChanges() {
        return this.definition._onChanges;
    }
    static set _onChanges(value) {
        this.definition._onChanges = value;
    }

    static get _order() {
        return this.definition._order;
    }
    static set _order(value) {
        this.definition._order = value;
    }

    static get _parent_name() {
        return this.definition._parent_name;
    }
    static set _parent_name(value) {
        this.definition._parent_name = value;
    }

    static get _rec_name() {
        return this.definition._rec_name;
    }
    static set _rec_name(value) {
        this.definition._rec_name = value;
    }

    static get _records() {
        return this.definition;
    }
    static set _records(value) {
        assignArray(this.definition, value);
    }

    static get _toolbar() {
        return this.definition._toolbar;
    }
    static set _toolbar(value) {
        this.definition._toolbar = value;
    }

    static get _views() {
        return this.definition._views;
    }
    static set _views(value) {
        this.definition._views = value;
    }

    /** @type {Record<string, (this: Model, fieldName: string) => void>} */
    _computes = {};
    _fetch = false;
    /**
     * @type {Omit<Model,
     *  "_computes"
     *  | "_fields"
     *  | "_inherit"
     *  | "_name"
     *  | "_onChanges"
     *  | "_order"
     *  | "_parent_name"
     *  | "_rec_name"
     *  | "_records"
     *  | "_related"
     *  | "_views"> | null
     * } */
    _fields = {};
    /** @type {Record<string, any>[]} */
    _filters = [];
    /** @type {string | null} */
    _inherit = null;
    /** @type {string} */
    _name = "";
    /** @type {Record<string, (record: ModelRecord) => any>} */
    _onChanges = {};
    /** @type {string} */
    _order = "id";
    _parent_name = "parent_id";
    /** @type {keyof Model | null} */
    _rec_name = null;
    /** @type {Partial<ModelRecord>[]} */
    _records = [];
    /** @type {Set<string>} */
    _related = new Set();
    /** @type {Record<"print" | "action", ActionDefinition[]>} */
    _toolbar = {};
    /** @type {Record<string, string>} */
    _views = {};

    get env() {
        return MockServer.current.env;
    }

    // Default fields, common to all models
    id = fields.Integer({ readonly: true });
    display_name = fields.Char({ compute: "_compute_display_name" });
    create_date = fields.Datetime({
        string: "Created on",
        readonly: true,
        default: () => new Date().toISOString().slice(0, 19).replace("T", " "),
    });
    write_date = fields.Datetime({
        string: "Last Modified on",
        readonly: true,
        default: (record) => record.create_date,
    });

    static [Symbol.iterator]() {
        return this.definition[Symbol.iterator]();
    }

    constructor() {
        super(...arguments);

        if (!modelInstanceLock) {
            const modelInstance = this.constructor.definition;

            this._computes = modelInstance._computes;
            this._fetch = modelInstance._fetch;
            this._fields = modelInstance._fields;
            this._inherit = modelInstance._inherit;
            this._name = modelInstance._name;
            this._onChanges = modelInstance._onChanges;
            this._order = modelInstance._order;
            this._parent_name = modelInstance._parent_name;
            this._rec_name = modelInstance._rec_name;
            this._records = modelInstance._records;
            this._related = modelInstance._related;
            this._views = modelInstance._views;
        }
    }

    //-------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    /**
     * @param {MaybeIterable<number>} idOrIds
     */
    action_archive(idOrIds) {
        const kwargs = getKwArgs(arguments, "ids");
        ({ ids: idOrIds } = kwargs);

        return this.write(idOrIds, { active: false }, kwargs);
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     */
    action_unarchive(idOrIds) {
        const kwargs = getKwArgs(arguments, "ids");
        ({ ids: idOrIds } = kwargs);

        return this.write(idOrIds, { active: true }, kwargs);
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     */
    browse(idOrIds) {
        const ids = ensureArray(idOrIds);
        const records = new this.constructor();
        if (ids.length > 1) {
            const recordSet = new Map();
            for (const id of ids) {
                recordSet.set(id, undefined);
            }
            for (const record of this) {
                if (recordSet.has(record.id)) {
                    recordSet.set(record.id, record);
                }
            }
            for (const record of recordSet.values()) {
                if (record) {
                    records.push(record);
                }
            }
        } else if (ids.length === 1) {
            const record = this.find((rec) => rec.id === ids[0]);
            if (record) {
                records.push(record);
            }
        }
        return records;
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     * @param {Partial<ModelRecord>} defaultValues
     */
    copy(idOrIds, defaultValues) {
        ({ ids: idOrIds, default: defaultValues } = getKwArgs(arguments, "ids", "default"));

        return ensureArray(idOrIds).map((id) => {
            const copyId = this._getNextId();
            const originalRecord = this.find((record) => record.id === id);
            this.push({
                ...originalRecord,
                ...defaultValues,
                id: copyId,
                display_name: `${originalRecord.display_name} (copy)`,
            });
            return copyId;
        });
    }

    /**
     * @param {Iterable<ModelRecord>} valuesList
     */
    create(valuesList) {
        const kwargs = getKwArgs(arguments, "vals_list");
        ({ vals_list: valuesList } = kwargs);

        const shouldReturnList = isIterable(valuesList);
        const allValues = shouldReturnList ? valuesList : [valuesList];
        /** @type {number[]} */
        const ids = [];
        for (const values of allValues) {
            if ("id" in values) {
                throw new MockServerError(`cannot create a record with a given ID value`);
            }
            const record = { id: this._getNextId() };
            ids.push(record.id);
            this.push(record);
            applyDefaults(this, values, kwargs.context);
            this._write(values, record.id);
        }
        this.browse(ids)._applyComputesAndValidate();
        return shouldReturnList ? ids : ids[0];
    }

    /**
     * @param {Iterable<string>} fields
     */
    default_get(fields) {
        const kwargs = getKwArgs(arguments, "fields_list");
        ({ fields_list: fields } = kwargs);

        /** @type {ModelRecord} */
        const result = {};
        for (const fieldName of fields) {
            if (fieldName === "id") {
                continue;
            }
            const field = this._fields[fieldName];
            const key = "default_" + fieldName;
            if (kwargs.context && key in kwargs.context) {
                if (isX2MField(field)) {
                    const ids = kwargs.context[key] || [];
                    result[fieldName] = ids.map(Command.link);
                } else {
                    result[fieldName] = kwargs.context[key];
                }
                continue;
            }
            if ("default" in field) {
                result[fieldName] = field.default;
                continue;
            } else {
                if (!(field.type in DEFAULT_FIELD_VALUES)) {
                    throw new MockServerError(
                        `missing default value for field type "${field.type}"`
                    );
                }
                result[fieldName] = DEFAULT_FIELD_VALUES[field.type]();
            }
        }
        for (const fieldName in result) {
            const field = this._fields[fieldName];
            if (isM2OField(field) && result[fieldName]) {
                if (!isValidId(result[fieldName], field, result)) {
                    delete result[fieldName];
                }
            }
        }
        return result;
    }

    /**
     * @param {Iterable<string>} fieldNames
     * @param {Iterable<string>} attributes
     */
    fields_get(fieldNames, attributes) {
        const kwargs = getKwArgs(arguments, "allfields", "attributes");
        ({ allfields: fieldNames, attributes } = kwargs);

        const fields = fieldNames ? pick(this._fields, ...fieldNames) : this._fields;
        if (!attributes) {
            return fields;
        }

        return fields.map((field) => pick(field, ...attributes));
    }

    /**
     * @param {[number | false, string][]} views
     * @param {{ load_filters?: boolean }} [options]
     */
    get_views(views, options) {
        const kwargs = getKwArgs(arguments, "views", "options");
        ({ views, options = {} } = kwargs);

        /** @type {typeof this.models} */
        const models = {};
        /** @type {typeof this.views} */
        const result = {};

        // Determine all the models/fields used in the views
        // modelFields = {modelName: {fields: Set([...fieldNames])}}
        const modelFields = {};
        views.forEach(([viewId, viewType]) => {
            result[viewType] = getView(this, [viewId, viewType], kwargs);
            for (const [modelName, fields] of Object.entries(result[viewType].models)) {
                modelFields[modelName] ||= { fields: new Set() };
                for (const field of fields) {
                    modelFields[modelName].fields.add(field);
                }
            }
            delete result[viewType].models;
        });

        // For each model, fetch the information of the fields used in the views only
        for (const [modelName, value] of Object.entries(modelFields)) {
            models[modelName] = { fields: MockServer.env[modelName].fields_get(value.fields) };
        }

        if (options.load_filters && "search" in result) {
            result["search"].filters = this._filters;
        }
        return { models, views: result };
    }

    /**
     * @param {string} name
     */
    name_create(name) {
        const kwargs = getKwArgs(arguments, "name");
        ({ name } = kwargs);

        const values = { [this._rec_name]: name, display_name: name };
        const [id] = this.create([values], kwargs);
        return [id, kwargs.name];
    }

    /**
     * @param {string} [name]
     * @param {DomainListRepr} [domain]
     * @param {string} [operator]
     * @param {number} [limit]
     */
    name_search(name, domain, operator, limit) {
        const kwargs = getKwArgs(arguments, "name", "args", "operator", "limit");
        ({ name = "", args: domain = [], operator = "ilike", limit = 100 } = kwargs);

        const actualDomain = new Domain(domain);
        /** @type {[number, string][]} */
        const result = [];
        for (const record of this) {
            const isInDomain = actualDomain.contains(record);
            if (
                isInDomain &&
                (!name ||
                    (operator === "="
                        ? record.display_name === name
                        : record.display_name?.includes(name)))
            ) {
                result.push(toIdDisplayName(record));
            }
        }
        return result.slice(0, limit);
    }

    /**
     * @param {Iterable<number>} ids
     * @param {Record<string, any>} values
     * @param {MaybeIterable<string>} fieldNames
     * @param {Record<string, any>} specification
     */
    onchange(ids, values, fieldNames, fieldsSpec) {
        const kwargs = getKwArgs(arguments, "ids", "values", "field_names", "fields_spec");
        ({ ids, values, field_names: fieldNames, fields_spec: fieldsSpec } = kwargs);

        fieldNames = ensureArray(fieldNames || []);

        const firstOnChange = !fieldNames.length;
        const fieldsFromView = Object.keys(fieldsSpec);

        let serverValues = {};
        const onchangeValues = {};
        for (const fieldName in values) {
            if (!(fieldName in this._fields)) {
                throw makeServerError({
                    type: "ValidationError",
                    message: `Field ${fieldName} does not exist`,
                });
            }
        }
        if (ids[0]) {
            serverValues = this.read(ids, fieldsFromView, kwargs)[0];
        } else if (firstOnChange) {
            // It is the new semantics: no field in arguments means we are in
            // a default_get + onchange situation
            fieldNames = fieldsFromView;
            for (const fieldName of fieldNames) {
                if (!(fieldName in serverValues) && fieldName !== "id") {
                    onchangeValues[fieldName] = false;
                }
            }
            const defaultValues = this.default_get(fieldsFromView, kwargs);
            for (const fieldName in defaultValues) {
                if (isX2MField(this._fields[fieldName])) {
                    const subSpec = fieldsSpec[fieldName];
                    for (const command of defaultValues[fieldName]) {
                        if (command[0] === 0 || command[0] === 1) {
                            command[2] = pick(command[2], ...Object.keys(subSpec.fields));
                        }
                    }
                }
            }
            Object.assign(onchangeValues, defaultValues);
        }

        const finalValues = { ...serverValues, ...onchangeValues, ...values };
        const proxy = new Proxy(finalValues, {
            set(target, p, newValue) {
                if (target[p] !== newValue) {
                    onchangeValues[p] = newValue;
                }
                return Reflect.set(target, p, newValue);
            },
        });

        for (const field of fieldNames) {
            if (typeof this._onChanges[field] === "function") {
                this._onChanges[field](proxy);
            }
        }

        return {
            value: convertToOnChange(this, onchangeValues, fieldsSpec),
        };
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     * @param {Iterable<string>} [fields]
     * @param {string | false} [load]
     */
    read(idOrIds, fields, load) {
        const kwargs = getKwArgs(arguments, "ids", "fields", "load");
        ({ ids: idOrIds, fields, load } = kwargs);

        const fieldNames = fields?.length ? fields : Object.keys(this._fields);
        return this._read_format(idOrIds, fieldNames, load);
    }

    /**
     * @param {DomainListRepr} domain
     * @param {Iterable<string>} fields
     * @param {string[]} groupby
     * @param {number} [offset]
     * @param {number} [limit]
     * @param {string} [orderby]
     * @param {boolean} [lazy]
     */
    read_group(domain, fields, groupby, offset, limit, orderby, lazy) {
        /**
         * @param {ModelRecordGroup} group
         * @param {ModelRecord[]} records
         */
        const aggregateFields = (group, records) => {
            for (const { fieldName, func, name } of aggregatedFields) {
                switch (this._fields[fieldName].type) {
                    case "integer":
                    case "float": {
                        if (func === "array_agg") {
                            group[name] = records.map((r) => r[fieldName]);
                        } else {
                            if (!records.length) {
                                group[name] = false;
                            } else {
                                group[name] = 0;
                                for (const r of records) {
                                    group[name] += r[fieldName];
                                }
                            }
                        }
                        break;
                    }
                    case "many2one":
                    case "reference": {
                        const ids = records.map((r) => r[fieldName]);
                        if (func === "array_agg") {
                            group[name] = ids.map((id) => (id ? id : null));
                        } else {
                            const uniqueIds = unique(ids).filter(Boolean);
                            group[name] = uniqueIds.length;
                        }
                        break;
                    }
                    case "boolean": {
                        if (func === "array_agg") {
                            group[name] = records.map((r) => r[fieldName]);
                        } else if (func === "bool_or") {
                            group[name] = records.some((r) => Boolean(r[fieldName]));
                        } else if (func === "bool_and") {
                            group[name] = records.every((r) => Boolean(r[fieldName]));
                        }
                        break;
                    }
                }
            }
        };

        const kwargs = getKwArgs(
            arguments,
            "domain",
            "fields",
            "groupby",
            "offset",
            "limit",
            "orderby",
            "lazy"
        );
        ({ domain, fields, groupby, offset, limit, orderby, lazy = true } = kwargs);

        const records = this._filter(domain);
        /** @type {string[]} */
        let groupBy = [];
        if (groupby.length) {
            groupBy = lazy ? [groupby[0]] : groupby;
        }
        const groupByFieldNames = groupBy.map((groupByField) => safeSplit(groupByField, ":")[0]);
        /** @type {{ fieldName: string; func?: string; name: string }[]} */
        const aggregatedFields = [];
        // if no fields have been given, the server picks all stored fields
        if (fields.length === 0) {
            for (const fieldName in this._fields) {
                if (!groupByFieldNames.includes(fieldName)) {
                    aggregatedFields.push({ fieldName, name: fieldName });
                }
            }
        } else {
            fields.forEach((fspec) => {
                const [, name, func, fname] = fspec.match(AGGREGATE_FUNCTION_REGEX);
                const fieldName = func ? fname || name : name;
                if (func && !VALID_AGGREGATE_FUNCTIONS.includes(func)) {
                    throw new MockServerError(`invalid aggregation function "${func}"`);
                }
                if (!this._fields[fieldName]) {
                    return;
                }
                if (groupByFieldNames.includes(fieldName)) {
                    // grouped fields are not aggregated
                    return;
                }
                if (
                    ["many2one", "reference"].includes(this._fields[fieldName].type) &&
                    !["count_distinct", "array_agg"].includes(func)
                ) {
                    return;
                }

                aggregatedFields.push({ fieldName, func, name });
            });
        }

        if (!groupBy.length) {
            const group = { __count: records.length, __domain: kwargs.domain };
            aggregateFields(group, records);
            return [group];
        }

        /** @type {Record<any, ModelRecord[]>} */
        const groups = {};
        for (const record of records) {
            let recordGroupValues = [];
            for (const gbField of groupBy) {
                const [fieldName] = safeSplit(gbField, ":");
                const value = formatFieldValue(this._fields, gbField, record[fieldName]);
                recordGroupValues = ensureArray(value).reduce((acc, val) => {
                    const newGroup = {};
                    newGroup[gbField] = val;
                    if (recordGroupValues.length === 0) {
                        acc.push(newGroup);
                    } else {
                        for (const groupValue of recordGroupValues) {
                            acc.push({ ...groupValue, ...newGroup });
                        }
                    }
                    return acc;
                }, []);
            }
            for (const groupValue of recordGroupValues) {
                const valueKey = JSON.stringify(groupValue);
                groups[valueKey] = groups[valueKey] || [];
                groups[valueKey].push(record);
            }
        }

        /** @type {ModelRecordGroup[]} */
        let readGroupResult = [];
        for (const [groupId, groupRecords] of Object.entries(groups)) {
            /** @type {ModelRecordGroup} */
            const group = {
                ...JSON.parse(groupId),
                __domain: domain || [],
                __range: {},
            };
            for (const gbField of groupBy) {
                if (!(gbField in group)) {
                    group[gbField] = false;
                    continue;
                }

                const [fieldName, granularity] = safeSplit(gbField, ":");
                const value = Number.isInteger(group[gbField])
                    ? group[gbField]
                    : group[gbField] || false;
                const { relation, type } = this._fields[fieldName];

                if (relation && !Array.isArray(value)) {
                    const relatedRecord = this.env[relation].find(({ id }) => id === value);
                    if (relatedRecord) {
                        group[gbField] = [value, relatedRecord.display_name];
                    } else {
                        group[gbField] = false;
                    }
                }

                if (isDateField(type)) {
                    if (value) {
                        if (!READ_GROUP_NUMBER_GRANULARITY.includes(granularity)) {
                            let startDate, endDate;
                            switch (granularity) {
                                case "hour": {
                                    startDate = parseDateTime(value, {
                                        format: "HH:00 dd MMM yyyy",
                                    });
                                    endDate = startDate.plus({ hours: 1 });
                                    // Remove the year from the result value of the group. It was needed
                                    // to compute the startDate and endDate.
                                    group[gbField] = startDate.toFormat("HH:00 dd MMM");
                                    break;
                                }
                                case "day": {
                                    startDate = parseDateTime(value, { format: "yyyy-MM-dd" });
                                    endDate = startDate.plus({ days: 1 });
                                    break;
                                }
                                case "week": {
                                    startDate = parseDateTime(value, { format: "WW kkkk" });
                                    endDate = startDate.plus({ weeks: 1 });
                                    break;
                                }
                                case "quarter": {
                                    startDate = parseDateTime(value, { format: "q yyyy" });
                                    endDate = startDate.plus({ quarters: 1 });
                                    break;
                                }
                                case "year": {
                                    startDate = parseDateTime(value, { format: "y" });
                                    endDate = startDate.plus({ years: 1 });
                                    break;
                                }
                                case "month":
                                default: {
                                    startDate = parseDateTime(value, { format: "MMMM yyyy" });
                                    endDate = startDate.plus({ months: 1 });
                                    break;
                                }
                            }
                            const serialize = type === "date" ? serializeDate : serializeDateTime;
                            const from = serialize(startDate);
                            const to = serialize(endDate);
                            group.__range[gbField] = { from, to };
                            group.__domain = [
                                [fieldName, ">=", from],
                                [fieldName, "<", to],
                                ...group.__domain,
                            ];
                        } else {
                            group.__domain = [
                                [`${fieldName}.${granularity}`, "=", value],
                                ...group.__domain,
                            ];
                        }
                    } else {
                        group.__range[gbField] = false;
                        group.__domain = [[fieldName, "=", value], ...group.__domain];
                    }
                } else {
                    group.__domain = [[fieldName, "=", value], ...group.__domain];
                }
            }
            if (Object.keys(group.__range || {}).length === 0) {
                delete group.__range;
            }
            // compute count key to match dumb server logic...
            const groupByNoLeaf = kwargs.context ? "group_by_no_leaf" in kwargs.context : false;
            let countKey;
            if (lazy && (groupBy.length >= 2 || !groupByNoLeaf)) {
                countKey = safeSplit(groupBy[0], ":")[0] + "_count";
            } else {
                countKey = "__count";
            }
            group[countKey] = groupRecords.length;
            aggregateFields(group, groupRecords);
            readGroupResult.push(group);
        }

        // Order by
        orderByField(this, orderby || groupByFieldNames.join(","), readGroupResult);

        // Limit
        if (limit) {
            offset ||= 0;
            readGroupResult = readGroupResult.slice(offset, limit + offset);
        }

        return readGroupResult;
    }

    /**
     * @param {KwArgs<{ domain: DomainListRepr, group_by: string, progress_bar: any }>} [kwargs={}]
     */
    /**
     * @param {DomainListRepr} domain
     * @param {string} groupBy
     * @param {any} progressBar
     */
    read_progress_bar(domain, groupBy, progressBar) {
        const kwargs = getKwArgs(arguments, "domain", "group_by", "progress_bar");
        ({ domain, group_by: groupBy, progress_bar: progressBar } = kwargs);

        const groups = this.read_group(domain, [], [groupBy]);

        // Find group by field
        const data = {};
        for (const group of groups) {
            const records = this._filter(group.__domain);
            let groupByValue = group[groupBy]; // always technical value here
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
            for (const record of records) {
                const fieldValue = record[progressBar.field];
                if (fieldValue in data[groupByValue]) {
                    data[groupByValue][fieldValue]++;
                }
            }
        }

        return data;
    }

    render_public_asset() {
        return true;
    }

    /**
     * @param {DomainListRepr} domain
     * @param {number} [offset]
     * @param {number} [limit]
     * @param {string} [order]
     */
    search(domain, offset, limit, order) {
        const kwargs = getKwArgs(arguments, "domain", "offset", "limit", "order");
        ({ domain, offset, limit, order } = kwargs);

        const { records } = this._search({
            context: kwargs.context,
            domain,
            limit,
            offset,
            order,
        });
        return records.map((record) => record.id);
    }

    /**
     * @param {DomainListRepr} domain
     * @param {number} [limit]
     */
    search_count(domain, limit) {
        const kwargs = getKwArgs(arguments, "domain", "limit");
        ({ domain, limit } = kwargs);

        return this._search(kwargs).length;
    }

    /**
     * @param {string} fieldName
     */
    search_panel_select_range(fieldName) {
        /**
         * @type {KwArgs<{
         *  category_domain: DomainListRepr;
         *  comodel_domain: DomainListRepr;
         *  enable_counters: boolean;
         *  filter_domain: DomainListRepr;
         *  limit: number;
         *  search_domain: DomainListRepr;
         * }>}
         */
        const kwargs = getKwArgs(arguments, "field_name");
        ({ field_name: fieldName } = kwargs);

        const field = this._fields[fieldName];
        const coModel = getRelation(field);
        const supportedTypes = ["many2one", "selection"];
        if (!supportedTypes.includes(field.type)) {
            throw new MockServerError(
                `only category types ${supportedTypes.join(" and ")} are supported, got "${
                    field.type
                }"`
            );
        }

        const modelDomain = kwargs.search_domain || [];
        const extraDomain = new Domain([
            ...(kwargs.category_domain || []),
            ...(kwargs.filter_domain || []),
        ]).toList();

        if (field.type === "selection") {
            kwargs.model_domain = modelDomain;
            return {
                parent_field: false,
                values: searchPanelSelectionRange(this, fieldName, {
                    ...kwargs,
                    model_domain: modelDomain,
                    extra_domain: extraDomain,
                }),
            };
        }

        const fieldNames = ["display_name"];
        let hierarchize = "hierarchize" in kwargs ? kwargs.hierarchize : true;
        let getParentId;
        let parentName = false;
        if (hierarchize && coModel._fields[coModel._parent_name]) {
            parentName = coModel._parent_name;
            fieldNames.push(parentName);
            getParentId = (record) => record[parentName]?.[0] ?? false;
        } else {
            hierarchize = false;
        }
        let comodelDomain = kwargs.comodel_domain || [];
        const enableCounters = kwargs.enable_counters;
        const expand = kwargs.expand;
        const limit = kwargs.limit;
        let domainImage;
        if (enableCounters || !expand) {
            domainImage = searchPanelFieldImage(this, fieldName, {
                ...kwargs,
                model_domain: modelDomain,
                extra_domain: extraDomain,
                only_counters: expand,
                set_limit: limit && !(expand || hierarchize || comodelDomain),
            });
        }
        if (!expand && !hierarchize && !comodelDomain.length) {
            if (limit && domainImage.size === limit) {
                return { error_msg: "Too many items to display." };
            }
            return {
                parent_field: parentName,
                values: [...domainImage.values()],
            };
        }
        let imageElementIds;
        if (!expand) {
            imageElementIds = [...domainImage.keys()].map(Number);
            let condition;
            if (hierarchize) {
                const ancestorIds = new Set();
                for (const id of imageElementIds) {
                    let recordId = id;
                    let record;
                    while (recordId) {
                        ancestorIds.add(recordId);
                        record = coModel.find((rec) => rec.id === recordId);
                        recordId = record[parentName];
                    }
                }
                condition = ["id", "in", unique(ancestorIds)];
            } else {
                condition = ["id", "in", imageElementIds];
            }
            comodelDomain = new Domain([...comodelDomain, condition]).toList();
        }

        let comodelRecords = coModel.search_read(comodelDomain, fieldNames, kwargs);

        if (hierarchize) {
            const ids = expand ? comodelRecords.map((rec) => rec.id) : imageElementIds;
            comodelRecords = searchPanelSanitizedParentHierarchy(comodelRecords, parentName, ids);
        }

        if (limit && comodelRecords.length === limit) {
            return { error_msg: "Too many items to display." };
        }
        // A map is used to keep the initial order.
        const fieldRange = new Map();
        for (const record of comodelRecords) {
            const values = {
                id: record.id,
                display_name: record.display_name,
            };
            if (hierarchize) {
                values[parentName] = getParentId(record);
            }
            if (enableCounters) {
                values.__count = domainImage.get(record.id)
                    ? domainImage.get(record.id).__count
                    : 0;
            }
            fieldRange.set(record.id, values);
        }

        if (hierarchize && enableCounters) {
            searchPanelGlobalCounters(fieldRange, parentName);
        }

        return {
            parent_field: parentName,
            values: [...fieldRange.values()],
        };
    }

    /**
     * @param {string} fieldName
     * @param {string} [groupBy]
     */
    search_panel_select_multi_range(fieldName, groupBy) {
        /**
         * @type {KwArgs<{
         *  category_domain: DomainListRepr;
         *  comodel_domain: DomainListRepr;
         *  enable_counters: boolean;
         *  filter_domain: DomainListRepr;
         *  limit: number;
         *  search_domain: DomainListRepr;
         * }>}
         */
        const kwargs = getKwArgs(arguments, "field_name", "group_by");
        ({ field_name: fieldName, group_by: groupBy } = kwargs);

        const field = this._fields[fieldName];
        const coModel = getRelation(field);
        const supportedTypes = ["many2many", "many2one", "selection"];
        if (!supportedTypes.includes(field.type)) {
            throw new MockServerError(
                `only filter types ${supportedTypes} are supported, got "${field.type}"`
            );
        }
        let modelDomain = kwargs.search_domain || [];
        let extraDomain = new Domain([
            ...(kwargs.category_domain || []),
            ...(kwargs.filter_domain || []),
        ]).toList();
        if (field.type === "selection") {
            return {
                values: searchPanelSelectionRange(this, fieldName, {
                    ...kwargs,
                    model_domain: modelDomain,
                    extra_domain: extraDomain,
                }),
            };
        }
        const fieldNames = ["display_name"];
        let groupIdName;
        if (groupBy) {
            const groupByField = coModel._fields[groupBy];
            fieldNames.push(groupBy);
            if (isM2OField(groupByField)) {
                groupIdName = (value) => value || [false, "Not set"];
            } else if (groupByField.type === "selection") {
                const groupBySelection = {
                    ...coModel._fields[groupBy].selection,
                    [false]: "Not Set",
                };
                groupIdName = (value) => [value, groupBySelection[value]];
            } else {
                groupIdName = (value) => (value ? [value, value] : [false, "Not set"]);
            }
        }
        let comodelDomain = kwargs.comodel_domain || [];
        const enableCounters = kwargs.enable_counters;
        const expand = kwargs.expand;
        const limit = kwargs.limit;
        if (isX2MField(field)) {
            const comodelRecords = coModel.search_read(comodelDomain, fieldNames, kwargs);
            if (expand && limit && comodelRecords.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            const groupDomain = kwargs.group_domain;
            const fieldRange = [];
            for (const record of comodelRecords) {
                const values = {
                    id: record.id,
                    display_name: record.display_name,
                };
                let groupId;
                if (groupBy) {
                    const [gId, gName] = groupIdName(record[groupBy]);
                    values.group_id = groupId = gId;
                    values.group_name = gName;
                }
                let count;
                let inImage;
                if (enableCounters || !expand) {
                    const searchDomain = new Domain([
                        ...modelDomain,
                        [fieldName, "in", record.id],
                    ]).toList();
                    let localExtraDomain = extraDomain;
                    if (groupBy && groupDomain) {
                        localExtraDomain = new Domain([
                            ...localExtraDomain,
                            ...(groupDomain[JSON.stringify(groupId)] || []),
                        ]).toList();
                    }
                    const searchCountDomain = new Domain([
                        ...searchDomain,
                        ...localExtraDomain,
                    ]).toList();
                    if (enableCounters) {
                        count = this.search_count(searchCountDomain);
                    }
                    if (!expand) {
                        if (enableCounters && JSON.stringify(localExtraDomain) === "[]") {
                            inImage = count;
                        } else {
                            inImage = this.search(searchDomain, [], 1).length;
                        }
                    }
                }
                if (expand || inImage) {
                    if (enableCounters) {
                        values.__count = count;
                    }
                    fieldRange.push(values);
                }
            }

            if (!expand && limit && fieldRange.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            return { values: fieldRange };
        }

        if (isM2OField(field)) {
            let domainImage;
            if (enableCounters || !expand) {
                extraDomain = new Domain([...extraDomain, ...(kwargs.group_domain || [])]).toList();
                modelDomain = new Domain([...modelDomain, ...(kwargs.group_domain || [])]).toList();
                domainImage = searchPanelFieldImage(this, fieldName, {
                    ...kwargs,
                    model_domain: modelDomain,
                    extra_domain: extraDomain,
                    only_counters: expand,
                    set_limit: limit && !(expand || groupBy || comodelDomain),
                });
            }
            if (!expand && !groupBy && !comodelDomain.length) {
                if (limit && domainImage.size === limit) {
                    return { error_msg: "Too many items to display." };
                }
                return { values: [...domainImage.values()] };
            }
            if (!expand) {
                const imageElementIds = [...domainImage.keys()].map(Number);
                comodelDomain = new Domain([
                    ...comodelDomain,
                    ["id", "in", imageElementIds],
                ]).toList();
            }
            const comodelRecords = coModel.search_read(comodelDomain, fieldNames, kwargs);
            if (limit && comodelRecords.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            const fieldRange = [];
            for (const record of comodelRecords) {
                const values = {
                    id: record.id,
                    display_name: record.display_name,
                };
                if (groupBy) {
                    const [groupId, groupName] = groupIdName(record[groupBy]);
                    values.group_id = groupId;
                    values.group_name = groupName;
                }
                if (enableCounters) {
                    values.__count = domainImage.get(record.id)
                        ? domainImage.get(record.id).__count
                        : 0;
                }
                fieldRange.push(values);
            }
            return { values: fieldRange };
        }
    }

    /**
     * @param {DomainListRepr} [domain]
     * @param {Iterable<string>} [fields]
     * @param {number} [offset]
     * @param {number} [limit]
     * @param {string} [order]
     */
    search_read(domain, fields, offset, limit, order) {
        const kwargs = getKwArgs(arguments, "domain", "fields", "offset", "limit", "order");
        ({ domain, fields, offset, limit, order } = kwargs);

        if (!fields?.length) {
            fields = Object.keys(this._fields);
        }
        const { records } = this._search({
            context: kwargs.context,
            domain,
            limit,
            offset,
            order,
        });
        return this.read(
            records.map((r) => r.id),
            unique([...fields, "id"])
        );
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     */
    unlink(idOrIds) {
        const kwargs = getKwArgs(arguments, "ids");
        ({ ids: idOrIds } = kwargs);

        const ids = ensureArray(idOrIds);
        for (let i = this.length - 1; i >= 0; i--) {
            if (ids.includes(this[i].id)) {
                this.splice(i, 1);
            }
        }

        // update value of relationnal fields pointing to the deleted records
        for (const model of Object.values(MockServer.current.models)) {
            for (const [fieldName, field] of Object.entries(model._fields)) {
                const coModel = getRelation(field);
                if (coModel?._name === this._name) {
                    for (const record of model) {
                        if (Array.isArray(record[fieldName])) {
                            record[fieldName] = record[fieldName].filter((id) => !ids.includes(id));
                        } else if (ids.includes(record[fieldName])) {
                            record[fieldName] = false;
                        }
                    }
                }
            }
        }

        return true;
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     * @param {Record<string, any>} specification
     */
    web_read(idOrIds, specification) {
        const kwargs = getKwArgs(arguments, "ids", "specification");
        ({ ids: idOrIds, specification } = kwargs);

        const ids = ensureArray(idOrIds);
        let fieldNames = Object.keys(specification);
        if (!fieldNames.length) {
            fieldNames = ["id"];
        }
        const records = this.read(ids, fieldNames, kwargs);
        this._unityReadRecords(records, specification);
        return records;
    }

    /**
     * @param {DomainListRepr} domain
     * @param {Record<string, any>} fields
     * @param {string[]} groupby
     * @param {number} [limit]
     * @param {number} [offset]
     * @param {string} [orderby]
     * @param {boolean} [lazy]
     */
    web_read_group(domain, fields, groupby, limit, offset, orderby, lazy) {
        const kwargs = getKwArgs(
            arguments,
            "domain",
            "fields",
            "groupby",
            "limit",
            "offset",
            "orderby",
            "lazy"
        );
        ({ domain, fields, groupby, limit, offset, orderby, lazy } = kwargs);

        const groups = this.read_group(kwargs);
        const allGroups = this.read_group(domain, ["display_name"], groupby, makeKwArgs({ lazy }));
        return { groups, length: allGroups.length };
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     * @param {Partial<ModelRecord>} values
     * @param {Record<string, any>} specification
     * @param {MaybeIterable<number>} [nextId]
     */
    web_save(idOrIds, values, specification, nextId) {
        const kwargs = getKwArgs(arguments, "ids", "vals", "specification", "next_id");
        ({ ids: idOrIds, vals: values, specification, next_id: nextId } = kwargs);

        let ids = ensureArray(idOrIds);
        if (ids.length === 0) {
            ids = this.create([values], kwargs);
        } else {
            this.write(ids, values);
        }
        if (nextId) {
            ids = nextId;
        }
        return this.web_read(ids, specification);
    }

    /**
     * @param {DomainListRepr} domain
     * @param {Record<string, any>} specification
     * @param {number} [offset]
     * @param {number} [limit]
     * @param {string} [order]
     * @param {number} [countLimit]
     */
    web_search_read(domain, specification, offset, limit, order, countLimit) {
        const kwargs = getKwArgs(
            arguments,
            "domain",
            "specification",
            "offset",
            "limit",
            "order",
            "count_limit"
        );
        ({ domain, specification, offset, limit, order, count_limit: countLimit } = kwargs);

        const fieldNames = Object.keys(specification);
        const { length, records } = this._search({
            context: kwargs.context,
            domain,
            limit,
            offset,
            order,
        });
        const result = {
            length,
            records: this.read(
                records.map((r) => r.id),
                unique(["id", ...fieldNames])
            ),
        };
        if (countLimit) {
            result.length = Math.min(result.length, countLimit);
        }
        this._unityReadRecords(result.records, specification);
        return result;
    }

    /**
     * @param {unknown} user
     */
    with_user(user) {
        return this;
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     * @param {Partial<ModelRecord>} values
     */
    write(idOrIds, values) {
        const kwargs = getKwArgs(arguments, "ids", "vals");
        ({ ids: idOrIds, vals: values } = kwargs);

        const ids = ensureArray(idOrIds);
        const originalRecords = {};
        for (const id of ids) {
            originalRecords[id] = { ...this.browse(id)[0] };
            this._write(values, id);
        }
        this.browse(ids)._applyComputesAndValidate(originalRecords);
        return true;
    }

    //-------------------------------------------------------------------------
    // Private
    //-------------------------------------------------------------------------

    /**
     * @param {Record<string, ModelRecord>} [originalRecords={}]
     */
    _applyComputesAndValidate(originalRecords = {}) {
        // Compute related fields
        for (const fieldName of this._related) {
            this._compute_related_field(fieldName);
        }

        // Apply compute functions
        for (const computeFn of Object.values(this._computes)) {
            computeFn.call(this);
        }

        // Validate record values
        for (const record of this) {
            for (const fieldName of Object.keys(record)) {
                const fieldDef = this._fields[fieldName];
                if (!isValidFieldValue(record, fieldDef)) {
                    throw new MockServerError(
                        `invalid value for field "${fieldName}" on ${getRecordQualifier(
                            record
                        )} in model "${this._name}": expected "${fieldDef.type}" and got: ${
                            record[fieldName]
                        }`
                    );
                }
            }

            updateComodelRelationalFields(this, record, originalRecords[record.id]);
        }
    }

    _compute_display_name() {
        if (this._rec_name) {
            for (const record of this) {
                const value = record[this._rec_name];
                record.display_name = (value && String(value)) ?? false;
            }
        } else {
            for (const record of this) {
                record.display_name = `${this._name},${record.id}`;
            }
        }
    }

    /**
     * @param {string} fieldName
     */
    _compute_related_field(fieldName) {
        const field = this._fields[fieldName];
        const fieldNames = safeSplit(field.related, ".");
        for (const record of this) {
            const [value, fieldType] = this._followRelation(record, fieldNames);
            if (!fieldType) {
                // The related field is not found on the record, so we
                // remove the compute function.
                this.env[this._name]._related.delete(fieldName);
                return;
            }
            if (value === undefined) {
                // Value is null: assign default value (if null)
                record[fieldName] ??= DEFAULT_FIELD_VALUES[fieldType]();
            } else {
                // Value is not null: override
                record[fieldName] = value;
            }
        }
    }

    /**
     * Get all records from a model matching a domain.  The only difficulty is
     * that if we have an 'active' field, we implicitely add active = true in
     * the domain.
     *
     * @param {DomainListRepr} [domain]
     * @param {{ active_test?: boolean }} [options]
     */
    _filter(domain, options) {
        domain ||= [];
        if (!Array.isArray(domain)) {
            throw new TypeError(`domain must be an array, got: ${domain}`);
        }
        const activeTest = (options?.active_test ?? true) && this._fields.active;
        if (domain.length === 1) {
            // Fast simplification for simple domains
            const [[fieldName, operator, value]] = domain;
            let simpleFilter;
            switch (typeof fieldName) {
                case "boolean":
                case "number": {
                    let shouldBeIncluded;
                    if (domain[0].length === 1) {
                        // Single boolean/number (?)
                        shouldBeIncluded = Boolean(fieldName);
                    } else {
                        // TRUE/FALSE leaf
                        shouldBeIncluded = fieldName === value;
                        if (operator === "!=") {
                            shouldBeIncluded = !shouldBeIncluded;
                        }
                    }
                    if (activeTest) {
                        simpleFilter = () => shouldBeIncluded;
                    } else {
                        return shouldBeIncluded ? this : new this.constructor();
                    }
                    break;
                }
                case "string": {
                    if (fieldName === "id" && ("in", "=").includes(operator)) {
                        // Simple "id" domain with "in" or "=" operator
                        const values = ensureArray(value);
                        simpleFilter = (record) => values.includes(record[fieldName]);
                    }
                    break;
                }
            }
            if (simpleFilter) {
                return this.filter(
                    (record) => simpleFilter(record) && (!activeTest || record.active)
                );
            }
        }
        if (activeTest) {
            // add ['active', '=', true] to the domain if 'active' is not yet present in domain
            const activeInDomain = domain.some((subDomain) => subDomain[0] === "active");
            if (!activeInDomain) {
                domain = [...domain, ["active", "=", true]];
            }
        }
        if (!domain.length) {
            return this;
        }
        domain = domain.map((criterion) => {
            // 'child_of' operator isn't supported by domain.js, so we replace
            // in by the 'in' operator (with the ids of children)
            if (criterion[1] === "child_of") {
                let oldLength = 0;
                const childIds = [criterion[2]];
                while (childIds.length > oldLength) {
                    oldLength = childIds.length;
                    for (const record of this) {
                        if (childIds.indexOf(record[this._parent_name]) >= 0) {
                            childIds.push(record.id);
                        }
                    }
                }
                criterion = [criterion[0], "in", childIds];
            }
            // In case of many2many field, if domain operator is '=' generally change it to 'in' operator
            const field = this._fields[criterion[0]] || {};
            if (isX2MField(field) && criterion[1] === "=") {
                if (criterion[2] === false) {
                    // if undefined value asked, domain.js require equality with empty array
                    criterion = [criterion[0], "=", []];
                } else {
                    criterion = [criterion[0], "in", [criterion[2]]];
                }
            }
            return criterion;
        });

        const filterDomain = new Domain(domain);
        return this.filter((record) => filterDomain.contains(record));
    }

    /**
     * @param {ModelRecord} record
     * @param {string[]} fieldNames
     * @returns {[any, FieldType]}
     */
    _followRelation(record, fieldNames) {
        let currentModel = this;
        let currentRecord = record;
        let currentField;
        let value;
        for (const fieldName of fieldNames) {
            currentField = currentModel._fields[fieldName];
            if (!currentField) {
                break;
            }
            if (!currentRecord) {
                value = undefined;
                break;
            }
            value = currentRecord?.[fieldName];
            const relation = getRelation(currentField, currentRecord);
            if (relation) {
                const ids = ensureArray(currentRecord?.[fieldName]);
                currentModel = relation;
                currentRecord = currentModel.find((r) => ids.includes(r.id));
            }
        }

        return [value, currentField?.type];
    }

    _getNextId() {
        return Math.max(0, ...this.map((record) => record?.id || 0)) + 1;
    }

    /**
     * @param {FieldDefinition} field
     * @param {ModelRecord} record
     */
    _getPropertyContainer(field, record) {
        const relationField = this._fields[field.definition_record];
        if (relationField) {
            const containerModel = getRelation(this._fields[field.definition_record]);
            const containerId = record[field.definition_record];
            if (containerId) {
                return containerModel.browse(containerId)[0];
            }
        }
        return null;
    }

    /**
     * @param {ViewType} viewType
     * @param {number | false} [viewId]
     */
    _getViewKey(viewType, viewId) {
        const numId = Number(viewId);
        const actualId = Number.isInteger(numId) && numId;
        return `${viewType},${actualId || false}`;
    }

    /**
     * @param {MaybeIterable<number>} idOrIds
     * @param {Iterable<string>} [fnames=[]]
     * @param {string | false} [load="_classic_read"]
     */
    _read_format(idOrIds, fnames = [], load = "_classic_read") {
        const ids = ensureArray(idOrIds);
        const fieldNames = unique(["id", ...fnames]);

        /** @type {ModelRecord[]} */
        const records = [];
        const validFields = [];

        // Mapping of model records used in the current read call.
        /** @type {Record<string, Record<number, ModelRecord>>} */
        const modelMap = {
            [this._name]: {},
        };
        for (const record of this) {
            modelMap[this._name][record.id] = record;
        }
        for (const fieldName of fieldNames) {
            const field = this._fields[fieldName];
            if (field) {
                validFields.push(field);
            } else {
                continue; // the field doesn't exist on the model, so skip it
            }
            if (field.type === "many2one_reference") {
                for (const record of this) {
                    const coModel = getRelation(field, record);
                    if (!coModel) {
                        continue;
                    }
                    modelMap[coModel._name] ||= {};
                    modelMap[coModel._name][record[fieldName]] = record[fieldName];
                }
            } else if (isM2OField(field.type)) {
                const coModel = getRelation(field);
                if (coModel && !modelMap[coModel._name]) {
                    modelMap[coModel._name] = {};
                    for (const record of coModel) {
                        modelMap[coModel._name][record.id] = record;
                    }
                }
            }
        }

        // Fill records from model map
        for (const id of ids) {
            if (!id) {
                throw new MockServerError(
                    `cannot read: falsy ID value would result in an access error on the actual server`
                );
            }
            const record = modelMap[this._name][id];
            if (!record) {
                continue;
            }
            const result = { id: record.id };
            for (const field of validFields) {
                if (["float", "integer", "monetary"].includes(field.type)) {
                    // read should return 0 for unset numeric fields
                    result[field.name] = record[field.name] || 0;
                } else if (isM2OField(field)) {
                    const coModel = getRelation(field, record);
                    const relRecord = coModel && modelMap[coModel._name][record[field.name]];
                    if (relRecord) {
                        if (field.type === "many2one_reference" || load !== "_classic_read") {
                            result[field.name] = record[field.name];
                        } else {
                            result[field.name] = [record[field.name], relRecord.display_name];
                        }
                    } else {
                        result[field.name] = false;
                    }
                } else if (isX2MField(field)) {
                    result[field.name] = record[field.name] || [];
                } else if (field.type === "properties") {
                    const container = this._getPropertyContainer(field, record);
                    if (container) {
                        result[field.name] = container[field.definition_record_field].map(
                            (def) => ({
                                ...def,
                                value: record[field.name][def.name] ?? false,
                            })
                        );
                    } else {
                        result[field.name] = false;
                    }
                } else {
                    result[field.name] = record[field.name] ?? false;
                }
            }
            records.push(result);
        }

        return records;
    }

    /**
     * @param {SearchParams} params
     */
    _search(params) {
        const offset = params.offset || 0;
        const records = this._filter(params.domain, {
            active_test: params.context?.active_test,
        });
        orderByField(records, params.order);
        const endLimit = params.limit ? offset + params.limit : undefined;
        return {
            length: records.length,
            records: records.slice(offset, endLimit),
        };
    }

    /**
     * @param {Record<string, any>} spec
     * @param {ModelRecord[]} records
     */
    _unityReadRecords(records, spec) {
        for (const fieldName in spec) {
            const field = this._fields[fieldName];
            const relatedFields = spec[fieldName].fields;
            switch (field.type) {
                case "reference": {
                    for (const record of records) {
                        if (!record[fieldName]) {
                            continue;
                        }
                        const [modelName, id] = getReferenceValue(record[fieldName]);
                        record[fieldName] = {};
                        if (relatedFields && Object.keys(relatedFields).length) {
                            const result = this.env[modelName].web_read(
                                id,
                                relatedFields,
                                makeKwArgs({ context: spec[fieldName].context })
                            );
                            record[fieldName] = result[0];
                        }
                        record[fieldName].id = { id, model: modelName };
                    }
                    break;
                }
                case "many2one_reference": {
                    for (const record of records) {
                        const id = record[fieldName];
                        if (!id) {
                            record[fieldName] = 0;
                            continue;
                        }
                        if (!relatedFields) {
                            continue;
                        }
                        // the field isn't necessarily in the view, so get the model by looking
                        // in "db"
                        const dbRecord = this.find((r) => r.id === record.id);
                        const model = dbRecord[field.model_field];
                        record[fieldName] = {};
                        if (relatedFields && Object.keys(relatedFields).length) {
                            const [result] = this.env[model].web_read(
                                id,
                                relatedFields,
                                makeKwArgs({ context: spec[fieldName].context })
                            );
                            record[fieldName] = result;
                        }
                    }
                    break;
                }
                case "many2many":
                case "one2many": {
                    if (relatedFields && Object.keys(relatedFields).length) {
                        const ids = unique(records.flatMap((r) => r[fieldName]));
                        const result = getRelation(field).web_read(
                            ids,
                            relatedFields,
                            makeKwArgs({ context: spec[fieldName].context })
                        );
                        /** @type {Record<string, ModelRecord>} */
                        const allRelRecords = {};
                        for (const relRecord of result) {
                            allRelRecords[relRecord.id] = relRecord;
                        }
                        const { limit, order } = spec[fieldName];
                        for (const record of records) {
                            /** @type {number[]} */
                            const relResIds = record[fieldName];
                            let relRecords = relResIds.map((resId) => allRelRecords[resId]);
                            if (order) {
                                relRecords = orderByField(getRelation(field), order, relRecords);
                            }
                            if (limit) {
                                relRecords = relRecords.map((r, i) =>
                                    i < limit ? r : { id: r.id }
                                );
                            }
                            record[fieldName] = relRecords;
                        }
                    }
                    break;
                }
                case "many2one": {
                    for (const record of records) {
                        if (record[fieldName] !== false) {
                            if (!relatedFields) {
                                record[fieldName] = record[fieldName][0];
                            } else {
                                record[fieldName] = getRelation(field).web_read(
                                    [record[fieldName][0]],
                                    relatedFields,
                                    makeKwArgs({ context: spec[fieldName].context })
                                )[0];
                            }
                        }
                    }
                    break;
                }
            }
        }
    }

    /**
     * @param {ModelRecord} values
     * @param {number} id
     */
    _write(values, id) {
        const record = this.find((r) => r.id === id);
        const todoValsMap = new Map(Object.entries(values));
        const MAX_ITER = todoValsMap.size;
        let i = 0;
        while (todoValsMap.size > 0 && i < MAX_ITER) {
            let [fieldName, value] = todoValsMap.entries().next().value;
            todoValsMap.delete(fieldName);
            const field = this._fields[fieldName];
            if (!field) {
                throw fieldNotFoundError(
                    this._name,
                    fieldName,
                    `could not write on ${getRecordQualifier(record)}`
                );
            }
            if (isX2MField(field)) {
                let ids = record[fieldName] ? record[fieldName].slice() : [];
                // if a field has been modified, its value must always be sent to the server for onchange and write.
                // take into account that the value can be a empty list of commands.
                if (Array.isArray(value) && value.length) {
                    if (
                        value.reduce((hasOnlyInt, val) => hasOnlyInt && Number.isInteger(val), true)
                    ) {
                        // fallback to command 6 when given a simple list of ids
                        value = [[6, 0, value]];
                    }
                } else if (value === false) {
                    // delete all command
                    value = [[5]];
                }
                // interpret commands
                for (const command of value || []) {
                    const coModel = getRelation(field, record);
                    if (command[0] === 0) {
                        // CREATE
                        const inverseData = command[2]; // write in place instead of copy, because some tests rely on the object given being updated
                        const inverseFieldName = field.inverse_fname_by_model_name?.[coModel._name];
                        if (inverseFieldName) {
                            inverseData[inverseFieldName] = id;
                        }
                        const [newId] = coModel.create([inverseData]);
                        ids.push(newId);
                    } else if (command[0] === 1) {
                        // UPDATE
                        coModel.write([command[1]], command[2]);
                    } else if (command[0] === 2 || command[0] === 3) {
                        // DELETE or FORGET
                        ids.splice(ids.indexOf(command[1]), 1);
                    } else if (command[0] === 4) {
                        // LINK_TO
                        if (!ids.includes(command[1])) {
                            ids.push(command[1]);
                        }
                    } else if (command[0] === 5) {
                        // DELETE ALL
                        ids = [];
                    } else if (command[0] === 6) {
                        // REPLACE WITH
                        // copy array to avoid leak by reference (eg. of default data)
                        ids = [...command[2]];
                    } else {
                        throw new MockServerError(
                            `command "${JSON.stringify(
                                value
                            )}" is not supported by the MockServer on field "${fieldName}" in model "${
                                this._name
                            }"`
                        );
                    }
                }
                record[fieldName] = ids;
            } else if (isM2OField(field)) {
                if (value) {
                    if (!isValidId(value, field, record)) {
                        if (todoValsMap.has(field.model_name_ref_fname)) {
                            // handle it later as it might likely become valid
                            todoValsMap.set(fieldName, value);
                            continue;
                        }
                        throw new MockServerError(
                            `invalid ID "${JSON.stringify(
                                value
                            )}" for a many2one on field "${fieldName}" in model "${this._name}"`
                        );
                    }
                    record[fieldName] = value;
                } else {
                    record[fieldName] = false;
                }
            } else if (field.type === "properties") {
                const properties = value || [];
                if (properties.some((p) => p.definition_changed || p.definition_deleted)) {
                    // Property definition changed or deleted
                    const container = this._getPropertyContainer(field, record);

                    container[field.definition_record_field] = [];

                    for (const property of properties) {
                        const definition = { ...property };
                        delete definition.definition_changed;
                        delete definition.definition_deleted;
                        delete definition.value;

                        if (!property.definition_deleted) {
                            container[field.definition_record_field].push(definition);
                        }
                    }
                }

                // Property values
                record[fieldName] ||= {};
                for (const property of properties) {
                    if (property.definition_deleted) {
                        delete record[fieldName][property.name];
                    } else {
                        let value = property.value ?? property.default ?? false;
                        if (value && property.comodel) {
                            // For relational fields: transform to [id, display_name] tuples
                            const coModel = this.env[property.comodel];
                            switch (property.type) {
                                case "one2many":
                                case "many2many": {
                                    value = coModel.browse(value).map(toIdDisplayName);
                                    break;
                                }
                                case "many2one": {
                                    value = toIdDisplayName(coModel.browse(value[0])[0]);
                                    break;
                                }
                            }
                        }
                        record[fieldName][property.name] = value;
                    }
                }
            } else if (!isComputed(field)) {
                record[fieldName] = value;
            }
            i++;
        }
    }
}

/**
 * Same as the {@link Model} class, with the added action of fetching the
 * actual definition of its homonym server model.
 *
 * The fields defined in these models will override existing fields retrieved from
 * the server model.
 *
 * @see {@link Model}
 * @example
 *  class Partner extends ServerModel {
 *      _name = "res.partner";
 *
 *      // fields will be fetched from the server model
 *
 *      name = fields.Char({ required: false }); // will override server field definition for "name"
 *  }
 */
export class ServerModel extends Model {
    _fetch = true;
}

export const Command = {
    clear: () => [5],
    /**
     * @param {Partial<ModelRecord>} values
     */
    create: (values) => [0, 0, values],
    /**
     * @param {number} id
     */
    delete: (id) => [2, id],
    /**
     * @param {number} id
     */
    link: (id) => [4, id],
    /**
     * @param {number[]} ids
     */
    set: (ids) => [6, 0, ids],
    /**
     * @param {number} id
     */
    unlink: (id) => [3, id],
    /**
     *
     * @param {number} id
     * @param {Partial<ModelRecord>} values
     */
    update: (id, values) => [1, id, values],
};
