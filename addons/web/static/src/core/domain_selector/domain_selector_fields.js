/** @odoo-module **/

import { Component } from "@odoo/owl";
import { selectOperators } from "@web/core/domain_selector/domain_selector_operators";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { _lt } from "@web/core/l10n/translation";
import { evaluateExpr, formatAST } from "@web/core/py_js/py";
import { toPyValue } from "@web/core/py_js/py_utils";
import { registry } from "@web/core/registry";
import { DateTimeInput } from "../datetime/datetime_input";
import { TagsList } from "@web/core/tags_list/tags_list";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { Expression, formatValue } from "@web/core/domain_tree";
import {
    DomainSelectorAutocomplete,
    DomainSelectorSingleAutocomplete,
} from "./domain_selector_autocomplete";

const { DateTime } = luxon;

const identity = (x) => x;
const isString = (value) => typeof value === "string";

// ============================================================================

export class Editor extends Component {
    static props = ["info", "value", "update", "fieldDef?"];
    static template = "web.DomainSelector.Editor";

    get stringifiedValue() {
        return formatValue(this.props.value);
    }
}

export class PathEditor extends Editor {
    static props = ["isDebugMode", "readonly", "resModel", "path", "update"];
    static template = "web.DomainSelector.PathEditor";

    get component() {
        return ModelFieldSelector;
    }

    get isSupportedPath() {
        const { path } = this.props;
        return [0, 1].includes(path) || typeof path === "string";
    }

    get stringifiedPath() {
        return formatValue(this.props.path);
    }

    onClear() {
        this.props.update();
    }
}

class Input extends Component {
    static props = ["value", "update"];
    static template = "web.DomainSelector.Input";
}

class Select extends Component {
    static props = ["value", "update", "options"];
    static template = "web.DomainSelector.Select";

    deserialize(value) {
        return JSON.parse(value);
    }

    serialize(value) {
        return JSON.stringify(value);
    }
}

class TagInput extends Component {
    static components = { TagsList };
    static props = ["value", "update"];
    static template = "web.DomainSelector.TagInput";
    get value() {
        return Array.isArray(this.props.value) ? this.props.value : [this.props.value];
    }
    get tags() {
        return this.value.map((val, index) => ({
            text: String(val),
            colorIndex: typeof val === "string" ? 0 : 2,
            onDelete: () => {
                this.props.update([...this.value.slice(0, index), ...this.value.slice(index + 1)]);
            },
        }));
    }
    onChange(ev) {
        const newVal = ev.currentTarget.value;
        ev.currentTarget.value = "";
        this.props.update([...this.value, newVal]);
    }
}

class Range extends Component {
    static props = ["value", "update", "editorInfo", "fieldDef"];
    static template = "web.DomainSelector.Range";
    static components = { Editor };

    update(index, newValue) {
        const result = [...this.props.value];
        result[index] = newValue;
        return this.props.update(result);
    }

    getValue(index) {
        return this.props.value[index];
    }

    getUpdater(index) {
        return (newValue) => this.update(index, newValue);
    }
}

// ============================================================================

const parsers = registry.category("parsers");
function parseValue(fieldType, value) {
    const parser = parsers.get(fieldType, (value) => value);
    try {
        return parser(value);
    } catch {
        return value;
    }
}

function makeEditor(component, { props, isSupported, defaultValue } = {}) {
    return {
        component,
        extractProps: props || (({ value, update }) => ({ value, update })),
        isSupported: isSupported || ((value) => !(value instanceof Expression)),
        defaultValue:
            defaultValue ||
            ((fieldDef, operator) => {
                switch (operator) {
                    case "in":
                    case "not in":
                        return [];
                    case "set":
                    case "not_set":
                    case "child_of":
                    case "parent_of":
                        return false;
                    case "is":
                    case "is_not":
                        return true;
                    case "=like":
                    case "=ilike":
                    case "like":
                    case "not like":
                    case "ilike":
                    case "not ilike":
                        return "";
                    default: {
                        let val;
                        switch (fieldDef?.type) {
                            case "integer":
                            case "float":
                            case "monetary":
                                val = 1;
                                break;
                            case "boolean":
                                val = false;
                                break;
                            default:
                                val = "";
                        }
                        if (operator === "between") {
                            return [val, val];
                        }
                        return val;
                    }
                }
            }),
    };
}

/**
 * @param {"date" | "datetime"} type
 * @param  {Parameters<serializeDate>} args
 */
const genericSerializeDate = (type, ...args) =>
    type === "date" ? serializeDate(...args) : serializeDateTime(...args);

/**
 * @param {"date" | "datetime"} type
 * @param  {Parameters<deserializeDate>} args
 */
