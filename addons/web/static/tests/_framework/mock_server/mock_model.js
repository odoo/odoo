// @ts-check

import { after, createJobScopedGetter } from "@odoo/hoot";
import { Domain } from "@web/core/domain";
import {
    deserializeDate,
    deserializeDateTime,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import {
    ensureArray,
    intersection,
    isIterable,
    unique,
} from "@web/core/utils/collections/arrays";
import { deepCopy, isObject, pick } from "@web/core/utils/collections/objects";
import { elementToIR } from "@web/views/ir/view_ir";

import * as fields from "./mock_fields.js";
import { MockServer } from "./mock_server.js";
import {
    getKwArgs,
    getRecordQualifier,
    makeKwArgs,
    makeServerError,
    MockServerError,
    safeSplit,
} from "./mock_server_utils.js";

const {
    DEFAULT_FIELD_VALUES,
    DEFAULT_RELATIONAL_FIELD_VALUES,
    DEFAULT_SELECTION_FIELD_VALUES,
    S_FIELD,
    copyFields,
    isComputed,
} = fields;

/**
 * @typedef {import("fields").INumerical["aggregator"]} Aggregator
 * @typedef {import("fields").FieldDefinition} FieldDefinition
 * @typedef {import("fields").FieldType} FieldType
 * @typedef {import("@web/core/context").Context} Context
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 * @typedef {{ fieldName: string; func: Aggregator; name: string }} AggregatedField
 * @typedef {(records: ModelRecord[], fieldName: string) => any} AggregatorFunction
 * @typedef {typeof Model} ModelConstructor
 * @typedef {{
 * create_date: string;
 * display_name: string | false;
 * id: number | false;
 * name: import("fields").FieldValue;
 * write_date: string;
 * [key: string]: any;
 * }} ModelRecord
 * @typedef {{
 * __domain: any;
 * __extra_domain: any[];
 * [key: string]: any;
 * }} ModelRecordGroup
 * @typedef {{
 * context?: Context;
 * domain?: DomainListRepr;
 * fields?: string[];
 * limit?: number;
 * modelName?: string;
 * offset?: number;
 * order?: string;
 * }} SearchParams
 * @typedef {string} ViewKey
 * @typedef {import("@web/views/view").ViewType} ViewType
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

/**
 * @template [T={}]
 * @typedef {{
 * args?: any[];
 * context?: Context;
 * [key: string]: any;
 * } & Partial<T>} KwArgs
 */

/**
 * @param {Iterable<AggregatedField>} aggregatedFields
 * @param {ModelRecordGroup} group
 * @param {ModelRecord[]} records
 */
function aggregateFields(aggregatedFields, group, records) {
    for (const { fieldName, func, name } of aggregatedFields) {
        group[name] = AGGREGATOR_FUNCTIONS[func](records, fieldName);
    }
}

/**
 * @template T
 * @param {T[]} target
 * @param {...T[]} arrays
 */
function assignArray(target, ...arrays) {
    for (const array of arrays) {
        for (let i = 0; i < array.length; i++) {
            target[i] = array[i];
        }
    }
    target.length = Math.max(...arrays.map((array) => array.length));
    return target;
}

/**
 * @param {Model} model
 * @param {ModelRecord} values
 * @param {Record<string, any>} specification
 */
function convertToOnChange(model, values, specification) {
    for (const [fname, val] of Object.entries(values)) {
        const field = model._fields[fname];
        if (isM2OField(field.type) && typeof val === "number") {
            values[fname] = getRelation(field).web_read(
                val,
                specification[fname].fields || {},
            )[0];
        } else if (isX2MField(field)) {
            const coModel = getRelation(field);
            values[fname] = val.map((cmd) => {
                switch (cmd[0]) {
                    case 0:
                    case 1:
                        return [
                            cmd[0],
                            cmd[1],
                            convertToOnChange(
                                coModel,
                                { ...cmd[2] },
                                specification[fname].fields || {},
                            ),
                        ];
                    case 4:
                        return [
                            cmd[0],
                            cmd[1],
                            coModel.web_read(
                                cmd[1],
                                specification[fname].fields || {},
                            )[0],
                        ];
                    default:
                        return [...cmd];
                }
            });
        } else if (field.type === "reference" && val) {
            const [modelName, id] = getReferenceValue(val);
            const result = model.env[modelName].web_read(
                id,
                specification[fname].fields || {},
            );
            values[fname] = { ...result[0], id: { id, model: modelName } };
        }
    }
    return values;
}

/** @param {typeof Model} ModelClass */
function createRawInstance(ModelClass) {
    modelInstanceLock++;
    const model = new ModelClass();
    modelInstanceLock--;
    return model;
}

/**
 * @param {string} modelName
 * @param {string} fieldName
 */
function fieldNotFoundError(modelName, fieldName, consequence) {
    let message = `Cannot find a definition for field "${fieldName}" in model "${modelName}"`;
    if (consequence) {
        message += `: ${consequence}`;
    }
    return new MockServerError(message);
}

/**
 * @param {Model} model
 * @param {ViewType} viewType
 * @param {string | number | false} viewId
 * @returns {[string, number | false]}
 */
function findView(model, viewType, viewId) {
    /** @type {Partial<Record<ViewKey, string>>} */
    const availableViews = Object.create(null);
    for (const [rawKey, arch] of Object.entries(model._views)) {
        availableViews[getViewKey(.../** @type {[any, any]} */ (safeSplit(rawKey)))] =
            arch;
    }
    for (const [id, arch] of Object.entries(inlineViewArchs[model._name] || {})) {
        if (arch || !availableViews[id]) {
            availableViews[id] = arch;
        }
    }

    let viewKey = getViewKey(viewType, viewId);
    if (!(viewKey in availableViews)) {
        if (typeof viewId === "number") {
            throw viewNotFoundError(model._name, viewType, viewId);
        }
        viewKey = /** @type {ViewKey} */ (
            Object.keys(availableViews)
                .filter((key) => key.startsWith(viewType))
                .sort()[0]
        );
        viewId = safeSplit(viewKey)[1];
    }
    const arch = availableViews[viewKey] || `<${viewType} />`;
    const actualViewId = Number(viewId) || false;
    return [arch, actualViewId];
}

/**
 * @param {FieldType} fieldType
 * @param {string} groupByField
 * @param {unknown} val
 */
function formatFieldValue(fieldType, groupByField, val) {
    if (val === false || val === undefined) {
        return false;
    }
    const [, granularityFunction = false] = safeSplit(groupByField, ":");
    const type = fieldType;

    if (["date", "datetime"].includes(type) && !granularityFunction) {
        throw new MockServerError(
            `Granularity should be always explicit for ${groupByField}`,
        );
    }

    if (type === "date") {
        const date = deserializeDate(String(val));
        const gf = /** @type {string} */ (granularityFunction);
        return gf in DATE_FORMAT ? DATE_FORMAT[gf](date) : date.toFormat("MMMM yyyy");
    } else if (type === "datetime") {
        const date = deserializeDateTime(/** @type {any} */ (val));
        const gf = /** @type {string} */ (granularityFunction);
        return gf in DATETIME_FORMAT
            ? DATETIME_FORMAT[gf](date)
            : date.toFormat("MMMM yyyy");
    } else if (Array.isArray(val)) {
        return val.length !== 0 && (isX2MField(type) ? val : val[0]);
    } else {
        return val;
    }
}

/** @param {unknown} value */
function isEmptyValue(value) {
    if (!value) {
        return true;
    }
    if (Array.isArray(value)) {
        return value.length === 0;
    }
    if (typeof value === "object") {
        return Object.keys(value).length === 0;
    }
    return false;
}

/**
 * @param {Model | null} previous
 * @param {typeof Model} constructor
 */
function getModelDefinition(previous, constructor) {
    const model = createRawInstance(constructor);
    model._name ||= constructor.getModelName(model);

    if (previous && !modelInstanceLock) {
        if (constructor === previous.constructor) {
            for (const [key, map] of INHERITED_PRIMITIVE_KEYS) {
                model[key] = map ? map(previous[key]) : previous[key];
            }
            for (const [key, map] of INHERITED_OBJECT_KEYS) {
                Object.assign(model[key], map ? map(previous[key]) : previous[key]);
            }
            assignArray(model._records, deepCopy(previous._records));
        } else {
            for (const [key, map] of INHERITED_PRIMITIVE_KEYS) {
                if (isEmptyValue(model[key])) {
                    model[key] = map ? map(previous[key]) : previous[key];
                }
            }
            for (const [key, map] of INHERITED_OBJECT_KEYS) {
                const previousValue = map ? map(previous[key]) : previous[key];
                for (const subKey in previousValue) {
                    if (isEmptyValue(model[key][subKey])) {
                        model[key][subKey] = previousValue[subKey];
                    }
                }
            }
            if (!model._records.length) {
                assignArray(model._records, deepCopy(previous._records));
            }
        }
    }

    for (const [fieldName, fieldDef] of Object.entries(model._fields)) {
        if (!fieldDef) {
            delete model._fields[fieldName];
            continue;
        }
        validateFieldDefinition(fieldName, fieldDef);
    }

    for (const [fieldName, fieldDef] of Object.entries(model)) {
        if (!(/** @type {any} */ (fieldDef)?.[S_FIELD])) {
            continue;
        }
        model._fields[fieldName] ||= validateFieldDefinition(
            fieldName,
            /** @type {any} */ (fieldDef),
        );
        delete model[fieldName];
    }

    return model;
}

/**
 * @param {Model} model
 * @param {string} [fieldNameSpec]
 */
function getOrderByField({ _fields, _name }, fieldNameSpec) {
    if (fieldNameSpec === "__count") {
        return _fields["id"];
    }
    const fieldPath =
        fieldNameSpec?.split(":")[0] || ("sequence" in _fields ? "sequence" : "id");
    const fieldNames = fieldPath.split(".");
    for (const fieldName of fieldNames.slice(0, -1)) {
        if (!(fieldName in _fields)) {
            throw fieldNotFoundError(_name, fieldName, "could not order records");
        }
        const relation = getRelation(_fields[fieldName]);
        _fields = relation._fields;
        _name = relation._name;
    }
    const fieldName = fieldNames.at(-1) ?? "";
    if (!(fieldName in _fields)) {
        throw fieldNotFoundError(_name, fieldName, "could not order records");
    }
    return _fields[fieldName];
}

/** @param {unknown} value */
function getReferenceValue(value) {
    const [modelName, id] = safeSplit(value);
    return [modelName, JSON.parse(id)];
}

/**
 * @param {FieldDefinition} field
 * @param {ModelRecord} record
 */
function getRelation(field, record = /** @type {ModelRecord} */ ({})) {
    let relation;
    if (field.relation) {
        relation = field.relation;
    } else if (field.type === "many2one_reference") {
        relation = record[field.model_field];
    }
    const comodel = relation || record[field.model_name_ref_fname];
    return comodel && MockServer.env[comodel];
}

/**
 * @param {Node | string} [node]
 * @returns {string}
 */
function getTag(node) {
    if (typeof node === "string") {
        return node;
    } else if (node) {
        return getTag(node.nodeName.toLowerCase());
    } else {
        return /** @type {any} */ (node);
    }
}

/**
 * @param {Model} model
 * @param {[number | false, ViewType]} args
 * @param {KwArgs<{ options: { toolbar?: boolean } }>} [kwargs={}]
 */
function getView(model, args, kwargs) {
    let [requestViewId, viewType] = args;
    if (!requestViewId) {
        const contextKey = `${viewType}_view_ref`;
        if (kwargs.context && contextKey in kwargs.context) {
            requestViewId = kwargs.context[contextKey];
        }
    }
    const [arch, viewId] = findView(model, viewType, requestViewId);
    const view = parseView(model, /** @type {any} */ ({ arch }));
    if (kwargs.options?.toolbar) {
        view.toolbar = model._toolbar;
    }
    if (viewId !== undefined) {
        view.id = viewId;
    }
    return view;
}

/**
 * @param {Model} model
 * @param {ViewType} viewType
 * @param {Record<string, Set<string>>} models
 */
function getViewFields(model, viewType, models) {
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
}

/**
 * @param {ViewType} viewType
 * @param {string | number | false} [viewId]
 * @returns {ViewKey}
 */
function getViewKey(viewType, viewId) {
    const nViewId =
        viewId && !isNaN(/** @type {any} */ (viewId)) ? Number(viewId) : viewId;
    return /** @type {ViewKey} */ ([viewType, nViewId || false].join(","));
}

/** @param {FieldDefinition | FieldType} field */
function isDateField(field) {
    const fieldType = typeof field === "string" ? field : field.type;
    return fieldType === "date" || fieldType === "datetime";
}

/** @param {FieldDefinition | FieldType} field */
function isM2OField(field) {
    const fieldType = typeof field === "string" ? field : field.type;
    return fieldType === "many2one" || fieldType === "many2one_reference";
}

/** @param {ViewType} viewType */
function isRelationalView(viewType) {
    return ["form", "kanban", "list"].includes(viewType);
}

/** @param {any[]} command */
function isValidCommand(command) {
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
    if (command.length > 2 && data !== false && typeof data !== "object") {
        return false;
    }
    return command.length <= 3;
}

/**
 * @param {ModelRecord} record
 * @param {FieldDefinition} fieldDef
 */
function isValidFieldValue(record, fieldDef) {
    const value = record[fieldDef.name];
    if (value === false) {
        return true;
    }
    switch (fieldDef.type) {
        case "binary":
        case "char":
        case "html":
        case "text": {
            return typeof value === "string";
        }
        case "boolean": {
            return typeof value === "boolean";
        }
        case "date": {
            return R_DATE.test(value);
        }
        case "datetime": {
            return R_DATE_TIME.test(value);
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
                (def) => typeof def.name === "string" && typeof def.type === "string",
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
}

/**
 * @param {number | false} id
 * @param {FieldDefinition} field
 * @param {ModelRecord} [record]
 */
function isValidId(id, field, record) {
    if (id === false) {
        return true;
    }
    if (!Number.isInteger(id)) {
        return false;
    }
    return true;
}

/**
 * @param {Element} element
 * @param {string} modelName
 */
function isViewEditable(element, modelName) {
    switch (getTag(element)) {
        case "form":
            return true;
        case "list":
            return (
                element.getAttribute("editable") || element.getAttribute("multi_edit")
            );
        case "field": {
            const fname = element.getAttribute("name");
            const field = MockServer.env[modelName]._fields[fname];
            return (
                !field.readonly && !/^(true|1)$/i.test(element.getAttribute("readonly"))
            );
        }
        default:
            return false;
    }
}

/** @param {FieldDefinition | FieldType} field */
function isX2MField(field) {
    const fieldType = typeof field === "string" ? field : field.type;
    return fieldType === "many2many" || fieldType === "one2many";
}

/**
 * @param {string} order
 * @param {string[]} groupby
 * @param {string[]} aggregates
 */
function getReadGroupOrder(order, groupby, aggregates) {
    if (!order) {
        return groupby.join(", ");
    }
    groupby = groupby.slice();
    const orderSpecs = [];
    for (const orderSpec of order.split(",")) {
        const [fname, direction] = orderSpec.trim().split(" ");
        if (fname === "__count") {
            orderSpecs.push(`${fname} ${direction}`);
            continue;
        }
        for (const groupbySpec of groupby) {
            if (fname === groupbySpec || groupbySpec.startsWith(`${fname}:`)) {
                groupby.splice(groupby.indexOf(groupbySpec), 1);
                orderSpecs.push(`${groupbySpec} ${direction}`);
                break;
            }
        }
        for (const agg of aggregates) {
            if (fname === agg || agg.startsWith(`${fname}:`)) {
                orderSpecs.push(`${agg} ${direction}`);
                break;
            }
        }
    }
    return [...orderSpecs, ...groupby].join(", ");
}

/**
 * @template {ModelRecord | ModelRecordGroup} [R=ModelRecord]
 * @param {Model} model
 * @param {string} [orderBy]
 * @param {R[]} [records]
 * @returns {R[]}
 */
function orderByField(model, orderBy, records) {
    if (!records) {
        records = /** @type {R[]} */ (/** @type {unknown} */ (model));
    }
    if (!orderBy) {
        orderBy = model._order;
    }
    const orderBys = safeSplit(orderBy);
    const [fieldNameSpec, direction = "ASC"] = safeSplit(orderBys.pop(), " ");
    const field = getOrderByField(model.env[model._name], fieldNameSpec);

    let valuesMap;
    if (field.type in DEFAULT_RELATIONAL_FIELD_VALUES) {
        let valueLength;
        const coModel = getRelation(field);
        const coField = getOrderByField(coModel);
        if (isX2MField(field)) {
            if (["float", "integer"].includes(coField.type)) {
                valueLength = coModel.reduce(
                    (longest, record) =>
                        Math.max(longest, String(record[coField.name]).length),
                    0,
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
            }),
        );
    } else if (field.type in DEFAULT_SELECTION_FIELD_VALUES) {
        valuesMap = new Map(field.selection.map((v, i) => [v[0], i]));
    }

    const sortedRecords = [...records].sort((r1, r2) => {
        if (!Object.hasOwn(r1, fieldNameSpec) || !Object.hasOwn(r2, fieldNameSpec)) {
            throw new MockServerError(
                `Cannot order by ${fieldNameSpec} because the field/spec isn't not in the record/group`,
            );
        }
        let v1 = r1[fieldNameSpec];
        let v2 = r2[fieldNameSpec];
        switch (field.type) {
            case "integer": {
                if (Array.isArray(v1)) {
                    v1 = v1[0];
                }
                if (Array.isArray(v2)) {
                    v2 = v2[0];
                }
                break;
            }
            case "boolean": {
                v1 = Number(v1);
                v2 = Number(v2);
                break;
            }
            case "many2one":
            case "many2one_reference": {
                v1 &&= valuesMap.get(v1[0] ?? v1);
                v2 &&= valuesMap.get(v2[0] ?? v2);
                break;
            }
            case "many2many":
            case "one2many": {
                v1 &&= v1.map((id) => valuesMap.get(id)).join("");
                v2 &&= v2.map((id) => valuesMap.get(id)).join("");
                break;
            }
            case "date":
            case "datetime": {
                v1 = Array.isArray(v1) ? new Date(v1[0]).getTime() : v1;
                v2 = Array.isArray(v2) ? new Date(v2[0]).getTime() : v2;
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
            if (
                !["boolean", "number", "string"].includes(typeof v1) ||
                typeof v1 !== typeof v2
            ) {
                throw new MockServerError(
                    `Cannot order by field "${fieldNameSpec}" in model "${
                        model._name
                    }": values must be of the same primitive type (got ${typeof v1} and ${typeof v2})`,
                );
            }
            result = v1 > v2 ? 1 : v1 < v2 ? -1 : 0;
        }
        return direction === "DESC" ? -result : result;
    });

    if (orderBys.length) {
        return orderByField(model, orderBys.join(","), sortedRecords);
    }

    return sortedRecords;
}

/**
 * @param {Model} model
 * @param {{
 * arch: string | Node;
 * editable?: boolean;
 * fields?: Record<string, FieldDefinition>;
 * level?: number;
 * modelName?: string;
 * processedNodes?: Node[];
 * }} params
 */
function parseView(model, params) {
    const processedNodes = params.processedNodes || [];
    const { arch } = params;
    const level = params.level || 0;
    const editable = params.editable || true;
    const fields = copyFields(model._fields);

    const { _onChanges } = model;
    const fieldNodes = {};
    const groupbyNodes = {};
    const relatedModels = { [model._name]: new Set() };
    const doc =
        typeof arch === "string"
            ? domParser.parseFromString(arch, "text/xml").documentElement
            : arch;
    const viewType = getTag(doc);
    const isEditable =
        editable && isViewEditable(/** @type {Element} */ (doc), model._name);

    traverseElement(doc, (node) => {
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return false;
        }
        const el = /** @type {Element} */ (node);
        for (const attr of ["required", "readonly", "invisible", "column_invisible"]) {
            if (/^(true|1)$/i.test(el.getAttribute(attr))) {
                el.setAttribute(attr, "True");
            }
        }
        const isField = getTag(node) === "field";
        const isGroupby = getTag(node) === "groupby";
        if (isField) {
            const fieldName = el.getAttribute("name");
            fieldNodes[fieldName] = {
                node,
                isInvisible: /^(true|1)$/i.test(el.getAttribute("invisible")),
                isEditable: isEditable && isViewEditable(el, model._name),
            };
            const field = fields[fieldName];
            if (!field) {
                throw fieldNotFoundError(model._name, fieldName);
            }
        } else if (isGroupby && !processedNodes.includes(node)) {
            const groupbyName = el.getAttribute("name");
            fieldNodes[groupbyName] = { node };
            groupbyNodes[groupbyName] = el;
        }
        if (isGroupby && !processedNodes.includes(node)) {
            return false;
        }
        return !isField;
    });
    for (const fieldName in fieldNodes) {
        relatedModels[model._name].add(fieldName);
    }
    for (const [name, { node: rawNode, isInvisible, isEditable }] of Object.entries(
        fieldNodes,
    )) {
        const node = /** @type {Element} */ (rawNode);
        const field = fields[name];
        if (isEditable && (isM2OField(field) || isX2MField(field))) {
            const canCreate = node.getAttribute("can_create");
            node.setAttribute("can_create", canCreate || "true");
            const canWrite = node.getAttribute("can_write");
            node.setAttribute("can_write", canWrite || "true");
        }
        if (isX2MField(field)) {
            const relModel = getRelation(field);
            if (
                viewType === "form" &&
                level === 0 &&
                !node.getAttribute("widget") &&
                !isInvisible
            ) {
                const inlineViewTypes = [...node.childNodes].map(getTag);
                const missingViewtypes = [];
                const nodeMode = getTag(node.getAttribute("mode"));
                if (
                    !intersection(inlineViewTypes, safeSplit(nodeMode || "kanban,list"))
                        .length
                ) {
                    missingViewtypes.push(safeSplit(nodeMode || "list")[0]);
                }
                for (const type of missingViewtypes) {
                    const [arch] = findView(
                        relModel,
                        /** @type {ViewType} */ (type),
                        false,
                    );
                    node.appendChild(
                        domParser.parseFromString(arch, "text/xml").documentElement,
                    );
                }
            }
            for (const childNode of node.childNodes) {
                if (childNode.nodeType === Node.ELEMENT_NODE) {
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
        if (
            isRelationalView(/** @type {ViewType} */ (viewType)) &&
            name in _onChanges
        ) {
            node.setAttribute("on_change", "1");
        }
    }
    for (const [name, node] of Object.entries(groupbyNodes)) {
        const field = fields[name];
        if (!isM2OField(field)) {
            throw new MockServerError(
                "Cannot group: 'groupby' can only target many2one fields",
            );
        }
        field.views = {};
        const coModel = getRelation(field);
        processedNodes.push(node);
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
        ir: elementToIR(/** @type {Element} */ (doc)),
        model: model._name,
        models: getViewFields(model, /** @type {ViewType} */ (viewType), relatedModels),
        type: viewType,
    };
}

/**
 * @param {Model} model
 * @param {string} fieldName
 * @param {DomainListRepr} domain
 * @param {boolean} [setCount]
 * @param {number | boolean} [limit]
 */
function searchPanelDomainImage(
    model,
    fieldName,
    domain,
    setCount = false,
    limit = false,
) {
    const field = model._fields[fieldName];
    let groupIdName;
    if (isM2OField(field)) {
        groupIdName = (value) => value || [false, undefined];
    } else if (field.type === "selection") {
        const selection = {};
        for (const [value, label] of model._fields[fieldName].selection) {
            selection[value] = label;
        }
        groupIdName = (value) => [value, selection[value]];
    }
    domain = new Domain([...domain, [fieldName, "!=", false]]).toList();
    const groups = model.formatted_read_group(
        domain,
        [fieldName],
        ["__count"],
        /** @type {any} */ (makeKwArgs({ limit })),
    );
    /** @type {Map<number, Record<string, any>>} */
    const domainImage = new Map();
    for (const group of groups) {
        const [id, display_name] = groupIdName(group[fieldName]);
        const values = { id, display_name };
        if (setCount) {
            values.__count = group.__count;
        }
        domainImage.set(id, values);
    }
    return domainImage;
}

/**
 * @param {Model} model
 * @param {string} fieldName
 * @param {KwArgs<{
 * enable_counters: boolean;
 * extra_domain: DomainListRepr;
 * limit: number;
 * only_counters: boolean;
 * set_limit: number;
 * }>} [kwargs={}]
 */
function searchPanelFieldImage(model, fieldName, kwargs) {
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
        setLimit && limit,
    );
    if (enableCounters && !noExtra) {
        const countDomainImage = searchPanelDomainImage(
            model,
            fieldName,
            countDomain,
            true,
        );
        for (const [id, values] of modelDomainImage.entries()) {
            const element = countDomainImage.get(id);
            values.__count = element ? element.__count : 0;
        }
    }

    return modelDomainImage;
}

/**
 * @param {Map<number, Record<string, any>>} valuesRange
 * @param {"parent_id" | false} parentName
 */
function searchPanelGlobalCounters(valuesRange, parentName) {
    const localCounters = [...valuesRange.keys()].map(
        (id) => valuesRange.get(id).__count,
    );
    const pName = /** @type {string} */ (parentName);
    for (let [id, values] of valuesRange.entries()) {
        const count = localCounters[id];
        if (count) {
            let parent_id = values[pName];
            while (parent_id) {
                values = valuesRange.get(parent_id);
                values.__count += count;
                parent_id = values[pName];
            }
        }
    }
}

/**
 * @param {Model} model
 * @param {"parent_id" | false} parentName
 * @param {number[]} ids
 */
function searchPanelSanitizedParentHierarchy(model, parentName, ids) {
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
                const pn = /** @type {string} */ (parentName);
                recordId = record[pn] && record[pn][0];
            } else {
                chainIsFullyIncluded = false;
            }
        }
        for (const id in ancestorChain) {
            recordsToKeep[id] = chainIsFullyIncluded;
        }
    }
    return model.filter((rec) => recordsToKeep[rec.id]);
}

/**
 * @param {Model} model
 * @param {string} fieldName
 * @param {KwArgs} [kwargs={}]
 */
function searchPanelSelectionRange(model, fieldName, kwargs) {
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
            values.__count = domainImage.get(value)
                ? domainImage.get(value).__count
                : 0;
        }
        selectionRange.push(values);
    }
    return selectionRange;
}

