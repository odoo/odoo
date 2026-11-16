/**
 * Field declarations for store models, given to `Model.extend({ fields })`.
 *
 * A field factory returns a plain descriptor tagged with {@link FIELD}. It is
 * typed as the field signal records expose, so that `name: fields.Char()`
 * types `record.name` as `FieldSignal<string | false>`.
 *
 * Relational factories are typed `any`: cast them to the field signal of the
 * comodel class, see the example below. A typed return value would make two
 * models that reference each other circular for TypeScript. Nothing checks
 * that the class matches the model name, and a relation without cast is `any`.
 */

// Declaring a relation, with its type:
//
//     /** @import { Many2one } from "@web/next/model/fields" */
//     /** @import { Partner } from "./partner" */
//
//     fields: {
//         partner_id: /** @type {Many2one<Partner>} */ (fields.Many2one("res.partner")),
//     }
//
// The `@import` is type-only (erased), so two models can reference each other
// without creating an import cycle.

export const FIELD = Symbol("field");

/**
 * What a record exposes for each field: call it to read (tracked), `set` to
 * write (a local write).
 *
 * @template T read value
 * @template [W=T] accepted value on write
 * @typedef {{ (): T; set(value: W): void }} FieldSignal
 */

/**
 * What a relational field accepts for one record: a record, an id, or values
 * (values with an `id` point to an existing record).
 *
 * @template M
 * @typedef {M | number | string | RecordValues<M>} RecordInput
 */

/**
 * Values of a record, as given to `create`, `update` and relational writes:
 * field names to what their `set` accepts. Any object for `Model` itself (a
 * record of unknown class).
 *
 * `setup?: never` keeps records out: without it, a record of another model
 * would match as soon as it shares a field name (at least `id`).
 *
 * @template M
 * @typedef {import("./model").Model extends M
 *  ? Record<string, any>
 *  : { id?: number | string; setup?: never } & {
 *      [K in keyof M as M[K] extends FieldSignal<any, any> ? K : never]?:
 *          M[K] extends FieldSignal<any, infer W> ? W : never;
 *  }} RecordValues
 */

// The relational signals are spelled out, not written as `FieldSignal<...>`:
// as type arguments, the accepted values would be computed from the comodel
// class right away, which is circular when two models reference each other.

/**
 * @template M
 * @typedef {{ (): M | null; set(value: RecordInput<M> | false | null): void }} Many2one
 */

/**
 * @template M
 * @typedef {{ (): M[]; set(value: RecordInput<M>[]): void }} One2many
 */

/**
 * @template M
 * @typedef {{ (): M[]; set(value: RecordInput<M>[]): void }} Many2many
 */

/**
 * @typedef {"char" | "text" | "html" | "integer" | "float" | "monetary" | "boolean"
 *  | "date" | "datetime" | "selection" | "json" | "many2one" | "one2many"
 *  | "many2many"} StoreFieldType
 *
 * @typedef {{ default?: any }} FieldOptions
 *
 * @typedef {FieldOptions & { inverse?: string }} RelationalFieldOptions
 */

/**
 * What the store keeps of a field: its name, and for a relation its comodel
 * and inverse. Labels, `required`, `readonly` and the like are not needed to
 * hold records: views read them from the description they already have.
 *
 * @typedef {{
 *  name: string;
 *  index: number;
 *  type: StoreFieldType;
 *  relation: string | null;
 *  inverse: string | null;
 *  default: any;
 *  comodel: import("./store").ModelMeta | null;
 *  inverseField: StoreField | null;
 *  indexed: boolean;
 * }} StoreField
 */

const RELATIONAL_TYPES = new Set(["many2one", "one2many", "many2many"]);

/**
 * @param {{ type: string }} field
 */
export function isRelational(field) {
    return RELATIONAL_TYPES.has(field.type);
}

/**
 * @param {{ type: string }} field
 */
export function isX2Many(field) {
    return field.type === "one2many" || field.type === "many2many";
}

/**
 * @param {StoreFieldType} type
 * @param {object} [options]
 * @returns {any} each factory types it
 */
function declare(type, options = {}) {
    return { [FIELD]: true, type, ...options };
}

/**
 * Turns a field definition, either declared in JS or received from the
 * server (`/web/model/get_definitions` or `fields_get`), into a store field.
 *
 * @param {string} name
 * @param {Record<string, any>} def
 * @param {number} index
 * @returns {StoreField}
 */
export function normalizeField(name, def, index) {
    const relation = def.relation || null;
    const inverse =
        def.inverse ||
        (relation && def.inverse_fname_by_model_name?.[relation]) ||
        def.relation_field ||
        null;
    return {
        name,
        index,
        type: def.type,
        relation,
        inverse,
        default: def.default,
        comodel: null,
        inverseField: null,
        indexed: false,
    };
}

export const fields = {
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<string | false>}
     */
    Char: (options) => declare("char", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<string | false>}
     */
    Text: (options) => declare("text", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<string | false>}
     */
    Html: (options) => declare("html", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<number>}
     */
    Integer: (options) => declare("integer", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<number>}
     */
    Float: (options) => declare("float", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<number>}
     */
    Monetary: (options) => declare("monetary", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<boolean>}
     */
    Boolean: (options) => declare("boolean", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<string | false>}
     */
    Date: (options) => declare("date", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<string | false>}
     */
    Datetime: (options) => declare("datetime", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<string | false>}
     */
    Selection: (options) => declare("selection", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {FieldSignal<any>}
     */
    Json: (options) => declare("json", options),
    /**
     * @param {string} relation name of the comodel
     * @param {RelationalFieldOptions} [options]
     * @returns {any} annotate it with `Many2one<ComodelClass>`
     */
    Many2one: (relation, options) => declare("many2one", { relation, ...options }),
    /**
     * @param {string} relation name of the comodel
     * @param {RelationalFieldOptions} [options]
     * @returns {any} annotate it with `One2many<ComodelClass>`
     */
    One2many: (relation, options) => declare("one2many", { relation, ...options }),
    /**
     * @param {string} relation name of the comodel
     * @param {RelationalFieldOptions} [options]
     * @returns {any} annotate it with `Many2many<ComodelClass>`
     */
    Many2many: (relation, options) => declare("many2many", { relation, ...options }),
};
