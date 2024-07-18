import { MockServerError } from "./mock_server_utils";

/**
 * @typedef {{
 *  compute?: (() => void) | string;
 *  default?: RecordFieldValue | ((record: ModelRecord) => RecordFieldValue);
 *  aggregator?: Aggregator;
 *  groupable: boolean;
 *  name: string;
 *  onChange?: (record: ModelRecord) => void;
 *  readonly: boolean;
 *  related?: string;
 *  required: boolean;
 *  searchable: boolean;
 *  sortable: boolean;
 *  store: boolean;
 *  string: string;
 * }} CommonFieldDefinition
 *
 * @typedef {ModelRecord} ModelRecord
 *
 * @typedef {MonetaryFieldDefinition
 *  | RelationalFieldDefinition
 *  | SelectionFieldDefinition
 *  | StandardFieldDefinition} FieldDefinition
 *
 * @typedef {FieldDefinition["type"]} FieldType
 *
 * @typedef {"array_agg"
 *  | "avg"
 *  | "bool_and"
 *  | "bool_or"
 *  | "count"
 *  | "count_distinct"
 *  | "max"
 *  | "min"
 *  | "sum"
 * } Aggregator
 *
 * @typedef {{
 *  __domain: string;
 *  __count: number;
 *  __range: Record<string, any>;
 *  [key: string]: any;
 * }} ModelRecordGroup
 *
 * @typedef {CommonFieldDefinition & {
 *  currency_field: string;
 *  type: keyof typeof DEFAULT_MONEY_FIELD_VALUES;
 * }} MonetaryFieldDefinition
 *
 * @typedef {number | string | boolean | number[]} RecordFieldValue
 *
 * @typedef {CommonFieldDefinition & {
 *  relation: string;
 *  relation_field?: string;
 *  type: keyof typeof DEFAULT_RELATIONAL_FIELD_VALUES;
 *  inverse_fname_by_model_name?: Record<string, string>;
 *  model_name_ref_fname: string;
 * }} RelationalFieldDefinition
 *
 * @typedef {CommonFieldDefinition & {
 *  selection: [string, string][];
 *  type: keyof typeof DEFAULT_SELECTION_FIELD_VALUES;
 * }} SelectionFieldDefinition
 *
 * @typedef {CommonFieldDefinition & {
 *  type: keyof typeof DEFAULT_STANDARD_FIELD_VALUES;
 * }} StandardFieldDefinition
 */

/**
 * @template [T={}]
 * @typedef {{
 *  args?: any[];
 *  context?: Record<string, any>;
 *  [key: string]: any;
 * } & Partial<T>} KwArgs
 */

/**
 * @param {string} name
 */
const camelToPascal = (name) =>
    name[0].toUpperCase() + name.slice(1).replace(/_([a-z])/g, (_, char) => char.toUpperCase());

/**
 * This function spawns a 2-level process to create field definitions: it's a function
 * returning a function returning a field descriptor.
 *
 * - this function ("generator") is called at the end of this file with pre-defined
 * parameters to configure the "constructor" functions, i.e. the ones that will
 * be called in the tests model definitions;
 *
 * - those "constructor" functions will then be called in model definitions and will
 * return the actual field descriptors.
 *
 * @template {FieldType} T
 * @template [RK=never]
 * @param {T} type
 * @param {{
 *  groupOperator?: GroupOperator;
 *  requiredKeys?: RK[];
 * }} params
 */