/** @param {ModelRecord} record */
function toIdDisplayName(record) {
    return record && [record.id, record.display_name];
}

/**
 * @param {Node} node
 * @param {(node: Node) => boolean} callback
 */
function traverseElement(node, callback) {
    if (callback(node)) {
        for (const child of node.childNodes) {
            traverseElement(child, callback);
        }
    }
}

/**
 * @param {Model} model
 * @param {ModelRecord} record
 * @param {ModelRecord} [originalRecord]
 */
function updateComodelRelationalFields(model, record, originalRecord) {
    for (const fname in record) {
        const field = model._fields[fname];
        const coModel = getRelation(field, record);
        const inverseFieldName =
            field.inverse_fname_by_model_name &&
            field.inverse_fname_by_model_name[coModel?._name];
        if (!inverseFieldName) {
            continue;
        }
        const relatedRecordIds = ensureArray(record[fname]);
        const comodelInverseField = coModel._fields[inverseFieldName];
        if (record[fname]) {
            for (const relatedRecordId of relatedRecordIds) {
                /** @type {any} */
                let inverseFieldNewValue = record.id;
                const relatedRecord = coModel.find(
                    (record) => record.id === relatedRecordId,
                );
                const relatedFieldValue =
                    relatedRecord && relatedRecord[inverseFieldName];
                if (
                    relatedFieldValue === undefined ||
                    relatedFieldValue === record.id ||
                    (field.type !== "one2many" && relatedFieldValue.includes(record.id))
                ) {
                    continue;
                }
                if (Array.isArray(relatedFieldValue)) {
                    inverseFieldNewValue = [...relatedFieldValue, record.id];
                }
                const data = /** @type {any} */ ({
                    [inverseFieldName]: inverseFieldNewValue,
                });
                if (comodelInverseField.type === "many2one_reference") {
                    data[comodelInverseField.model_name_ref_fname] = model._name;
                }
                /** @type {any} */ (coModel)._write(data, relatedRecordId);
            }
        } else if (field.type === "many2one_reference") {
            const model_many2one_field =
                comodelInverseField.inverse_fname_by_model_name[model._name];
            /** @type {any} */ (model)._write(
                { [model_many2one_field]: false },
                record.id,
            );
        }
        if (originalRecord) {
            const originalRecordIds = ensureArray(originalRecord[fname]);
            const removedRecordIds = originalRecordIds.filter(
                (recordId) =>
                    Number.isInteger(recordId) && !relatedRecordIds.includes(recordId),
            );
            for (const removedRecordId of removedRecordIds) {
                const removedRecord = coModel.find(
                    (record) => record.id === removedRecordId,
                );
                if (!removedRecord) {
                    continue;
                }
                /** @type {any} */
                let inverseFieldNewValue = false;
                if (Array.isArray(removedRecord[inverseFieldName])) {
                    inverseFieldNewValue = removedRecord[inverseFieldName].filter(
                        (id) => id !== record.id,
                    );
                }
                /** @type {any} */ (coModel)._write(
                    {
                        [inverseFieldName]: inverseFieldNewValue.length
                            ? inverseFieldNewValue
                            : false,
                    },
                    removedRecordId,
                );
            }
        }
    }
}

