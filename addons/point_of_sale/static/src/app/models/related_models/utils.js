import {
    deserializeDateTime,
    serializeDateTime,
    deserializeDate,
    serializeDate,
} from "@web/core/l10n/dates";
export const RELATION_TYPES = new Set(["many2many", "many2one", "one2many"]);
export const DATE_TIME_TYPE = new Set(["date", "datetime"]);
export const X2MANY_TYPES = new Set(["many2many", "one2many"]);
export const PARENT_X2MANY_TYPES = new Set(["many2one", "many2many"]);
export const RAW_SYMBOL = Symbol("raw");
export const STORE_SYMBOL = Symbol("store");
export const SERIALIZED_UI_STATE_PROP = "JSONuiState";
export const BACKREF_PREFIX = "<-";

export function getBackRef(model, fieldName) {
    return `${BACKREF_PREFIX}${model}.${fieldName}`;
}
export function clone(obj) {
    return JSON.parse(
        JSON.stringify(obj, (_, value) => (value instanceof Set ? [...value] : value))
    );
}

/**
 * Returns a new object with the same keys, but with values transformed by the provided function.
 *
 * @param {Object} obj - The input object whose values will be transformed.
 * @param {Function} fn - A function that takes (key, value, index) and returns a new value.
 * @returns {Object} A new object with the same keys but transformed values.
 *
 * @example
 * const obj = { a: 1, b: 2, c: 3 };
 * const doubled = mapObj(obj, (key, value) => value * 2);
 * console.log(doubled); // { a: 2, b: 4, c: 6 }
 */
export function mapObj(obj, fn) {
    return Object.fromEntries(Object.entries(obj).map(([k, v], i) => [k, fn(k, v, i)]));
}

export function convertRawToDateTime(model, value, prop) {
    if (!value) {
        return undefined;
    }
    const datetime = deserializeDateTime(value);
    if (!datetime.isValid) {
        throw new Error(`Invalid date: ${value} for model ${model.model} in field ${prop}`);
    }
    return datetime;
}

export function convertDateTimeToRaw(value) {
    if (!value) {
        return undefined;
    }
    // Verify if is already a valid date object
    if (typeof value !== "string") {
        return serializeDateTime(value);
    }
    return value;
}

export function convertRawToDate(model, value, prop) {
    if (!value) {
        return undefined;
    }
    const date = deserializeDate(value);
    if (!date.isValid) {
        throw new Error(`Invalid date: ${value} for model ${model.model} in field ${prop}`);
    }
    return date;
}

export function convertDateToRaw(value) {
    if (!value) {
        return undefined;
    }
    // Verify if is already a valid date object
    if (typeof value !== "string") {
        return serializeDate(value);
    }
    return value;
}

/**
 * Creates a deep immutable proxy for the given object or array.
 * Any attempts to modify, delete, or redefine properties will throw an error.
 *
 * Note: This function only supports plain objects and arrays.
 * It does NOT support Map, Set, or other complex data structures.
 *
 * @param {Object|Array} obj - The object or array to make immutable.
 * @param {string} errorMsg - The error message to throw on modification attempts.
 * @returns {Proxy} A Proxy that enforces deep immutability.
 */
export function deepImmutable(obj, errorMsg) {
    return new Proxy(obj, {
        get(target, prop, receiver) {
            if ("__deepImmutable" === prop) {
                return true;
            }
            const value = Reflect.get(target, prop, receiver);
            return value && typeof value === "object" ? deepImmutable(value, errorMsg) : value;
        },
        set() {
            throw new Error(errorMsg);
        },
        deleteProperty() {
            throw new Error(errorMsg);
        },
        defineProperty() {
            throw new Error(errorMsg);
        },
    });
}

export class AggregatedUpdates {
    constructor() {
        this.updates = new Map();
    }

    /**
     * Adds a field update for the given record.
     * @param {Object} record - The record
     * @param {string} fieldName - The name of the field that was updated.
     */
    add(record, fieldName) {
        if (!this.updates.has(record)) {
            this.updates.set(record, new Set());
        }
        this.updates.get(record).add(fieldName);
    }

    /**
     * Iterates over all updated records, fires the update event (unless silenced), and marks the records as dirty.
     *
     * @param {Object} opts - Options for controlling the update behavior.
     * @param {string[]} [opts.silentModels=[]] - List of model names to exclude from triggering update events.
     */
    fireEventAndDirty(opts = {}) {
        const { silentModels = [] } = opts;
        for (const [record, fields] of this.updates) {
            if (!silentModels.includes(record.model.name)) {
                record.model.triggerEvents("update", { id: record.id, fields: [...fields] });
            }
            record._markDirty();
        }
    }

    /**
     *  Remove record updated
     */
    remove(record) {
        this.updates.delete(record);
    }
}
