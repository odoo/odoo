import { markup, toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

/**
 * Class of markup, useful to detect content that is markup and to
 * automatically markup field during trusted insert
 */
export const Markup = markup("").constructor;

/** @typedef {ATTR_SYM|MANY_SYM|ONE_SYM} FIELD_SYM */
export const ATTR_SYM = Symbol("attr");
export const MANY_SYM = Symbol("many");
export const ONE_SYM = Symbol("one");
export const OR_SYM = Symbol("or");
export const RECORD_SYM = Symbol("Record");
export const FIELD_DEFINITION_SYM = Symbol("FieldDefinition");
export const RECORD_FIELD_SYM = Symbol("RecordField");
export const STORE_SYM = Symbol("Store");
export const RECORD_DELETED_SYM = Symbol("RecordDeleted");

/**
 * @template T
 * @param {T} obj
 * @returns {T}
 */
export function _0(obj) {
    const raw = toRaw(obj);
    if (!raw) {
        return raw;
    }
    return raw._0 ?? raw;
}

export function OR(...args) {
    return [OR_SYM, ...args];
}

/** @param {FieldDefinition} */
export function isAttr(definition) {
    return Boolean(definition?.[ATTR_SYM]);
}

export function isCommand(data) {
    return ["ADD", "DELETE", "ADD.noinv", "DELETE.noinv"].includes(data?.[0]?.[0]);
}

export function isRecord(record) {
    return Boolean(record?.[RECORD_SYM]);
}

/**
 * @param {typeof import("./record").Record} Model
 * @param {string} fieldName
 */
export function isRelation(Model, fieldName) {
    return Model._.fieldsMany.get(fieldName) || Model._.fieldsOne.get(fieldName);
}