/**
 * @param {string} fieldName
 * @param {FieldDefinition} fieldDef
 */
function validateFieldDefinition(fieldName, fieldDef) {
    if (/** @type {any} */ (fieldDef)[S_FIELD] && fieldDef.name) {
        throw new MockServerError(
            `Cannot set the name of field "${fieldName}" from its definition: got "${fieldDef.name}"`,
        );
    }
    delete (/** @type {any} */ (fieldDef)[S_FIELD]);
    return fieldDef;
}

/**
 * @param {string} modelName
 * @param {ViewType} viewType
 * @param {number | false} viewId
 */
function viewNotFoundError(modelName, viewType, viewId, consequence) {
    let message = `Cannot find an arch for view "${viewType}" with ID ${JSON.stringify(
        viewId,
    )} in model "${modelName}"`;
    if (consequence) {
        message += `: ${consequence}`;
    }
    return new MockServerError(message);
}

/** @type {AggregatorFunction} */
function array_agg_distinct(records, fieldName) {
    return unique(records.map((record) => record[fieldName])).sort(compareAggregated);
}

/**
 * @param {any} a
 * @param {any} b
 * @returns {number}
 */
function compareAggregated(a, b) {
    if (typeof a === "number" && typeof b === "number") {
        return a - b;
    }
    return String(a).localeCompare(String(b));
}

/** @type {AggregatorFunction} */
function array_agg(records, fieldName) {
    return records.map((record) => record[fieldName]);
}

/** @type {AggregatorFunction} */
function bool_and(records, fieldName) {
    return records.length > 0 && records.every((record) => record[fieldName]);
}

/** @type {AggregatorFunction} */
function bool_or(records, fieldName) {
    return records.some((record) => record[fieldName]);
}

/** @type {AggregatorFunction} */
function count_distinct(records, fieldName) {
    return unique(records.map((record) => record[fieldName])).filter(
        (value) => value !== null && value !== undefined && value !== false,
    ).length;
}

/** @type {AggregatorFunction} */
function count(records) {
    return records.length;
}

/** @type {AggregatorFunction} */
function max(records, fieldName) {
    if (!records.length) {
        return false;
    }
    return records.reduce((best, record) => {
        const value = record[fieldName];
        return best === undefined || value > best ? value : best;
    }, undefined);
}

/** @type {AggregatorFunction} */
function min(records, fieldName) {
    if (!records.length) {
        return false;
    }
    return records.reduce((best, record) => {
        const value = record[fieldName];
        return best === undefined || value < best ? value : best;
    }, undefined);
}

/** @type {AggregatorFunction} */
function sum(records, fieldName) {
    if (!records.length) {
        return false;
    }
    return records.reduce((acc, record) => acc + record[fieldName], 0);
}

/** @type {AggregatorFunction} */
function avg(records, fieldName) {
    if (!records.length) {
        return false;
    }
    return sum(records, fieldName) / records.length;
}

/** @type {AggregatorFunction} */
function sum_currency(records, fieldName) {
    if (!records.length) {
        return false;
    }
    return records.reduce((acc, record) => acc + record[fieldName], 0);
}