const makeFieldGenerator = (type, { groupOperator, requiredKeys = [] } = {}) => {
    const constructorFnName = camelToPascal(type);
    const defaultDef = {
        readonly: false,
        required: false,
        searchable: true,
        sortable: true,
        store: true,
        groupable: true,
    };
    if (groupOperator) {
        defaultDef.aggregator = groupOperator;
    }
    if (type !== "generic") {
        defaultDef.type = type;
    }

    // 2nd level: returns the "constructor" function
    return {
        /**
         * @param {Partial<Omit<T extends MonetaryFieldDefinition["type"]
         *  ? MonetaryFieldDefinition : T extends RelationalFieldDefinition["type"]
         *  ? RelationalFieldDefinition : T extends SelectionFieldDefinition["type"]
         *  ? SelectionFieldDefinition : StandardFieldDefinition, "name">>
         * } [fieldDefinition]
         */
        [constructorFnName](fieldDefinition) {
            // Creates a pre-version of the field definition
            const preDef = {
                ...defaultDef,
                ...fieldDefinition,
                [FIELD_SYMBOL]: true,
            };
            for (const key of requiredKeys) {
                if (!(key in preDef)) {
                    throw new MockServerError(
                        `missing key "${key}" in ${type || "generic"} field definition`
                    );
                }
            }

            const toAssign = {};

            // Fill default values in definition based on given properties
            if (isComputed(preDef)) {
                // By default: computed fields are readonly and not stored
                toAssign.readonly = fieldDefinition.readonly ?? true;
                toAssign.store = fieldDefinition.store ?? false;
            }

            // Remove aggregator for no-store expect related ones
            if (!preDef.store && !preDef.related) {
                toAssign.aggregator = fieldDefinition.aggregator ?? undefined;
                toAssign.groupable = fieldDefinition.groupable ?? false;
            }

            return Object.assign(preDef, toAssign);
        },
    }[constructorFnName];
};

/**
 * @param {FieldDefinition} field
 */
export function isComputed(field) {
    return globalThis.Boolean(field.compute || field.related);
}

export const Binary = makeFieldGenerator("binary");

export const Boolean = makeFieldGenerator("boolean");

export const Char = makeFieldGenerator("char");

export const Date = makeFieldGenerator("date");

export const Datetime = makeFieldGenerator("datetime");

export const Float = makeFieldGenerator("float", {
    groupOperator: "sum",
});

export const Generic = makeFieldGenerator("generic");

export const Html = makeFieldGenerator("html");

export const Image = makeFieldGenerator("image");

export const Integer = makeFieldGenerator("integer", {
    groupOperator: "sum",
});

export const Json = makeFieldGenerator("json");

export const Many2many = makeFieldGenerator("many2many", {
    requiredKeys: ["relation"],
});

export const Many2one = makeFieldGenerator("many2one", {
    requiredKeys: ["relation"],
});

export const Many2oneReference = makeFieldGenerator("many2one_reference", {
    requiredKeys: ["model_field", "relation"],
});

export const Monetary = makeFieldGenerator("monetary", {
    groupOperator: "sum",
    requiredKeys: ["currency_field"],
});

export const One2many = makeFieldGenerator("one2many", {
    requiredKeys: ["relation"],
});

export const Properties = makeFieldGenerator("properties");

export const PropertiesDefinition = makeFieldGenerator("properties_definition");

export const Reference = makeFieldGenerator("reference", {
    requiredKeys: ["selection"],
});

export const Selection = makeFieldGenerator("selection", {
    requiredKeys: ["selection"],
});

export const Text = makeFieldGenerator("text");

// Default field values
export const DEFAULT_MONEY_FIELD_VALUES = {
    monetary: () => 0,
};
export const DEFAULT_RELATIONAL_FIELD_VALUES = {
    many2many: () => [],
    many2one: () => false,
    many2one_reference: () => false,
    one2many: () => [],
};
export const DEFAULT_SELECTION_FIELD_VALUES = {
    reference: () => false,
    selection: () => false,
};
export const DEFAULT_STANDARD_FIELD_VALUES = {
    binary: () => false,
    boolean: () => false,
    char: () => false,
    date: () => false,
    datetime: () => false,
    float: () => 0,
    html: () => false,
    number: () => 0,
    image: () => false,
    integer: () => 0,
    json: () => false,
    properties: () => false,
    properties_definition: () => false,
    text: () => false,
};
export const DEFAULT_FIELD_VALUES = {
    ...DEFAULT_MONEY_FIELD_VALUES,
    ...DEFAULT_RELATIONAL_FIELD_VALUES,
    ...DEFAULT_SELECTION_FIELD_VALUES,
    ...DEFAULT_STANDARD_FIELD_VALUES,
};
export const FIELD_SYMBOL = Symbol("field");
