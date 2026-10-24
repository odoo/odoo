/**
 * Field declarations for store models.
 *
 * A field factory returns a plain descriptor tagged with {@link FIELD}. It is
 * typed as returning the field's *value* type, so that a class field such as
 * `name = fields.Char()` is typed as a string on records, while the store reads
 * the descriptor once at setup time (records never run class field
 * initializers).
 */

export const FIELD = Symbol("field");

/**
 * @typedef {"char" | "text" | "html" | "integer" | "float" | "monetary" | "boolean"
 *  | "date" | "datetime" | "selection" | "json" | "many2one" | "one2many"
 *  | "many2many"} StoreFieldType
 *
 * @typedef {{
 *  string?: string;
 *  required?: boolean;
 *  readonly?: boolean;
 *  default?: any;
 * }} FieldOptions
 *
 * @typedef {FieldOptions & { inverse?: string }} RelationalFieldOptions
 *
 * @typedef {{
 *  name: string;
 *  index: number;
 *  type: StoreFieldType;
 *  relation: string | null;
 *  inverse: string | null;
 *  string: string;
 *  required: boolean;
 *  readonly: boolean;
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
        string: def.string || name,
        required: Boolean(def.required),
        readonly: Boolean(def.readonly),
        default: def.default,
        comodel: null,
        inverseField: null,
        indexed: false,
    };
}

export const fields = {
    /**
     * @param {FieldOptions} [options]
     * @returns {string | false}
     */
    Char: (options) => declare("char", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {string | false}
     */
    Text: (options) => declare("text", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {string | false}
     */
    Html: (options) => declare("html", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {number}
     */
    Integer: (options) => declare("integer", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {number}
     */
    Float: (options) => declare("float", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {number}
     */
    Monetary: (options) => declare("monetary", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {boolean}
     */
    Boolean: (options) => declare("boolean", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {string | false}
     */
    Date: (options) => declare("date", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {string | false}
     */
    Datetime: (options) => declare("datetime", options),
    /**
     * @param {FieldOptions & { selection?: [string, string][] }} [options]
     * @returns {string | false}
     */
    Selection: (options) => declare("selection", options),
    /**
     * @param {FieldOptions} [options]
     * @returns {any}
     */
    Json: (options) => declare("json", options),
    /**
     * @param {string} relation
     * @param {RelationalFieldOptions} [options]
     * @returns {import("./model").Model | null}
     */
    Many2one: (relation, options) => declare("many2one", { relation, ...options }),
    /**
     * @param {string} relation
     * @param {RelationalFieldOptions} [options]
     * @returns {import("./model").Model[]}
     */
    One2many: (relation, options) => declare("one2many", { relation, ...options }),
    /**
     * @param {string} relation
     * @param {RelationalFieldOptions} [options]
     * @returns {import("./model").Model[]}
     */
    Many2many: (relation, options) => declare("many2many", { relation, ...options }),
};
