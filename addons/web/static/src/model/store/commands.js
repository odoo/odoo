import { CHANGES, FLAGS, ID, MODEL, NEW, VALUES } from "./model";
import { peek } from "./store";

export const CREATE = 0;
export const UPDATE = 1;
export const DELETE = 2;
export const UNLINK = 3;
export const LINK = 4;

/**
 * @typedef {import("./model").Model} Model
 * @typedef {import("./fields").StoreField} StoreField
 */

/**
 * Builds the values to send to the server for a record of a store: its changed
 * fields, with x2many changes as commands computed from the difference between
 * the last server list and the current one. Nothing is logged while editing.
 *
 * One2many children are nested: new ones as CREATE, changed ones as UPDATE,
 * removed ones as DELETE. Many2many changes are LINK and UNLINK.
 *
 * `version` is the latest change included: pass it to `store.ack` once the
 * server confirmed the save, so that edits made in the meantime stay dirty.
 *
 * @param {Model} record
 * @returns {{ vals: Record<string, any>; version: number }}
 */
export function toCommands(record) {
    let version = 0;

    /**
     * @param {Model} rec
     * @param {StoreField | null} skipField the inverse many2one of the parent list
     */
    const serialize = (rec, skipField) => {
        const model = rec[MODEL];
        /** @type {Record<string, any>} */
        const vals = {};
        for (const [index, change] of rec[CHANGES] || []) {
            version = Math.max(version, change.version);
            const field = model.fields[index];
            if (field !== skipField && field.type !== "one2many") {
                vals[field.name] = serializeValue(rec, field, change.value);
            }
        }
        for (const field of model.fields) {
            if (field.type === "one2many") {
                const commands = one2manyCommands(rec, field, serialize);
                if (commands.length) {
                    vals[field.name] = commands;
                }
            }
        }
        return vals;
    };

    return { vals: serialize(record, null), version };
}

/**
 * @param {Model} rec
 * @param {StoreField} field
 * @param {(rec: Model, skipField: StoreField | null) => Record<string, any>} serialize
 */
function one2manyCommands(rec, field, serialize) {
    const current = peek(rec, field);
    if (!current) {
        return [];
    }
    const base = rec[VALUES][field.index] || [];
    const commands = [];
    for (const child of current) {
        const childVals = serialize(child, field.inverseField);
        if (child[FLAGS] & NEW) {
            commands.push([CREATE, child[ID], childVals]);
            continue;
        }
        if (!base.includes(child)) {
            commands.push([LINK, child[ID]]);
        }
        if (Object.keys(childVals).length) {
            commands.push([UPDATE, child[ID], childVals]);
        }
    }
    for (const child of base) {
        if (!current.includes(child)) {
            commands.push([DELETE, child[ID]]);
        }
    }
    return commands;
}

/**
 * @param {Model} rec
 * @param {StoreField} field
 * @param {any} value
 */
function serializeValue(rec, field, value) {
    switch (field.type) {
        case "many2one":
            return value ? value[ID] : false;
        case "many2many": {
            const base = rec[VALUES][field.index] || [];
            return [
                ...base.filter((r) => !value.includes(r)).map((r) => [UNLINK, r[ID]]),
                ...value.filter((r) => !base.includes(r)).map((r) => [LINK, r[ID]]),
            ];
        }
        default:
            return value ?? false;
    }
}
