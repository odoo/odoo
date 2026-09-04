import { untrack } from "@odoo/owl";

import { registry } from "@web/core/registry";

/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

export const modelRegistry = registry.category("discuss.model");

export const COMPUTED_SYM = Symbol("computed");
const FIELD_DEFINITION_SYM = Symbol("field_definition");
/** @typedef {ATTR_SYM|MANY_SYM|ONE_SYM} FIELD_SYM */
export const ATTR_SYM = Symbol("attr");
export const MANY_SYM = Symbol("many");
export const ONE_SYM = Symbol("one");
export const OR_SYM = Symbol("or");
const AND_SYM = Symbol("and");
export const IS_RECORD_SYM = Symbol("isRecord");
export const IS_FIELD_SYM = Symbol("isField");
export const STORE_SYM = Symbol("store");

export function AND(...args) {
    return [AND_SYM, ...args];
}
export function OR(...args) {
    return [OR_SYM, ...args];
}

const COMMANDS = new Set(["ADD", "DELETE", "ADD.noinv", "DELETE.noinv", "REPLACE"]);

export function isCommandList(data) {
    return Array.isArray(data) && data.length > 0 && data.every((cmd) => isCommand(cmd));
}

export function isCommand(data) {
    return COMMANDS.has(data?.[0]);
}

/**
 * Normalize a list of many commands.
 *
 * @param {Array|Object|null|false|undefined} command Many command. Can
 * either be:
 * - A falsy value or an empty array: interpreted as a "clear" command.
 * - An object: interpreted as a replace.
 * - A command.
 * - An array of commands.
 * - An array of raw values: interpreted as a replace.
 * @returns {Array<[string, any[]]>} Normalized list of `[mode, value]` arrays.
 */
export function normalizeManyCommands(command) {
    const ensureArrayValue = (cmd) => [cmd[0], Array.isArray(cmd[1]) ? cmd[1] : [cmd[1]]];
    if (!command || (Array.isArray(command) && command.length === 0)) {
        return [["REPLACE", []]];
    }
    if (isCommandList(command)) {
        return command.map(ensureArrayValue);
    }
    if (isCommand(command)) {
        return [ensureArrayValue(command)];
    }
    const replaceCmdList = ensureArrayValue(["REPLACE", command]);
    if (replaceCmdList[1].some((val) => isCommand(val))) {
        throw new Error("Many commands cannot mix raw values and commands");
    }
    return [replaceCmdList];
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

export function isComputedDefinition(val) {
    return val?.[COMPUTED_SYM];
}

export const fields = {
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Object} [param1={}]
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @returns {import("models").Models[M]}
     */
    One(targetModel, param1) {
        return { ...param1, targetModel, [FIELD_DEFINITION_SYM]: true, [ONE_SYM]: true };
    },
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Object} [param1={}]
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @returns {import("models").Models[M][]}
     */
    Many(targetModel, param1) {
        return { ...param1, targetModel, [FIELD_DEFINITION_SYM]: true, [MANY_SYM]: true };
    },
    /**
     * @template T
     * @param {T} def
     * @param {Object} [param1={}]
     * @param {boolean} [param1.asProxy=false] a read returns the value as a proxy, so that
     *   mutating its content is observed too. Only for an object, an array, a Map or a Set.
     * @param {'datetime'|'date'} [param1.type] if defined, automatically transform to a
     * specific type.
     * @returns {T}
     */
    Attr(def, param1) {
        return { ...param1, [FIELD_DEFINITION_SYM]: true, [ATTR_SYM]: true, default: def };
    },
    /**
     * HTML fields are ATTR that are automatically markup when the data being inserted is a markup.
     *
     * @param {string} def
     * @param {Object} [param1={}]
     * @returns {string|markup }
     */
    Html(def, param1) {
        const definition = {
            ...param1,
            [FIELD_DEFINITION_SYM]: true,
            [ATTR_SYM]: true,
            default: def,
        };
        definition.html = true;
        return definition;
    },
    /**
     * @param {Object} [param0={}]
     * @returns {luxon.DateTime}
     */
    Date(param0) {
        return {
            ...param0,
            [FIELD_DEFINITION_SYM]: true,
            [ATTR_SYM]: true,
            type: "date",
        };
    },
    /**
     * @param {Object} [param0={}]
     * @returns {luxon.DateTime}
     */
    Datetime(param0) {
        return {
            ...param0,
            [FIELD_DEFINITION_SYM]: true,
            [ATTR_SYM]: true,
            type: "datetime",
        };
    },
};

export function makeRecordFieldLocalId(recordLocalId, fieldName) {
    return `${recordLocalId}:${fieldName}`;
}

export const technicalKeysOnRecords = new Set(["_", "env", "Model", "Models", "recordByLocalId"]);

/**
 * Wraps the given methods so they run untracked: reactive reads inside them
 * never subscribe the caller's computation. Applied once at module load on a
 * class prototype (or the class itself for statics); the wrapper runs on the
 * call receiver. Defined non-enumerable, like the class methods it shadows.
 *
 * @param {Object} object
 * @param {string[]} names
 */
export function untrackFunctions(object, names) {
    for (const name of names) {
        const originalFn = object[name];
        Object.defineProperty(object, name, {
            configurable: true,
            enumerable: false,
            value: function untrackFunctionsValue(...args) {
                const self = this;
                return untrack(function untrackFunctionsValueUntracked() {
                    return originalFn.apply(self, args);
                });
            },
            writable: true,
        });
    }
}