const genericDeserializeDate = (type, ...args) =>
    type === "date" ? deserializeDate(...args) : deserializeDateTime(...args);

const DEFAULT = {
    operators: [
        "=",
        "!=",
        ">",
        ">=",
        "<",
        "<=",
        "ilike",
        "not ilike",
        "like",
        "not like",
        "=like",
        "=ilike",
        "child_of",
        "parent_of",
        "in",
        "not in",
        "set",
        "not_set",
    ],
    editors: { default: makeEditor(Input) },
    defaultValue: () => "",
};

const SET_NOT_SET_EDITOR = {
    component: null,
    extractProps: identity,
    isSupported: (value) => value === false,
};

// ----------------------------------------------------------------------------

const BOOLEAN = {
    operators: ["is", "is_not"],
    editors: {
        default: makeEditor(Select, {
            props: ({ value, update }) => ({
                value,
                update,
                options: [
                    [true, _lt("set")],
                    [false, _lt("not set")],
                ],
            }),
        }),
    },
    defaultValue: () => true,
};

// ----------------------------------------------------------------------------

const DATETIME_EDITOR_BETWEEN = makeEditor(Range, {
    props: ({ value, update, fieldDef }) => ({
        value,
        update,
        editorInfo: getEditorInfo(fieldDef),
        fieldDef,
    }),
});

const DATETIME = {
    operators: ["=", "!=", ">", ">=", "<", "<=", "between", "set", "not_set"],
    editors: {
        default: makeEditor(DateTimeInput, {
            props: ({ value, update, fieldDef }) => ({
                value: genericDeserializeDate(fieldDef.type, value),
                type: fieldDef.type,
                onApply: (value) =>
                    update(value ? genericSerializeDate(fieldDef.type, value) : DateTime.local()),
            }),
        }),
        between: DATETIME_EDITOR_BETWEEN,
    },
    defaultValue: ({ type }) => genericSerializeDate(type, DateTime.local()),
};

// ----------------------------------------------------------------------------

const TEXT = {
    operators: ["=", "!=", "ilike", "not ilike", "in", "not in", "set", "not_set"],
    editors: {
        default: makeEditor(Input),
        in: makeEditor(TagInput),
        "not in": makeEditor(TagInput),
    },
    defaultValue: () => "",
};

// ----------------------------------------------------------------------------

const NUMBER = {
    operators: ["=", "!=", ">", ">=", "<", "<=", "between", "ilike", "not ilike", "set", "not_set"],
    editors: {
        default: makeEditor(Input, {
            props: ({ value, update, fieldDef }) => ({
                value: String(value),
                update: (value) => update(parseValue(fieldDef.type, value)),
            }),
        }),
        between: makeEditor(Range, {
            props: ({ value, update, fieldDef }) => ({
                value,
                update,
                editorInfo: getEditorInfo(fieldDef),
                fieldDef,
            }),
        }),
    },
    defaultValue: () => 1,
};

// ----------------------------------------------------------------------------

const isId = (value) => Number.isInteger(value) && value >= 1;

const RELATIONAL_EDITOR_EQUALITY = makeEditor(DomainSelectorSingleAutocomplete, {
    props: ({ value, update, fieldDef }) => {
        return {
            resModel: fieldDef.relation,
            fieldString: fieldDef.string,
            update,
            value,
        };
    },
    isSupported: () => true,
});
RELATIONAL_EDITOR_EQUALITY.shouldResetValue = (value) => value !== false || !isId(value);

const RELATIONAL_EDITOR_IN = makeEditor(DomainSelectorAutocomplete, {
    props: ({ value, update, fieldDef }) => {
        return {
            resModel: fieldDef.relation,
            fieldString: fieldDef.string,
            update: (value) => update([...new Set(value)]),
            value: Array.isArray(value) ? [...new Set(value)] : value,
        };
    },
    isSupported: (value) => Array.isArray(value),
});

const MANY2ONE = {
    operators: ["in", "not in", "=", "!=", "ilike", "not ilike", "set", "not_set"],
    editors: {
        default: makeEditor(Input, { isSupported: isString }), // ilike, not ilike + others (found in original domain)
        "=": RELATIONAL_EDITOR_EQUALITY,
        "!=": RELATIONAL_EDITOR_EQUALITY,
        in: RELATIONAL_EDITOR_IN,
        "not in": RELATIONAL_EDITOR_IN,
        set: SET_NOT_SET_EDITOR,
        not_set: SET_NOT_SET_EDITOR,
    },
    defaultValue: (_, operator) => {
        switch (operator) {
            case "in":
            case "not in":
                return [];
            case "=":
            case "!=":
            case "set":
            case "not_set":
                return false;
            default:
                return "";
        }
    },
};