const AGGREGATOR_FUNCTIONS = {
    array_agg_distinct,
    array_agg,
    avg,
    bool_and,
    bool_or,
    count_distinct,
    count,
    max,
    min,
    sum,
    sum_currency,
};
/** @type {Record<string, (date: luxon["DateTime"]["prototype"]) => string | number>} */
const DATE_FORMAT = {
    day_of_month: (date) => date.day,
    day_of_week: (date) => date.weekday % 7,
    day_of_year: (date) => date.ordinal,
    day: (date) => date.toFormat("yyyy-MM-dd"),
    iso_week_number: (date) => date.weekNumber,
    month_number: (date) => date.month,
    quarter_number: (date) => date.quarter,
    quarter: (date) => `Q${date.toFormat("q yyyy")}`,
    week: (date) => `W${date.toFormat("WW kkkk")}`,
    year_number: (date) => date.year,
    year: (date) => date.toFormat("yyyy"),
};
/** @type {Record<string, (date: luxon["DateTime"]["prototype"]) => string | number>} */
const DATETIME_FORMAT = {
    ...DATE_FORMAT,
    hour_number: (date) => date.hour,
    hour: (date) => date.toFormat("HH:00 dd MMM yyyy"),
    minute_number: (date) => date.minute,
    second_number: (date) => date.second,
};
/** @type {[string, Function | null][]} */
const INHERITED_OBJECT_KEYS = [
    ["_computes", null],
    ["_fields", copyFields],
    ["_onChanges", null],
    ["_toolbar", deepCopy],
    ["_views", null],
];
/** @type {[string, Function | null][]} */
const INHERITED_PRIMITIVE_KEYS = [
    ["_description", null],
    ["_fold_name", null],
    ["_inherit", null],
    ["_order", null],
    ["_parent_name", null],
    ["_rec_name", null],
    ["_related", (set) => new Set(set)],
];
const READ_GROUP_NUMBER_GRANULARITY = /** @type {const} */ ([
    "day_of_month",
    "day_of_week",
    "day_of_year",
    "hour_number",
    "iso_week_number",
    "minute_number",
    "month_number",
    "quarter_number",
    "second_number",
    "year_number",
]);

/** @typedef {READ_GROUP_NUMBER_GRANULARITY[number]} ReadGroupNumberGranularity */

const MAX_NUMBER_OPENED_GROUPS = 10;

const R_AGGREGATE_FUNCTION = /(\w+):(\w+)/;
const R_CAMEL_CASE = /([a-z])([A-Z])/g;
const R_DATE = /\d{4}-\d{2}-\d{2}/;
const R_DATE_TIME = /\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?/;

/** @type {Record<string, Partial<Record<ViewKey, string>>>} */
const inlineViewArchs = Object.create(null);
const domParser = new DOMParser();
const xmlSerializer = new XMLSerializer();
let modelInstanceLock = 0;

/**
 * @param {string} modelName
 * @param {Partial<Record<ViewKey, string>>} archs
 */
export function registerInlineViewArchs(modelName, archs) {
    if (!inlineViewArchs[modelName]) {
        inlineViewArchs[modelName] = Object.create(null);
        after(() => delete inlineViewArchs[modelName]);
    }
    const modelViews = inlineViewArchs[modelName];
    for (const [rawKey, arch] of Object.entries(archs)) {
        modelViews[getViewKey(.../** @type {[any, any]} */ (safeSplit(rawKey)))] = arch;
    }
}

/** @extends {Array<ModelRecord>} */
export class Model extends Array {
    /** @type {ReturnType<typeof createJobScopedGetter<typeof getModelDefinition>> | null} */
    static definitionGetter = null;

    static get definition() {
        this.definitionGetter ||= createJobScopedGetter(getModelDefinition);
        return this.definitionGetter(this);
    }

    static get _description() {
        return this.definition._description;
    }
    static set _description(value) {
        this.definition._description = value;
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

    static get _fold_name() {
        return this.definition._fold_name;
    }
    static set _fold_name(value) {
        this.definition._fold_name = value;
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
        return this.definition._records;
    }
    static set _records(value) {
        assignArray(this.definition._records, value);
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

    /** @param {Model} [instance] */
    static getModelName(instance) {
        instance ||= createRawInstance(this);
        return (
            instance._name ||
            safeSplit(instance._inherit)[0] ||
            (this.name
                ? this.name.replace(R_CAMEL_CASE, "$1.$2").toLowerCase()
                : "anonymous")
        );
    }

    /** @type {Record<string, (this: Model, fieldName: string) => void>} */
    _computes = {};
    _description = "";
    /** @type {Record<string, any>} */
    _fields = {};
    /** @type {Record<string, any>[]} */
    _filters = [];
    /** @type {string} */
    _fold_name = "fold";
    /** @type {string | string[] | null} */
    _inherit = null;
    /** @type {string} */
    _name = "";
    /** @type {Record<string, boolean | ((record: ModelRecord) => any)>} */
    _onChanges = {};
    /** @type {string} */
    _order = "id";
    _parent_name = "parent_id";
    /** @type {string | null} */
    _rec_name = null;
    /** @type {Partial<ModelRecord>[]} */
    _records = [];
    /** @type {Set<string>} */
    _related = new Set();
    /** @type {Record<string, any>} */
    _toolbar = {};
    /** @type {Partial<Record<ViewKey, string>>} */
    _views = {};

    get env() {
        return MockServer.env;
    }

    id = fields.Integer({ readonly: true, aggregator: undefined });
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
            const modelInstance = /** @type {any} */ (this.constructor).definition;

            this._computes = modelInstance._computes;
            this._description = modelInstance._description;
            this._fields = modelInstance._fields;
            this._fold_name = modelInstance._fold_name;
            this._inherit = modelInstance._inherit;
            this._name = modelInstance._name;
            this._onChanges = modelInstance._onChanges;
            this._order = modelInstance._order;
            this._parent_name = modelInstance._parent_name;
            this._rec_name = modelInstance._rec_name;
            this._related = modelInstance._related;
            this._views = modelInstance._views;
        }
    }

    /** @param {MaybeIterable<number | false>} idOrIds */
    action_archive(idOrIds) {
        const kwargs = getKwArgs(arguments, "ids");
        ({ ids: idOrIds } = kwargs);

        return this.write(idOrIds, { active: false }, kwargs);
    }

    /** @param {MaybeIterable<number | false>} idOrIds */
    action_unarchive(idOrIds) {
        const kwargs = getKwArgs(arguments, "ids");
        ({ ids: idOrIds } = kwargs);

        return this.write(idOrIds, { active: true }, kwargs);
    }

