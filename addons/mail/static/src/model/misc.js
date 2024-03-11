import { markup } from "@odoo/owl";
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
const AND_SYM = Symbol("and");
export const IS_RECORD_SYM = Symbol("isRecord");
export const IS_RECORD_LIST_SYM = Symbol("isRecordList");
export const IS_FIELD_SYM = Symbol("isField");
export const IS_DELETED_SYM = Symbol("isDeleted");

export function AND(...args) {
    return [AND_SYM, ...args];
}
export function OR(...args) {
    return [OR_SYM, ...args];
}

export function isAttr(definition) {
    return Boolean(definition?.[ATTR_SYM]);
}
export function isCommand(data) {
    return ["ADD", "DELETE", "ADD.noinv", "DELETE.noinv"].includes(data?.[0]?.[0]);
}
export function isOne(list) {
    return Boolean(list?.[ONE_SYM]);
}
export function isMany(list) {
    return Boolean(list?.[MANY_SYM]);
}
export function isRecord(record) {
    return Boolean(record?.[IS_RECORD_SYM]);
}
export function isRecordList(recordList) {
    return Boolean(recordList?.[IS_RECORD_LIST_SYM]);
}
/** @param {FIELD_SYM|RecordList} val */
export function isRelation(val) {
    if ([MANY_SYM, ONE_SYM].includes(val)) {
        return true;
    }
    return isOne(val) || isMany(val);
}
/** @param {FIELD_SYM} SYM */
export function isField(SYM) {
    return [MANY_SYM, ONE_SYM, ATTR_SYM].includes(SYM);
}

/**
 * @typedef {Object} FieldDefinition
 * @property {boolean} [ATTR_SYM] true when this is an attribute, i.e. a non-relational field.
 * @property {boolean} [MANY_SYM] true when this is a many relation.
 * @property {boolean} [ONE_SYM] true when this is a one relation.
 * @property {any} [default] the default value of this attribute.
 * @property {boolean} [html] whether the attribute is an html field. Useful to automatically markup
 *   when the insert is trusted.
 * @property {string} [targetModel] model name of records contained in this relational field.
 * @property {() => any} [compute] if set the field is computed based on provided function.
 *   The `this` of function is the record, and the function is recalled whenever any field
 *   in models used by this compute function is changed. The return value is the new value of
 *   the field. On relational field, passing a (list of) record(s) or data work as expected.
 * @property {boolean} [eager=false] when field is computed, determines whether the computation
 *   of this field is eager or lazy. By default, fields are computed lazily, which means that
 *   they are computed when dependencies change AND when this field is being used. In eager mode,
 *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
 *   behaviour of OWL reactive.
 * @property {string} [inverse] name of inverse relational field in targetModel.
 * @property {(r: Record) => void} [onAdd] hook that is called when relation is updated
 *   with a record being added. Callback param is record being added into relation.
 * @property {(r: Record) => void} [onDelete] hook that is called when relation is updated
 *   with a record being deleted. Callback param is record being deleted from relation.
 * @property {() => void} [onUpdate] hook that is called when field is updated.
 * @property {(r1: Record, r2: Record) => number} [sort] if defined, this many relational field is
 *   automatically sorted by this function.
 */
/**
 * @typedef {Object} RecordField
 * @property {string} name the name of the field in the model definition
 * @property {boolean} [ATTR_SYM] true when this is an attribute, i.e. a non-relational field.
 * @property {boolean} [MANY_SYM] true when this is a many relation.
 * @property {boolean} [ONE_SYM] true when this is a one relation.
 * @property {any} [default] the default value of this attribute.
 * @property {() => void} [compute] for computed field, invoking this function (re-)computes the field.
 * @property {boolean} [computing] for computed field, determines whether the field is computing its value.
 * @property {() => void} [requestCompute] on computed field, calling this function makes a request to compute
 *   the field. This doesn't necessarily mean the field is immediately re-computed: during an update cycle, this
 *   is put in the compute FC_QUEUE and will be invoked at end.
 * @property {boolean} [computeOnNeed] on lazy-computed field, determines whether the field should be (re-)computed
 *   when it's needed (i.e. accessed). Eager computed fields are immediately re-computed at end of update cycle,
 *   whereas lazy computed fields wait extra for them being needed.
 * @property {boolean} [computeInNeed] on lazy computed-fields, determines whether this field is needed (i.e. accessed).
 * @property {() => void} [sort] for sorted field, invoking this function (re-)sorts the field.
 * @property {boolean} [sorting] for sorted field, determines whether the field is sorting its value.
 * @property {() => void} [requestSort] on sorted field, calling this function makes a request to sort
 *   the field. This doesn't necessarily mean the field is immediately re-sorted: during an update cycle, this
 *   is put in the sort FS_QUEUE and will be invoked at end.
 * @property {boolean} [sortOnNeed] on lazy-sorted field, determines whether the field should be (re-)sorted
 *   when it's needed (i.e. accessed). Eager sorted fields are immediately re-sorted at end of update cycle,
 *   whereas lazy sorted fields wait extra for them being needed.
 * @property {boolean} [sortInNeed] on lazy sorted-fields, determines whether this field is needed (i.e. accessed).
 * @property {() => void} [onUpdate] function that contains functions to be called when the value of field
 *   has changed, e.g. sort and onUpdate.
 * @property {RecordList<Record>} [value] value of the field. Either its raw value if it's an attribute,
 *   or a RecordList if it's a relational field.
 */