const X2MANY = {
    operators: ["in", "not in", "=", "!=", "ilike", "not ilike", "set", "not_set"],
    editors: {
        default: makeEditor(Input, { isSupported: isString }), // ilike, not ilike + others (found in original domain)
        in: RELATIONAL_EDITOR_IN,
        "not in": RELATIONAL_EDITOR_IN,
        "=": RELATIONAL_EDITOR_IN,
        "!=": RELATIONAL_EDITOR_IN,
        set: SET_NOT_SET_EDITOR,
        not_set: SET_NOT_SET_EDITOR,
    },
    defaultValue: (_, operator) => {
        switch (operator) {
            case "in":
            case "not in":
            case "=":
            case "!=":
                return [];
            case "set":
            case "not_set":
                return false;
            default:
                return "";
        }
    },
};

// ----------------------------------------------------------------------------

const SELECTION_EDITOR_IN = makeEditor(Input, {
    props: ({ value, update }) => ({
        value: formatAST(toPyValue(value)),
        update: (value) => update(evaluateExpr(value)),
    }),
});

const SELECTION = {
    operators: ["=", "!=", "in", "not in", "set", "not_set"],
    editors: {
        default: makeEditor(Select, {
            props: ({ value, update, fieldDef }) => ({
                value,
                update,
                options: fieldDef.selection || [],
            }),
        }),
        in: SELECTION_EDITOR_IN,
        "not in": SELECTION_EDITOR_IN,
    },
    defaultValue: (fieldDef) => fieldDef.selection[0][0] ?? false,
};

// ----------------------------------------------------------------------------

const PROPERTIES = {
    operators: ["set", "not_set"],
    defaultValue: () => false,
};

const PROPERTIES_SELECTION = {
    operators: ["=", "!=", "set", "not_set"],
    editors: {
        default: makeEditor(Select, {
            props: ({ value, update, fieldDef }) => ({
                value,
                update,
                options: fieldDef.selection || [],
            }),
        }),
    },
    defaultValue: ({ selection }) => selection?.[0]?.[0] ?? false,
};

const PROPERTIES_RELATIONAL = {
    operators: ["=", "!=", "set", "not_set"],
    editors: { default: makeEditor(Input) },
    defaultValue: (fieldDef) => (fieldDef.type === "many2one" ? 1 : []),
};

// ----------------------------------------------------------------------------

const JSON_FIELD = {
    operators: ["=", "!=", "ilike", "not ilike", "set", "not_set"],
    editors: {
        default: makeEditor(Input),
    },
    defaultValue: () => "",
};

// ============================================================================

export const FIELD_DESCRIPTIONS = {
    boolean: BOOLEAN,
    char: TEXT,
    date: DATETIME,
    datetime: DATETIME,
    float: NUMBER,
    html: TEXT,
    integer: NUMBER,
    json: JSON_FIELD,
    many2many: X2MANY,
    many2one: MANY2ONE,
    monetary: NUMBER,
    one2many: X2MANY,
    properties: PROPERTIES,
    properties_definition: PROPERTIES,
    selection: SELECTION,
    text: TEXT,
};

const PROPERTIES_DESCRIPTIONS = {
    selection: PROPERTIES_SELECTION,
    many2many: PROPERTIES_RELATIONAL,
    many2one: PROPERTIES_RELATIONAL,
    one2many: PROPERTIES_RELATIONAL,
    tags: PROPERTIES_RELATIONAL,
};

export function getFieldInfo(fieldDef) {
    const { is_property, type } = fieldDef || {};
    if (is_property && PROPERTIES_DESCRIPTIONS[type]) {
        return PROPERTIES_DESCRIPTIONS[type];
    } else if (FIELD_DESCRIPTIONS[type]) {
        return FIELD_DESCRIPTIONS[type];
    } else {
        return DEFAULT;
    }
}

export function getEditorInfo(fieldDef, operator) {
    const descr = getFieldInfo(fieldDef);
    const editorInfo = descr.editors[operator] || descr.editors.default;
    editorInfo.defaultValue = () => getDefaultValue(fieldDef, operator);
    return editorInfo;
}

export function getOperatorsInfo(fieldDef) {
    const descr = getFieldInfo(fieldDef);
    return selectOperators(descr.operators);
}

export function getDefaultValue(fieldDef, operator) {
    const descr = getFieldInfo(fieldDef);
    return descr.defaultValue(fieldDef, operator);
}

export function getDefaultOperator(fieldDef) {
    const descr = getFieldInfo(fieldDef);
    return descr.operators[0];
}
