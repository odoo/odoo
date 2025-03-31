import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";

/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

export const modelRegistry = registry.category("discuss.model");

/**
 * Class of markup, useful to detect content that is markup and to
 * automatically markup field during trusted insert
 */
export const Markup = markup("").constructor;

export const FIELD_DEFINITION_SYM = Symbol("field_definition");
/** @typedef {ATTR_SYM|MANY_SYM|ONE_SYM} FIELD_SYM */
export const ATTR_SYM = Symbol("attr");
export const MANY_SYM = Symbol("many");
export const ONE_SYM = Symbol("one");
export const OR_SYM = Symbol("or");
const AND_SYM = Symbol("and");
export const IS_RECORD_SYM = Symbol("isRecord");
export const IS_FIELD_SYM = Symbol("isField");
export const IS_DELETING_SYM = Symbol("isDeleting");
export const IS_DELETED_SYM = Symbol("isDeleted");
export const STORE_SYM = Symbol("store");

export function AND(...args) {
    return [AND_SYM, ...args];
}
export function OR(...args) {
    return [OR_SYM, ...args];
}

export function isCommand(data) {
    return ["ADD", "DELETE", "ADD.noinv", "DELETE.noinv"].includes(data?.[0]?.[0]);
}
/**
 * @param {typeof import("./record").Record} Model
 * @param {string} fieldName
 */
export function isOne(Model, fieldName) {
    return Model._.fieldsOne.get(fieldName);
}
/**
 * @param {typeof import("./record").Record} Model
 * @param {string} fieldName
 */
export function isMany(Model, fieldName) {
    return Model._.fieldsMany.get(fieldName);
}
/** @param {Record} record */
export function isRecord(record) {
    return Boolean(record?._?.[IS_RECORD_SYM]);
}
/**
 * @param {typeof import("./record").Record} Model
 * @param {string} fieldName
 */
export function isRelation(Model, fieldName) {
    return isMany(Model, fieldName) || isOne(Model, fieldName);
}
export function isFieldDefinition(val) {
    return val?.[FIELD_DEFINITION_SYM];
}
