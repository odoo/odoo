import { deepCopy } from "@web/core/utils/objects";
import { MockServerError } from "./mock_server_utils";

/**
 * @typedef {import("fields").INumerical["aggregator"]} Aggregator
 * @typedef {import("fields").FieldDefinition} FieldDefinition
 * @typedef {import("fields").FieldDefinitionsByType} FieldDefinitionsByType
 * @typedef {import("fields").FieldType} FieldType
 * @typedef {import("./mock_model").ModelRecord} ModelRecord
 *
 * @typedef {{
 *  compute?: (() => void) | string;
 *  default?: RecordFieldValue | ((record: ModelRecord) => RecordFieldValue);
 *  onChange?: (record: ModelRecord) => void;
 * }} MockFieldProperties
 *
 * @typedef {number | string | boolean | number[]} RecordFieldValue
 */

/**
 * @param {string} name
 */
function camelToPascal(name) {
    return (
        name[0].toUpperCase() + name.slice(1).replace(R_CAMEL_CASE, (_, char) => char.toUpperCase())
    );
}

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
 * @template [R=never]
 * @param {T} type
 * @param {{
 *  aggregator?: Aggregator;
 *  requiredKeys?: R[];
 * }} params
 */
function makeFieldGenerator(type, { aggregator, requiredKeys = [] } = {}) {
    const constructorFnName = camelToPascal(type);
    const defaultDef = { ...DEFAULT_FIELD_PROPERTIES };
    if (aggregator) {
        defaultDef.aggregator = aggregator;
    }
    if (type !== "generic") {
        defaultDef.type = type;
    }

    // 2nd level: returns the "constructor" function
    return {
        /**
         * @param {Partial<FieldDefinitionsByType[T] & MockFieldProperties>} [properties]
         */
        [constructorFnName](properties) {
            // Creates a pre-version of the field definition
            const field = {
                ...defaultDef,
                ...properties,
                [S_FIELD]: true,
            };

            for (const key of requiredKeys) {
                if (!(key in field)) {
                    throw new MockServerError(
                        `Missing key "${key}" in ${type || "generic"} field definition`
                    );
                }
            }

            // Fill default values in definition based on given properties
            if (isComputed(field)) {
                // By default: computed fields are readonly and not stored
                field.readonly = properties.readonly ?? true;
                field.store = properties.store ?? false;
            }

            return field;
        },
    }[constructorFnName];
}

const R_CAMEL_CASE = /_([a-z])/g;
const R_ENDS_WITH_ID = /_id(s)?$/i;
const R_LOWER_FOLLOWED_BY_UPPER = /([a-z])([A-Z])/g;
const R_SPACE_OR_UNDERSCORE = /[\s_]+/g;

/**
 * @param {Record<string, FieldDefinition & MockFieldProperties>} fields
 */
export function copyFields(fields) {
    const fieldsCopy = {};
    for (const [fieldName, field] of Object.entries(fields)) {
        const fieldCopy = {};
        for (const [property, value] of Object.entries(field)) {
            fieldCopy[property] = typeof value === "object" ? deepCopy(value) : value;
        }
        fieldsCopy[fieldName] = fieldCopy;
    }
    return fieldsCopy;
}

/**
 * @param {FieldDefinition & MockFieldProperties} field
 */
export function isComputed(field) {
    return globalThis.Boolean(field.compute || field.related);
}

/**
 * @param {unknown} value
 */
export function getFieldDisplayName(value) {
    const str = String(value)
        .replace(R_ENDS_WITH_ID, "$1")
        .replace(R_LOWER_FOLLOWED_BY_UPPER, (_, a, b) => `${a} ${b.toLowerCase()}`)
        .replace(R_SPACE_OR_UNDERSCORE, " ")
        .trim();
    return str[0].toUpperCase() + str.slice(1);
}

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

export const DEFAULT_FIELD_PROPERTIES = {
    readonly: false,
    required: false,
    searchable: true,
    sortable: true,
    store: true,
    groupable: true,
};

export const S_FIELD = Symbol("field");
export const S_SERVER_FIELD = Symbol("field");

export const Binary = makeFieldGenerator("binary");

export const Boolean = makeFieldGenerator("boolean");

export const Char = makeFieldGenerator("char");

export const Date = makeFieldGenerator("date");

export const Datetime = makeFieldGenerator("datetime");

export const Float = makeFieldGenerator("float", {
    aggregator: "sum",
});

export const Generic = makeFieldGenerator("generic");

export const Html = makeFieldGenerator("html");

export const Image = makeFieldGenerator("image");

export const Integer = makeFieldGenerator("integer", {
    aggregator: "sum",
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
    aggregator: "sum",
    requiredKeys: ["currency_field"],
});

export const One2many = makeFieldGenerator("one2many", {
    requiredKeys: ["relation"],
});

export const Properties = makeFieldGenerator("properties", {
    requiredKeys: ["definition_record", "definition_record_field"],
});

export const PropertiesDefinition = makeFieldGenerator("properties_definition");

export const Reference = makeFieldGenerator("reference", {
    requiredKeys: ["selection"],
});

export const Selection = makeFieldGenerator("selection", {
    requiredKeys: ["selection"],
});

export const Text = makeFieldGenerator("text");
