/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
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

const { DateTime } = luxon;

// ============================================================================

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
    static props = ["value", "update"];
    static template = "web.DomainSelector.TagInput";

    setup() {
        this.inputRef = useRef("input");
    }

    removeTag(tagIndex) {
        return this.props.update([
            ...this.props.value.slice(0, tagIndex),
            ...this.props.value.slice(tagIndex + 1),
        ]);
    }

    addTag(value) {
        return this.props.update([...this.props.value, value]);
    }

    onBtnClick() {
        const value = this.inputRef.el.value;
        this.inputRef.el.value = "";
        return this.addTag(value);
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

function makeEditor(component, props) {
    return {
        component,
        props: props || (({ value, update }) => ({ value, update })),
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
        "equal",
        "not_equal",
        "greater_than",
        "greater_equal",
        "less_than",
        "less_equal",
        "ilike",
        "not_ilike",
        "like",
        "not_like",
        "equal_like",
        "equal_ilike",
        "child_of",
        "parent_of",
        "in",
        "not_in",
        "set",
        "not_set",
    ],
    editors: { default: makeEditor(Input) },
    defaultValue: () => "",
};

// ----------------------------------------------------------------------------

const BOOLEAN = {
    operators: ["is", "is_not"],
    editors: {
        default: makeEditor(Select, ({ value, update }) => ({
            value,
            update,
            options: [
                [true, _lt("set")],
                [false, _lt("not set")],
            ],
        })),
    },
    defaultValue: () => true,
};

// ----------------------------------------------------------------------------

const DATETIME = {
    operators: [
        "equal",
        "not_equal",
        "greater_than",
        "greater_equal",
        "less_than",
        "less_equal",
        "set",
        "not_set",
    ],
    editors: {
        default: makeEditor(DateTimeInput, ({ field, value, update }) => ({
            value: genericDeserializeDate(field.type, value),
            type: field.type,
            onApply: (value) =>
                update(value ? genericSerializeDate(field.type, value) : DateTime.local()),
        })),
    },
    defaultValue: ({ type }) => genericSerializeDate(type, DateTime.local()),
};

// ----------------------------------------------------------------------------

const TEXT = {
    operators: ["equal", "not_equal", "ilike", "not_ilike", "set", "not_set", "in", "not_in"],
    editors: {
        default: makeEditor(Input),
        in: makeEditor(TagInput),
        not_in: makeEditor(TagInput),
    },
    defaultValue: () => "",
};

// ----------------------------------------------------------------------------

const NUMBER = {
    operators: [
        "equal",
        "not_equal",
        "greater_than",
        "greater_equal",
        "less_than",
        "less_equal",
        "ilike",
        "not_ilike",
        "set",
        "not_set",
    ],
    editors: {
        default: makeEditor(Input, ({ value, update, field }) => ({
            value: `${value}`,
            update: (value) => update(parseValue(field.type, value)),
        })),
    },
    defaultValue: () => 1,
};

// ----------------------------------------------------------------------------

const RELATIONAL = {
    operators: ["equal", "not_equal", "ilike", "not_ilike", "set", "not_set"],
    editors: { default: makeEditor(Input) },
    defaultValue: (field) => (field.type === "many2one" ? 1 : []),
};

// ----------------------------------------------------------------------------

const SELECTION_EDITOR_IN = makeEditor(Input, ({ value, update }) => ({
    value: formatAST(toPyValue(value)),
    update: (value) => update(evaluateExpr(value)),
}));

const SELECTION = {
    operators: ["equal", "not_equal", "in", "not_in", "set", "not_set"],
    editors: {
        default: makeEditor(Select, ({ value, update, field }) => ({
            value,
            update,
            options: field.selection,
        })),
        in: SELECTION_EDITOR_IN,
        not_in: SELECTION_EDITOR_IN,
    },
    defaultValue: (field) => field.selection[0][0] ?? false,
};

// ----------------------------------------------------------------------------

const PROPERTIES = {
    operators: ["set", "not_set"],
    defaultValue: () => false,
};

const PROPERTIES_SELECTION = {
    operators: ["equal", "not_equal", "set", "not_set"],
    editors: {
        default: makeEditor(Select, ({ value, update, field }) => ({
            value,
            update,
            options: field.selection || [],
        })),
    },
    defaultValue: (field) => field.selection?.[0]?.[0] ?? false,
};

const PROPERTIES_RELATIONAL = {
    operators: ["equal", "not_equal", "set", "not_set"],
    editors: { default: makeEditor(Input) },
    defaultValue: (field) => (field.type === "many2one" ? 1 : []),
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
    many2many: RELATIONAL,
    many2one: RELATIONAL,
    monetary: NUMBER,
    one2many: RELATIONAL,
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
    if (fieldDef.is_property && PROPERTIES_DESCRIPTIONS[fieldDef.type]) {
        return PROPERTIES_DESCRIPTIONS[fieldDef.type];
    } else if (FIELD_DESCRIPTIONS[fieldDef.type]) {
        return FIELD_DESCRIPTIONS[fieldDef.type];
    } else {
        return DEFAULT;
    }
}

export function getEditorInfo(fieldDef, operator) {
    const fieldInfo = getFieldInfo(fieldDef);
    return fieldInfo.editors[operator] || fieldInfo.editors.default;
}

export function getOperatorsInfo(fieldDef) {
    return selectOperators(getFieldInfo(fieldDef).operators);
}

export function getDefaultFieldValue(fieldDef) {
    const desc = getFieldInfo(fieldDef);
    return desc.defaultValue(fieldDef);
}