    /** @param {MaybeIterable<number | false>} idOrIds */
    browse(idOrIds) {
        const ids = ensureArray(idOrIds);
        const records = new /** @type {any} */ (this.constructor)();
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
     * @param {MaybeIterable<number | false>} idOrIds
     * @param {Partial<ModelRecord>} defaultValues
     */
    copy(idOrIds, defaultValues) {
        ({ ids: idOrIds, default: defaultValues } = getKwArgs(
            arguments,
            "ids",
            "default",
        ));

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
     * @param {MaybeIterable<Partial<ModelRecord>>} valuesList
     * @param {KwArgs} [_kwargs]
     */
    create(valuesList, _kwargs = {}) {
        const kwargs = getKwArgs(arguments, "vals_list");
        ({ vals_list: valuesList } = kwargs);

        const shouldReturnList = isIterable(valuesList);
        const allValues = shouldReturnList
            ? /** @type {Iterable<Partial<ModelRecord>>} */ (valuesList)
            : [/** @type {Partial<ModelRecord>} */ (valuesList)];
        /** @type {number[]} */
        const ids = [];
        for (const values of allValues) {
            if ("id" in values) {
                throw new MockServerError(
                    `Cannot create a record with a given ID value`,
                );
            }
            const record = /** @type {ModelRecord} */ ({ id: this._getNextId() });
            const recordId = /** @type {number} */ (record.id);
            ids.push(recordId);
            this.push(record);
            this._applyDefaults(/** @type {any} */ (values), kwargs.context);
            this._write(/** @type {any} */ (values), recordId);
        }
        this.browse(ids)._applyComputesAndValidate();
        return shouldReturnList ? ids : ids[0];
    }

    /** @param {Iterable<string>} fields */
    default_get(fields) {
        const kwargs = getKwArgs(arguments, "fields_list");
        ({ fields_list: fields } = kwargs);

        /** @type {Record<string, any>} */
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
                        `Missing default value for field type "${field.type}"`,
                    );
                }
                result[fieldName] = DEFAULT_FIELD_VALUES[field.type]();
            }
        }
        for (const fieldName in result) {
            const field = this._fields[fieldName];
            if (isM2OField(field) && result[fieldName]) {
                if (!isValidId(result[fieldName], field, /** @type {any} */ (result))) {
                    delete result[fieldName];
                }
            }
        }
        return result;
    }

    /**
     * @param {Iterable<string>} [fieldNames]
     * @param {Iterable<string>} [attributes]
     */
    fields_get(fieldNames, attributes) {
        const kwargs = getKwArgs(arguments, "allfields", "attributes");
        ({ allfields: fieldNames, attributes } = kwargs);

        const fields = fieldNames ? pick(this._fields, ...fieldNames) : this._fields;
        if (!attributes) {
            return fields;
        }

        return Object.fromEntries(
            Object.entries(fields).map(([name, field]) => [
                name,
                pick(field, ...attributes),
            ]),
        );
    }

    /**
     * @param {DomainListRepr} domain
     * @param {string[]} groupby
     * @param {string[]} aggregates
     * @param {DomainListRepr} [having]
     * @param {number} [offset]
     * @param {number} [limit]
     * @param {string} [order]
     */
    formatted_read_group(domain, groupby, aggregates, having, offset, limit, order) {
        const kwargs = getKwArgs(
            arguments,
            "domain",
            "groupby",
            "aggregates",
            "having",
            "offset",
            "limit",
            "order",
        );
        ({ domain, groupby, aggregates, having, offset, limit, order } = kwargs);

        const records = this._filter(domain);
        const aggregatedFields = /** @type {AggregatedField[]} */ (
            aggregates.map((fspec) => {
                if (fspec === "__count") {
                    return { fieldName: "__count", func: "count", name: "__count" };
                }
                const [, fieldName, func] = fspec.match(R_AGGREGATE_FUNCTION);
                if (func && !(func in AGGREGATOR_FUNCTIONS)) {
                    throw new MockServerError(`Invalid aggregation function "${func}"`);
                }
                if (!this._fields[fieldName]) {
                    throw new MockServerError(`Invalid field in "${fspec}"`);
                }
                return { fieldName, func, name: fspec };
            })
        );

        if (!groupby.length) {
            const group = /** @type {ModelRecordGroup} */ ({ __extra_domain: [] });
            aggregateFields(aggregatedFields, group, records);
            return [group];
        }

        /** @type {Record<any, ModelRecord[]>} */
        const groups = {};
        for (const record of records) {
            const recordGroupsValues = [{}];
            for (const groupbySpec of groupby) {
                const [fieldName] = String(groupbySpec).split(":");
                const [recordValue, field] = this._followRelation(
                    record,
                    fieldName.split("."),
                );
                const value = formatFieldValue(field.type, groupbySpec, recordValue);

                if (field.type === "many2many" && value) {
                    for (const group of [...recordGroupsValues]) {
                        for (const [index, id] of Object.entries(value)) {
                            // eslint-disable-next-line eqeqeq -- index is a string key from Object.entries; loose == 0 matches only the first ("0") entry, === would never match
                            if (/** @type {any} */ (index) == 0) {
                                group[groupbySpec] = id;
                            } else {
                                const new_group = { ...group };
                                new_group[groupbySpec] = id;
                                recordGroupsValues.push(new_group);
                            }
                        }
                    }
                } else {
                    for (const group of recordGroupsValues) {
                        group[groupbySpec] = value;
                    }
                }
            }
            for (const group of recordGroupsValues) {
                const valueKey = JSON.stringify(group);
                groups[valueKey] = groups[valueKey] || [];
                groups[valueKey].push(record);
            }
        }

        /** @type {ModelRecordGroup[]} */
        let readGroupResult = [];
        for (const [groupKey, groupRecords] of Object.entries(groups)) {
            /** @type {ModelRecordGroup} */
            const group = {
                ...JSON.parse(groupKey),
                __extra_domain: [],
            };
            for (const groupbySpec of groupby) {
                const [fieldPath, granularity] = safeSplit(groupbySpec, ":");
                const value = Number.isInteger(group[groupbySpec])
                    ? group[groupbySpec]
                    : group[groupbySpec] || false;
                const [, field] = this._followRelation(
                    /** @type {any} */ ({}),
                    fieldPath.split("."),
                );
                const { relation, type } = field;

                if (relation && !Array.isArray(value)) {
                    const relatedRecord = this.env[relation].find(
                        ({ id }) => id === value,
                    );
                    if (relatedRecord) {
                        group[groupbySpec] = [value, relatedRecord.display_name];
                        const _fold_name = this.env[relation]._fold_name;
                        if (_fold_name in this.env[relation]._fields) {
                            group.__fold = relatedRecord[_fold_name] || false;
                        }
                    } else {
                        group[groupbySpec] = false;
                    }
                } else if (fieldPath === "id") {
                    if (!value) {
                        group[groupbySpec] = false;
                    } else {
                        const relatedRecord = this.env[this._name].find(
                            ({ id }) => id === value,
                        );
                        const displayName = relatedRecord?.display_name || "";
                        group[groupbySpec] = [value, displayName];
                    }
                }
                if (isDateField(type)) {
                    if (value) {
                        if (
                            READ_GROUP_NUMBER_GRANULARITY.includes(
                                /** @type {any} */ (granularity),
                            )
                        ) {
                            group.__extra_domain = [
                                ...this._readGroupExtraDomain(
                                    fieldPath,
                                    value,
                                    /** @type {any} */ (granularity),
                                ),
                                ...group.__extra_domain,
                            ];
                        } else {
                            let startDate, endDate;
                            switch (granularity) {
                                case "hour": {
                                    startDate = parseDateTime(value, {
                                        format: "HH:00 dd MMM yyyy",
                                    });
                                    endDate = startDate.plus({ hours: 1 });
                                    group[groupbySpec] =
                                        startDate.toFormat("HH:00 dd MMM");
                                    break;
                                }
                                case "day": {
                                    startDate = parseDateTime(value, {
                                        format: "yyyy-MM-dd",
                                    });
                                    endDate = startDate.plus({ days: 1 });
                                    break;
                                }
                                case "week": {
                                    startDate = parseDateTime(value, {
                                        format: "WW kkkk",
                                    });
                                    endDate = startDate.plus({ weeks: 1 });
                                    break;
                                }
                                case "quarter": {
                                    startDate = parseDateTime(value, {
                                        format: "q yyyy",
                                    });
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
                                    startDate = parseDateTime(value, {
                                        format: "MMMM yyyy",
                                    });
                                    endDate = startDate.plus({ months: 1 });
                                    break;
                                }
                            }
                            const serialize =
                                type === "date" ? serializeDate : serializeDateTime;
                            const from = serialize(startDate);
                            const to = serialize(endDate);
                            if (from === false || to === false) {
                                throw new MockServerError(
                                    `Invalid date range for "${fieldPath}"`,
                                );
                            }
                            group.__extra_domain = [
                                ...this._readGroupDateRangeExtraDomain(
                                    fieldPath,
                                    from,
                                    to,
                                ),
                                ...group.__extra_domain,
                            ];
                            group[groupbySpec] = [from, group[groupbySpec]];
                        }
                    } else {
                        group.__extra_domain = [
                            ...this._readGroupExtraDomain(fieldPath, value),
                            ...group.__extra_domain,
                        ];
                    }
                } else {
                    group.__extra_domain = [
                        ...this._readGroupExtraDomain(fieldPath, value),
                        ...group.__extra_domain,
                    ];
                }
            }
            aggregateFields(aggregatedFields, group, groupRecords);
            readGroupResult.push(group);
        }

        readGroupResult = orderByField(
            this,
            order || groupby.join(","),
            readGroupResult,
        );

        if (limit) {
            offset ||= 0;
            readGroupResult = readGroupResult.slice(offset, limit + offset);
        }

        return readGroupResult;
    }

    formatted_read_grouping_sets(domain, grouping_sets, aggregates, having, order) {
        const kwargs = getKwArgs(
            arguments,
            "domain",
            "grouping_sets",
            "aggregates",
            "having",
            "order",
        );
        ({ domain, grouping_sets, aggregates, having, order } = kwargs);
        const result = [];
        for (const groupby of grouping_sets) {
            let current_order = order;
            if (order) {
                const parts = [];
                for (const order_part of order.split(",")) {
                    const fname = order_part.split(" ", 1)[0];
                    if (groupby.includes(fname) || aggregates.includes(fname)) {
                        parts.push(order_part);
                    }
                }
                current_order = parts.join(",");
            }
            result.push(
                this.formatted_read_group(
                    domain,
                    groupby,
                    aggregates,
                    having,
                    null,
                    null,
                    current_order,
                ),
            );
        }
        return result;
    }

    /**
     * @param {[number | false, string][]} views
     * @param {{ load_filters?: boolean, arch?: boolean }} [options]
     */
    get_views(views, options) {
        const kwargs = getKwArgs(arguments, "views", "options");
        ({ views, options = {} } = kwargs);

        /** @type {Record<string, any>} */
        const models = {};
        /** @type {Record<string, any>} */
        const result = {};

        const modelFields = {};
        for (const [viewId, viewType] of views) {
            result[viewType] = getView(
                this,
                [viewId, /** @type {ViewType} */ (viewType)],
                kwargs,
            );
            for (const [modelName, fields] of Object.entries(result[viewType].models)) {
                modelFields[modelName] ||= { fields: new Set() };
                for (const field of fields) {
                    modelFields[modelName].fields.add(field);
                }
            }
            delete result[viewType].models;
            if (options.arch === false) {
                delete result[viewType].arch;
            }
        }

        for (const [modelName, value] of Object.entries(modelFields)) {
            models[modelName] = {
                fields: this.env[modelName].fields_get(value.fields),
            };
        }

        if (options.load_filters && "search" in result) {
            result["search"].filters = this._filters;
        }
        return { models, views: result };
    }

    /** @param {string} name */
    name_create(name) {
        const kwargs = getKwArgs(arguments, "name");
        ({ name } = kwargs);

        const values = /** @type {any} */ ({
            [this._rec_name]: name,
            display_name: name,
        });
        const [id] = /** @type {number[]} */ (this.create([values], kwargs));
        return [id, kwargs.name];
    }

    /**
     * @param {string} [name]
     * @param {DomainListRepr} [domain]
     * @param {string} [operator]
     * @param {number} [limit]
     */
    name_search(name, domain, operator, limit) {
        const kwargs = getKwArgs(arguments, "name", "domain", "operator", "limit");
        ({ name = "", domain = [], operator = "ilike", limit = 100 } = kwargs);

        const actualDomain = new Domain(domain);
        /** @type {[number, string][]} */
        const result = [];
        for (const record of this) {
            const isInDomain = actualDomain.contains(record);
            if (isInDomain && (!name || (record.display_name || "").includes(name))) {
                result.push(/** @type {any} */ (toIdDisplayName(record)));
            }
        }
        return result.slice(0, limit);
    }

    /**
     * @param {any} ids
     * @param {Record<string, any>} values
     * @param {any} fieldNames
     * @param {Record<string, any>} fieldsSpec
     */
    onchange(ids, values, fieldNames, fieldsSpec) {
        const kwargs = getKwArgs(
            arguments,
            "ids",
            "values",
            "field_names",
            "fields_spec",
        );
        ({ ids, values, field_names: fieldNames, fields_spec: fieldsSpec } = kwargs);

        fieldNames = ensureArray(fieldNames || []);

        const firstOnChange = !fieldNames.length;
        const fieldsFromView = Object.keys(fieldsSpec);

        /** @type {Record<string, any>} */
        let serverValues = {};
        /** @type {Record<string, any>} */
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
            serverValues = this.read(
                ids,
                fieldsFromView,
                /** @type {any} */ (kwargs),
            )[0];
        } else if (firstOnChange) {
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
                            command[2] = pick(
                                command[2],
                                ...Object.keys(subSpec.fields),
                            );
                        }
                    }
                }
            }
            Object.assign(onchangeValues, defaultValues);
        }

        const finalValues = { ...serverValues, ...onchangeValues, ...values };
        const proxy = new Proxy(finalValues, {
            set(target, p, newValue) {
                const key = /** @type {string} */ (p);
                if (target[key] !== newValue) {
                    onchangeValues[key] = newValue;
                }
                return Reflect.set(target, p, newValue);
            },
        });

        for (const field of fieldNames) {
            if (typeof this._onChanges[field] === "function") {
                this._onChanges[field](/** @type {any} */ (proxy));
            }
        }

        return {
            value: convertToOnChange(
                this,
                /** @type {any} */ (onchangeValues),
                fieldsSpec,
            ),
        };
    }

    /**
     * @param {MaybeIterable<number | false>} idOrIds
     * @param {string[]} [fields]
     * @param {string | false} [load]
     */
    read(idOrIds, fields, load) {
        const kwargs = getKwArgs(arguments, "ids", "fields", "load");
        ({ ids: idOrIds, fields, load } = kwargs);

        const fieldNames = fields?.length ? fields : Object.keys(this._fields);
        return this._read_format(idOrIds, fieldNames, load);
    }

    /** @param {KwArgs<{ domain: DomainListRepr, group_by: string, progress_bar: any }>} [kwargs={}] */
    /**
     * @param {DomainListRepr} domain
     * @param {string} groupBy
     * @param {any} progressBar
     */
    read_progress_bar(domain, groupBy, progressBar) {
        const kwargs = getKwArgs(arguments, "domain", "group_by", "progress_bar");
        ({ domain, group_by: groupBy, progress_bar: progressBar } = kwargs);

        const groups = this.formatted_read_group(
            domain,
            [groupBy, progressBar.field],
            ["__count"],
        );

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

    render_public_asset() {
        return true;
    }

    /**
     * @overload
     * @param {DomainListRepr} domain
     * @param {KwArgs<{offset: number, limit: number, order: string}>} options
     * @returns {number[]}
     */
    /**
     * @overload
     * @param {DomainListRepr} domain
     * @param {number} [offset]
     * @param {number} [limit]
     * @param {string} [order]
     * @returns {number[]}
     */
    /**
     * @param {DomainListRepr} domain
     * @param {number | KwArgs<{offset: number, limit: number, order: string}>} [offset]
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
            offset: /** @type {number|undefined} */ (offset),
            order,
        });
        return records.map((record) => /** @type {number} */ (record.id));
    }

    /**
     * @param {DomainListRepr} domain
     * @param {number} [limit]
     */
    search_count(domain, limit) {
        const kwargs = getKwArgs(arguments, "domain", "limit");
        ({ domain, limit } = kwargs);

        return this._search(/** @type {any} */ (kwargs)).length;
    }

    /** @param {string} fieldName */
    search_panel_select_range(fieldName) {
        /**
         * @type {KwArgs<{
         * category_domain: DomainListRepr;
         * comodel_domain: DomainListRepr;
         * enable_counters: boolean;
         * filter_domain: DomainListRepr;
         * limit: number;
         * search_domain: DomainListRepr;
         * }>}
         */
        const kwargs = getKwArgs(arguments, "field_name");
        ({ field_name: fieldName } = kwargs);

        const field = this._fields[fieldName];
        const coModel = getRelation(field);
        const supportedTypes = ["many2one", "selection"];
        if (!supportedTypes.includes(field.type)) {
            throw new MockServerError(
                `Only category types ${supportedTypes.join(" and ")} are supported, got "${
                    field.type
                }"`,
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
        /** @type {string | false} */
        let parentName = false;
        if (hierarchize && coModel._fields[coModel._parent_name]) {
            parentName = coModel._parent_name;
            fieldNames.push(/** @type {string} */ (parentName));
            getParentId = (record) =>
                record[/** @type {string} */ (parentName)]?.[0] ?? false;
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
                set_limit: /** @type {any} */ (
                    limit && !(expand || hierarchize || comodelDomain)
                ),
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
                        recordId = record[/** @type {string} */ (parentName)];
                    }
                }
                condition = /** @type {any} */ (["id", "in", unique(ancestorIds)]);
            } else {
                condition = /** @type {any} */ (["id", "in", imageElementIds]);
            }
            comodelDomain = new Domain([...comodelDomain, condition]).toList();
        }

        let comodelRecords = coModel.search_read(comodelDomain, fieldNames, kwargs);

        if (hierarchize) {
            const ids = expand ? comodelRecords.map((rec) => rec.id) : imageElementIds;
            comodelRecords = searchPanelSanitizedParentHierarchy(
                comodelRecords,
                /** @type {any} */ (parentName),
                ids,
            );
        }

        if (limit && comodelRecords.length === limit) {
            return { error_msg: "Too many items to display." };
        }
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
            searchPanelGlobalCounters(fieldRange, /** @type {any} */ (parentName));
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
         * category_domain: DomainListRepr;
         * comodel_domain: DomainListRepr;
         * enable_counters: boolean;
         * filter_domain: DomainListRepr;
         * limit: number;
         * search_domain: DomainListRepr;
         * }>}
         */
        const kwargs = getKwArgs(arguments, "field_name", "group_by");
        ({ field_name: fieldName, group_by: groupBy } = kwargs);

        const field = this._fields[fieldName];
        const coModel = getRelation(field);
        const supportedTypes = ["many2many", "many2one", "selection"];
        if (!supportedTypes.includes(field.type)) {
            throw new MockServerError(
                `Only filter types ${supportedTypes} are supported, got "${field.type}"`,
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
                const groupBySelection = /** @type {any} */ ({
                    ...coModel._fields[groupBy].selection,
                    [/** @type {any} */ (false)]: "Not Set",
                });
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
            const comodelRecords = coModel.search_read(
                comodelDomain,
                fieldNames,
                kwargs,
            );
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
                        if (
                            enableCounters &&
                            JSON.stringify(localExtraDomain) === "[]"
                        ) {
                            inImage = count;
                        } else {
                            inImage = this.search(
                                searchDomain,
                                /** @type {any} */ ([]),
                                1,
                            ).length;
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
                extraDomain = new Domain([
                    ...extraDomain,
                    ...(kwargs.group_domain || []),
                ]).toList();
                modelDomain = new Domain([
                    ...modelDomain,
                    ...(kwargs.group_domain || []),
                ]).toList();
                domainImage = searchPanelFieldImage(this, fieldName, {
                    ...kwargs,
                    model_domain: modelDomain,
                    extra_domain: extraDomain,
                    only_counters: expand,
                    set_limit: /** @type {any} */ (
                        limit && !(expand || groupBy || comodelDomain)
                    ),
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
            const comodelRecords = coModel.search_read(
                comodelDomain,
                fieldNames,
                kwargs,
            );
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
     * @param {string[]} [fields]
     * @param {number} [offset]
     * @param {number} [limit]
     * @param {string} [order]
     * @param {boolean | KwArgs<{context: object}>} [load=true]
     */
    search_read(domain, fields, offset, limit, order, load = true) {
        const kwargs = getKwArgs(
            arguments,
            "domain",
            "fields",
            "offset",
            "limit",
            "order",
            "load",
        );
        ({ domain, fields, offset, limit, order, load } = kwargs);

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
            unique([...fields, "id"]),
            /** @type {any} */ (load),
        );
    }

    /** @param {MaybeIterable<number | false>} idOrIds */
    unlink(idOrIds) {
        const kwargs = getKwArgs(arguments, "ids");
        ({ ids: idOrIds } = kwargs);

        const ids = ensureArray(idOrIds);
        for (let i = this.length - 1; i >= 0; i--) {
            if (ids.includes(/** @type {number} */ (this[i].id))) {
                this.splice(i, 1);
            }
        }

        for (const model of Object.values(
            /** @type {any} */ (MockServer.current)._models,
        )) {
            for (const [fieldName, field] of Object.entries(model._fields)) {
                const coModel = getRelation(field);
                if (coModel?._name === this._name) {
                    for (const record of model) {
                        if (Array.isArray(record[fieldName])) {
                            record[fieldName] = record[fieldName].filter(
                                (id) => !ids.includes(id),
                            );
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
     * @param {string} name
     * @param {Record<string, any>} specification
     * @param {DomainListRepr} [domain]
     * @param {string} [operator]
     * @param {number} [limit]
     */
    web_name_search(name, specification, domain, operator, limit) {
        const kwargs = getKwArgs(
            arguments,
            "name",
            "specification",
            "args",
            "operator",
            "limit",
        );
        ({
            name,
            specification,
            domain = [],
            operator = "ilike",
            limit = 100,
        } = kwargs);

        const idNamePairs = this.name_search(
            name,
            domain,
            operator,
            limit,
            /** @type {any} */ (kwargs),
        );
        if (
            Object.keys(specification).length === 1 &&
            "display_name" in specification
        ) {
            return idNamePairs.map(([id, name]) => ({
                id,
                display_name: name,
                __formatted_display_name: name,
            }));
        }

        return this.web_read(
            idNamePairs.map(([id]) => id),
            specification,
        );
    }

    /**
     * @param {MaybeIterable<number | false>} idOrIds
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
        const records = this.read(ids, fieldNames, /** @type {any} */ (kwargs));
        this._unityReadRecords(records, specification);
        return records;
    }

    /**
     * @param {DomainListRepr} domain
     * @param {string[]} groupby
     * @param {string[]} aggregates
     * @param {number} [limit]
     * @param {number} [offset]
     * @param {string} [order]
     * @param {any} [auto_unfold]
     * @param {any} [opening_info]
     * @param {any} [unfold_read_specification]
     * @param {any} [unfold_read_default_limit]
     * @param {any} [groupby_read_specification]
     */
    web_read_group(
        domain,
        groupby,
        aggregates,
        limit,
        offset,
        order,
        auto_unfold,
        opening_info,
        unfold_read_specification,
        unfold_read_default_limit,
        groupby_read_specification,
    ) {
        const kwargs = getKwArgs(
            arguments,
            "domain",
            "groupby",
            "aggregates",
            "limit",
            "offset",
            "order",
            "auto_unfold",
            "opening_info",
            "unfold_read_specification",
            "unfold_read_default_limit",
            "groupby_read_specification",
        );
        ({
            domain,
            groupby,
            aggregates,
            limit,
            offset,
            order,
            auto_unfold,
            opening_info,
            unfold_read_specification,
            unfold_read_default_limit,
            groupby_read_specification,
        } = kwargs);

        aggregates = ["__count", ...aggregates];
        const read_group_order = getReadGroupOrder(order, [groupby[0]], aggregates);
        let groups = this.formatted_read_group(
            domain,
            [groupby[0]],
            aggregates,
            [],
            null,
            null,
            read_group_order,
        );
        const length = groups.length;
        offset = offset || 0;
        groups = groups.slice(offset, limit ? limit + offset : undefined);

        this._openGroups(
            groups,
            domain,
            groupby,
            aggregates,
            order,
            opening_info,
            auto_unfold,
            {
                specification: unfold_read_specification,
                offset: 0,
                limit: unfold_read_default_limit,
                order: order,
            },
            groupby_read_specification,
        );

        return { groups, length };
    }

    _openGroups(
        groups,
        mainDomain,
        remainingGroupby,
        aggregates,
        order,
        infoOpening,
        autoUnfold,
        webSearchArgs,
        groupbyReadSpecification,
    ) {
        /** @type {any} */
        let groupInfos = false;
        if (infoOpening && infoOpening.length !== 0) {
            groupInfos = Object.fromEntries(
                infoOpening.map((info) => [info.value, info]),
            );
        }
        const previousGroupby = remainingGroupby[0];
        const field = this._fields[previousGroupby.split(":")[0]];
        let nbOpenedGroup = 0;

        if (
            groupbyReadSpecification &&
            Object.hasOwn(groupbyReadSpecification, previousGroupby)
        ) {
            const readSpec = groupbyReadSpecification[previousGroupby];
            for (const group of groups) {
                const groupbyValue = group[previousGroupby];
                if (Array.isArray(groupbyValue)) {
                    const id = groupbyValue[0];
                    group.__values = this.env[field.relation].web_read(
                        [id],
                        readSpec,
                    )[0];
                } else {
                    group.__values = { id: false };
                }
            }
        }

        for (const group of groups) {
            let fold = false;
            let foldInfo = false;
            if (Object.hasOwn(group, "__fold")) {
                fold = group.__fold;
                foldInfo = true;
                delete group.__fold;
            }

            if (nbOpenedGroup >= MAX_NUMBER_OPENED_GROUPS) {
                continue;
            }

            const groupbyValue = group[previousGroupby];
            const rawGroupbyValue = Array.isArray(groupbyValue)
                ? groupbyValue[0]
                : groupbyValue;

            const argsRead = { ...webSearchArgs };
            let subgroupOpeningInfo = null;
            let extraDomain = [];
            if (groupInfos && Object.hasOwn(groupInfos, rawGroupbyValue)) {
                const groupInfo = groupInfos[rawGroupbyValue];
                if (groupInfo.folded) {
                    continue;
                }
                argsRead.limit = groupInfo.limit;
                argsRead.offset = groupInfo.offset;
                extraDomain = groupInfo.progressbar_domain || [];
                subgroupOpeningInfo = groupInfo.groups;
            } else if (
                (!foldInfo && !autoUnfold) ||
                fold ||
                (field.relation && !groupbyValue)
            ) {
                continue;
            }

            nbOpenedGroup += 1;
            if (remainingGroupby.length === 1) {
                if (argsRead.offset && argsRead.offset >= group.__count) {
                    group.__offset = 0;
                    argsRead.offset = 0;
                }
                const groupDomain = [
                    ...group.__extra_domain,
                    ...mainDomain,
                    ...extraDomain,
                ];
                if (extraDomain.length && aggregates.length) {
                    const filteredAggregates = aggregates.filter(
                        (spec) => spec !== "__count",
                    );
                    if (filteredAggregates.length) {
                        const [filteredValues] = this.formatted_read_group(
                            groupDomain,
                            [],
                            filteredAggregates,
                        );
                        for (const spec of filteredAggregates) {
                            group[spec] = filteredValues[spec];
                        }
                    }
                }
                if (argsRead.order) {
                    const orderedFields = argsRead.order
                        .split(",")
                        .map((part) => part.trim().split(" ")[0]);
                    if (!orderedFields.includes("id")) {
                        argsRead.order += ", id ASC";
                    }
                }
                group.__records = this.web_search_read(
                    groupDomain,
                    .../** @type {[any, any, any, any]} */ (Object.values(argsRead)),
                ).records;
            } else {
                const groupDomain = [...group.__extra_domain, ...mainDomain];

                let groups = this.formatted_read_group(
                    groupDomain,
                    [remainingGroupby[1]],
                    aggregates,
                    [],
                    null,
                    null,
                    getReadGroupOrder(order, [remainingGroupby[1]], aggregates),
                );
                const length = groups.length;
                const subOffset = argsRead.offset || 0;
                groups = groups.slice(
                    subOffset,
                    argsRead.limit ? subOffset + argsRead.limit : undefined,
                );
                group.__groups = { groups, length };

                this._openGroups(
                    groups,
                    groupDomain,
                    remainingGroupby.slice(1),
                    aggregates,
                    order,
                    subgroupOpeningInfo,
                    0,
                    webSearchArgs,
                    groupbyReadSpecification,
                );
            }
        }
    }

    /**
     * @param {MaybeIterable<number | false>} idOrIds
     * @param {Record<string, any>} specification
     * @param {string} fieldName
     * @param {number} offset
     */
    web_resequence(idOrIds, specification, fieldName, offset) {
        const kwargs = getKwArgs(
            arguments,
            "ids",
            "field_name",
            "offset",
            "specification",
        );
        ({ ids: idOrIds, field_name: fieldName, offset = 0, specification } = kwargs);

        if (!(fieldName in this._fields)) {
            return [];
        }

        const ids = ensureArray(idOrIds);
        for (const [index, id] of ids.entries()) {
            this.write(id, { [fieldName]: offset + index });
        }

        return this.web_read(ids, specification);
    }

    /**
     * @param {MaybeIterable<number | false>} idOrIds
     * @param {Partial<ModelRecord>} values
     * @param {Record<string, any>} specification
     * @param {MaybeIterable<number>} [nextId]
     * @param {Record<string, any>} [knownValues]
     */
    web_save(idOrIds, values, specification, nextId, knownValues) {
        const kwargs = getKwArgs(
            arguments,
            "ids",
            "vals",
            "specification",
            "next_id",
            "known_values",
        );
        ({
            ids: idOrIds,
            vals: values,
            specification,
            next_id: nextId,
            known_values: knownValues,
        } = kwargs);

        let ids = ensureArray(idOrIds);
        if (ids.length && knownValues) {
            this._checkConcurrentFieldChanges(
                ids.filter((id) => id !== false),
                values,
                knownValues,
            );
        }
        if (ids.length === 0) {
            ids = /** @type {number[]} */ (
                this.create(/** @type {any} */ ([values]), kwargs)
            );
        } else {
            this.write(ids, values);
        }
        if (nextId) {
            ids = /** @type {number[]} */ (ensureArray(nextId));
        }
        return this.web_read(ids, specification);
    }

    /**
     * @param {number[]} ids
     * @param {Record<string, any>} vals
     * @param {Record<string, any>} knownValues
     */
    _checkConcurrentFieldChanges(ids, vals, knownValues) {
        const SAFE_TYPES = new Set([
            "integer",
            "boolean",
            "char",
            "text",
            "selection",
            "float",
            "monetary",
            "many2one",
        ]);
        const coerce = (type, value) => {
            if (value === null || value === undefined || value === false) {
                return (
                    { integer: 0, float: 0, monetary: 0, boolean: false }[type] ?? ""
                );
            }
            if (type === "many2one") {
                if (Array.isArray(value)) {
                    return value[0] ?? false;
                }
                if (value && typeof value === "object") {
                    return value.id ?? false;
                }
                return typeof value === "number" ? value : false;
            }
            if (type === "integer") {
                return Math.trunc(Number(value));
            }
            if (type === "float" || type === "monetary") {
                return Math.round(Number(value) * 1e6) / 1e6;
            }
            if (type === "boolean") {
                return Boolean(value);
            }
            return String(value);
        };
        const baselinesById =
            ids.length === 1 ? { [ids[0]]: knownValues } : knownValues;
        for (const id of ids) {
            const baseline = baselinesById[id] ?? baselinesById[String(id)];
            if (!baseline) {
                continue;
            }
            const record = this.find((r) => r.id === id);
            if (!record) {
                continue;
            }
            for (const fieldName of Object.keys(baseline)) {
                const field = this._fields[fieldName];
                if (!field || !SAFE_TYPES.has(field.type) || !(fieldName in vals)) {
                    continue;
                }
                let conflicts;
                try {
                    const current = coerce(field.type, record[fieldName]);
                    const base = coerce(field.type, baseline[fieldName]);
                    const next = coerce(field.type, vals[fieldName]);
                    conflicts = current !== base && current !== next;
                } catch {
                    conflicts = false;
                }
                if (conflicts) {
                    throw makeServerError({
                        type: "UserError",
                        message:
                            "This record was modified by another user while " +
                            "you were editing it.",
                    });
                }
            }
        }
    }

    /**
     * @param {number[]} ids
     * @param {Partial<ModelRecord>[]} values
     * @param {Record<string, any>} specification
     * @param {Record<string, any>} [knownValues]
     * @returns {any[]}
     */
    web_save_multi(ids, values, specification, knownValues) {
        const kwargs = getKwArgs(
            arguments,
            "ids",
            "values",
            "specification",
            "known_values",
        );
        ({ ids, values, specification, known_values: knownValues } = kwargs);

        if (
            !Array.isArray(ids) ||
            !Array.isArray(values) ||
            ids.length !== values.length
        ) {
            throw new Error(
                "web_save_multi requires `ids` and `values` of the same length.",
            );
        }

        const results = [];

        for (let i = 0; i < ids.length; i++) {
            const id = ids[i];
            const val = values[i];
            const baseline = knownValues
                ? (knownValues[id] ?? knownValues[String(id)])
                : undefined;
            const res = this.web_save([id], val, specification, undefined, baseline);
            if (Array.isArray(res)) {
                results.push(...res);
            } else {
                results.push(res);
            }
        }

        return results;
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
            "count_limit",
        );
        ({
            domain,
            specification,
            offset,
            limit,
            order,
            count_limit: countLimit,
        } = kwargs);

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
                unique(["id", ...fieldNames]),
            ),
        };
        if (countLimit) {
            result.length = Math.min(result.length, countLimit);
        }
        this._unityReadRecords(result.records, specification);
        return result;
    }

    /** @param {unknown} user */
    with_user(user) {
        return this;
    }

    /**
     * @param {MaybeIterable<number | false>} idOrIds
     * @param {Partial<ModelRecord>} values
     */
    write(idOrIds, values) {
        const kwargs = getKwArgs(arguments, "ids", "vals");
        ({ ids: idOrIds, vals: values } = kwargs);

        const ids = ensureArray(idOrIds);
        const originalRecords = {};
        for (const id of ids) {
            originalRecords[id] = { ...this.browse(id)[0] };
            this._write(/** @type {any} */ (values), /** @type {number} */ (id));
        }
        this.browse(ids)._applyComputesAndValidate(originalRecords);
        return true;
    }

    /**
     * @protected
     * @param {Record<string, ModelRecord>} [originalRecords={}]
     */
    _applyComputesAndValidate(originalRecords = {}) {
        for (const record of this) {
            updateComodelRelationalFields(
                this,
                record,
                originalRecords[/** @type {number} */ (record.id)],
            );
        }

        for (const fieldName of this._related) {
            this._compute_related_field(fieldName);
        }

        for (const computeFn of Object.values(this._computes)) {
            /** @type {Function} */ (computeFn).call(this);
        }

        for (const record of this) {
            for (const fieldName of Object.keys(record)) {
                const fieldDef = this._fields[fieldName];
                if (!isValidFieldValue(record, fieldDef)) {
                    throw new MockServerError(
                        `Invalid value for field "${fieldName}" on ${getRecordQualifier(
                            record,
                        )} in model "${this._name}": expected "${fieldDef.type}" and got: ${
                            record[fieldName]
                        }`,
                    );
                }
            }
        }
    }

    /**
     * @private
     * @param {ModelRecord} record
     * @param {Context} [context]
     */
    _applyDefaults(record, context) {
        for (const fieldName in this._fields) {
            if (fieldName === "id" || record[fieldName] !== undefined) {
                continue;
            }
            if (fieldName === "active") {
                record[fieldName] = true;
                continue;
            }
            if (fieldName === "create_uid") {
                if ("res.users" in /** @type {any} */ (MockServer.current)._models) {
                    record[fieldName] = this.env.uid;
                }
                continue;
            }
            const fieldDef = this._fields[fieldName];
            if (context && `default_${fieldName}` in context) {
                record[fieldName] = context[`default_${fieldName}`];
            } else if ("default" in fieldDef) {
                record[fieldName] =
                    typeof fieldDef.default === "function"
                        ? fieldDef.default.call(this, record)
                        : fieldDef.default;
            } else if (fieldDef.type in DEFAULT_FIELD_VALUES) {
                record[fieldName] = DEFAULT_FIELD_VALUES[fieldDef.type]();
            }
        }
    }

    _compute_display_name() {
        if (this._rec_name) {
            for (const record of this) {
                const value = record[this._rec_name];
                record.display_name = /** @type {any} */ (
                    value ? String(value) : false
                );
            }
        } else {
            for (const record of this) {
                record.display_name = `${this._name},${record.id}`;
            }
        }
    }

    /**
     * @private
     * @param {string} fieldName
     */
    _compute_related_field(fieldName) {
        const field = this._fields[fieldName];
        const fieldNames = safeSplit(field.related, ".");
        for (const record of this) {
            const [value, field] = this._followRelation(record, fieldNames);
            if (!field) {
                this.env[this._name]._related.delete(fieldName);
                return;
            }
            if (value === undefined) {
                record[fieldName] ??= DEFAULT_FIELD_VALUES[field.type]();
            } else {
                record[fieldName] = value;
            }
        }
    }

    /**
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
            const [[fieldName, operator, value]] = domain;
            let simpleFilter;
            switch (typeof fieldName) {
                case "boolean":
                case "number": {
                    let shouldBeIncluded;
                    if (domain[0].length === 1) {
                        shouldBeIncluded = Boolean(fieldName);
                    } else {
                        shouldBeIncluded = fieldName === value;
                        if (operator === "!=") {
                            shouldBeIncluded = !shouldBeIncluded;
                        }
                    }
                    if (activeTest) {
                        simpleFilter = () => shouldBeIncluded;
                    } else {
                        return shouldBeIncluded
                            ? this
                            : new /** @type {any} */ (this.constructor)();
                    }
                    break;
                }
                case "string": {
                    if (fieldName === "id" && ["in", "="].includes(operator)) {
                        const values = ensureArray(value);
                        simpleFilter = (record) => values.includes(record[fieldName]);
                    }
                    break;
                }
            }
            if (simpleFilter) {
                return this.filter(
                    (record) => simpleFilter(record) && (!activeTest || record.active),
                );
            }
        }
        if (activeTest) {
            const activeInDomain = domain.some(
                (subDomain) => subDomain[0] === "active",
            );
            if (!activeInDomain) {
                domain = [...domain, ["active", "=", true]];
            }
        }
        if (!domain.length) {
            return this;
        }
        domain = domain.map((criterion) => {
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
            const field = this._fields[criterion[0]] || {};
            if (isX2MField(field) && criterion[1] === "=") {
                if (criterion[2] === false) {
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
     * @private
     * @param {ModelRecord} record
     * @param {string[]} fieldNames
     * @returns {[any, any]}
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
            value = currentRecord?.[fieldName];
            const relation = getRelation(currentField, currentRecord);
            if (relation) {
                const ids = ensureArray(currentRecord?.[fieldName]);
                currentModel = relation;
                currentRecord = currentModel.find((r) => ids.includes(r.id));
            }
        }

        return [value, currentField];
    }

    /** @private */
    _getNextId() {
        return Math.max(0, ...this.map((record) => record?.id || 0)) + 1;
    }

    /**
     * @private
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
     * @param {MaybeIterable<number | false>} idOrIds
     * @param {Iterable<string>} [fnames=[]]
     * @param {string | false} [load="_classic_read"]
     */
    _read_format(idOrIds, fnames = [], load = "_classic_read") {
        const ids = ensureArray(idOrIds);
        const fieldNames = unique(["id", ...fnames]);

        /** @type {ModelRecord[]} */
        const records = [];
        const validFields = [];

        /** @type {Record<string, Record<number, ModelRecord>>} */
        const modelMap = {
            [this._name]: {},
        };
        for (const record of this) {
            modelMap[this._name][/** @type {number} */ (record.id)] = record;
        }
        for (const fieldName of fieldNames) {
            const field = this._fields[fieldName];
            if (field) {
                validFields.push(field);
            } else {
                continue;
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

        for (const id of ids) {
            if (!id) {
                throw new MockServerError(
                    `Cannot read: falsy ID value would result in an access error on the actual server`,
                );
            }
            const record = modelMap[this._name][id];
            if (!record) {
                continue;
            }
            /** @type {Record<string, any>} */
            const result = { id: record.id };
            for (const field of validFields) {
                if (["float", "integer", "monetary"].includes(field.type)) {
                    result[field.name] = record[field.name] || 0;
                } else if (isM2OField(field)) {
                    const coModel = getRelation(field, record);
                    const relRecord =
                        coModel && modelMap[coModel._name][record[field.name]];
                    if (relRecord) {
                        if (
                            field.type === "many2one_reference" ||
                            load !== "_classic_read"
                        ) {
                            result[field.name] = record[field.name];
                        } else {
                            result[field.name] = [
                                record[field.name],
                                relRecord.display_name,
                            ];
                        }
                    } else {
                        result[field.name] = false;
                    }
                } else if (isX2MField(field)) {
                    result[field.name] = record[field.name] || [];
                } else if (field.type === "properties") {
                    const container = this._getPropertyContainer(field, record);
                    if (container) {
                        result[field.name] = container[
                            field.definition_record_field
                        ].map((/** @type {any} */ def) => ({
                            ...def,
                            value: record[field.name][def.name],
                        }));
                    } else {
                        result[field.name] = false;
                    }
                } else {
                    result[field.name] = record[field.name] ?? false;
                }
            }
            records.push(/** @type {any} */ (result));
        }

        return records;
    }

    /**
     * @private
     * @param {SearchParams} params
     */
    _search(params) {
        const offset = params.offset || 0;
        const records = this._filter(params.domain, {
            active_test: params.context?.active_test,
        });
        const ordered = orderByField(records, params.order);
        const endLimit = params.limit ? offset + params.limit : undefined;
        return {
            length: ordered.length,
            records: ordered.slice(offset, endLimit),
        };
    }

    /**
     * @private
     * @param {Record<string, any>} spec
     * @param {ModelRecord[]} records
     */
    _unityReadRecords(records, spec) {
        for (const fieldName in spec) {
            const field = this._fields[fieldName];
            if (!field) {
                throw new Error(
                    `MockServer: model "${this._name}" has no field ` +
                        `"${fieldName}" referenced in a web_read specification`,
                );
            }
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
                                makeKwArgs({ context: spec[fieldName].context }),
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
                        const dbRecord = this.find((r) => r.id === record.id);
                        const model = dbRecord[field.model_field];
                        record[fieldName] = {};
                        if (relatedFields && Object.keys(relatedFields).length) {
                            const [result] = this.env[model].web_read(
                                id,
                                relatedFields,
                                makeKwArgs({ context: spec[fieldName].context }),
                            );
                            record[fieldName] = result;
                        }
                    }
                    break;
                }
                case "many2many":
                case "one2many": {
                    if (relatedFields && Object.keys(relatedFields).length) {
                        const { limit, order } = spec[fieldName];
                        const relModel = getRelation(field);
                        for (const record of records) {
                            /** @type {number[]} */
                            let relResIds = record[fieldName];
                            if (order) {
                                const relRecords = relModel.read(relResIds);
                                const orderedRelRecords = orderByField(
                                    relModel,
                                    order,
                                    relRecords,
                                );
                                relResIds = /** @type {number[]} */ (
                                    orderedRelRecords.map((r) => r.id)
                                );
                            }
                            let result = relModel.web_read(
                                relResIds,
                                relatedFields,
                                makeKwArgs({ context: spec[fieldName].context }),
                            );
                            if (limit) {
                                result = result.map((r, i) =>
                                    i < limit ? r : { id: r.id },
                                );
                            }
                            record[fieldName] = result;
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
                                    makeKwArgs({ context: spec[fieldName].context }),
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
     * @private
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
                    `could not write on ${getRecordQualifier(record)}`,
                );
            }
            if (isX2MField(field)) {
                let ids = record[fieldName] ? record[fieldName].slice() : [];
                if (Array.isArray(value) && value.length) {
                    if (
                        value.reduce(
                            (hasOnlyInt, val) => hasOnlyInt && Number.isInteger(val),
                            true,
                        )
                    ) {
                        value = [[6, 0, value]];
                    }
                } else if (value === false) {
                    value = [[5, false, false]];
                }
                for (const command of value || []) {
                    const coModel = getRelation(field, record);
                    if (command[0] === 0) {
                        const inverseData = command[2];
                        const inverseFieldName =
                            field.inverse_fname_by_model_name?.[coModel._name];
                        if (inverseFieldName) {
                            inverseData[inverseFieldName] =
                                field.type === "many2many" ? [id] : id;
                        }
                        const [newId] = coModel.create([inverseData]);
                        ids.push(newId);
                    } else if (command[0] === 1) {
                        coModel.write([command[1]], command[2]);
                    } else if (command[0] === 2 || command[0] === 3) {
                        const index = ids.indexOf(command[1]);
                        if (index >= 0) {
                            ids.splice(index, 1);
                        }
                        if (command[0] === 2) {
                            coModel.unlink([command[1]]);
                        }
                    } else if (command[0] === 4) {
                        if (!ids.includes(command[1])) {
                            ids.push(command[1]);
                        }
                    } else if (command[0] === 5) {
                        ids = [];
                    } else if (command[0] === 6) {
                        ids = [...command[2]];
                    } else {
                        throw new MockServerError(
                            `Command "${JSON.stringify(
                                value,
                            )}" is not supported by the MockServer on field "${fieldName}" in model "${
                                this._name
                            }"`,
                        );
                    }
                }
                record[fieldName] = ids;
            } else if (isM2OField(field)) {
                if (value) {
                    if (!isValidId(value, field, record)) {
                        if (todoValsMap.has(field.model_name_ref_fname)) {
                            todoValsMap.set(fieldName, value);
                            continue;
                        }
                        throw new MockServerError(
                            `Invalid ID "${JSON.stringify(
                                value,
                            )}" for a many2one on field "${fieldName}" in model "${this._name}"`,
                        );
                    }
                    record[fieldName] = value;
                } else {
                    record[fieldName] = false;
                }
            } else if (field.type === "properties") {
                const properties = value || [];
                if (
                    properties.some((p) => p.definition_changed || p.definition_deleted)
                ) {
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

                record[fieldName] ||= {};
                for (const property of properties) {
                    if (property.definition_deleted) {
                        delete record[fieldName][property.name];
                    } else {
                        let value = property.value ?? property.default;
                        if (value && property.comodel) {
                            const coModel = this.env[property.comodel];
                            switch (property.type) {
                                case "one2many":
                                case "many2many": {
                                    value = coModel.browse(value).map(toIdDisplayName);
                                    break;
                                }
                                case "many2one": {
                                    value = toIdDisplayName(
                                        coModel.browse(value[0])[0],
                                    );
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

    /**
     * @param {string} fieldPath
     * @param {any} value
     * @param {ReadGroupNumberGranularity} [numberGranularity]
     * @returns {DomainListRepr}
     * @private
     */
    _readGroupExtraDomain(fieldPath, value, numberGranularity) {
        const [fieldName, ...remainingPath] = fieldPath.split(".");
        if (remainingPath.length) {
            const relation = getRelation(this._fields[fieldName]);
            const subDomain = relation._readGroupExtraDomain(
                remainingPath.join("."),
                value,
                numberGranularity,
            );
            return value
                ? [[fieldName, "any", subDomain]]
                : ["|", [fieldName, "not any", []], [fieldName, "any", subDomain]];
        } else if (numberGranularity) {
            return [[`${fieldName}.${numberGranularity}`, "=", value]];
        } else {
            return [[fieldName, "=", value]];
        }
    }

    /**
     * @param {string} fieldPath
     * @param {string} from
     * @param {string} to
     * @returns {DomainListRepr}
     * @private
     */
    _readGroupDateRangeExtraDomain(fieldPath, from, to) {
        const [fieldName, ...remainingPath] = fieldPath.split(".");
        if (remainingPath.length) {
            const relation = getRelation(this._fields[fieldName]);
            const subDomain = relation._readGroupDateRangeExtraDomain(
                remainingPath.join("."),
                from,
                to,
            );
            return [[fieldName, "any", subDomain]];
        } else {
            return [
                [fieldName, ">=", from],
                [fieldName, "<", to],
            ];
        }
    }
}

export class ServerModel extends Model {
    static _fetch = true;
}

export const Command = {
    clear: () => [5, false, false],
    /** @param {Partial<ModelRecord>} values */
    create: (values) => [0, 0, values],
    /** @param {number} id */
    delete: (id) => [2, id, false],
    /** @param {number} id */
    link: (id) => [4, id, false],
    /** @param {number[]} ids */
    set: (ids) => [6, false, ids],
    /** @param {number} id */
    unlink: (id) => [3, id, false],
    /**
     * @param {number} id
     * @param {Partial<ModelRecord>} values
     */
    update: (id, values) => [1, id, values],
};
