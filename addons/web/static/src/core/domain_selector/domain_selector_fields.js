/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
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

const DATE = {
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
        default: makeEditor(DatePicker, ({ value, update }) => ({
            date: deserializeDate(value),
            onDateTimeChanged: (value) => {
                if (!value.isValid) {
                    return;
                }
                return update(value ? serializeDate(value) : luxon.DateTime.local());
            },
        })),
    },
    defaultValue: () => serializeDate(luxon.DateTime.local()),
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
        default: makeEditor(DateTimePicker, ({ value, update }) => ({
            date: deserializeDateTime(value),
            onDateTimeChanged: (value) => {
                if (!value.isValid) {
                    return;
                }
                return update(value ? serializeDateTime(value) : luxon.DateTime.local());
            },
        })),
    },
    defaultValue: () => serializeDateTime(luxon.DateTime.local()),
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
    defaultValue: (field) => field.selection[0][0],
};

// ============================================================================

export const FIELD_DESCRIPTIONS = {
    boolean: BOOLEAN,
    char: TEXT,
    date: DATE,
    datetime: DATETIME,
    float: NUMBER,
    html: TEXT,
    integer: NUMBER,
    many2many: RELATIONAL,
    many2one: RELATIONAL,
    monetary: NUMBER,
    one2many: RELATIONAL,
    selection: SELECTION,
    text: TEXT,
};

export function getFieldInfo(fieldType) {
    return FIELD_DESCRIPTIONS[fieldType] || DEFAULT;
}

export function getEditorInfo(fieldType, operator) {
    const fieldInfo = getFieldInfo(fieldType);
    return fieldInfo.editors[operator] || fieldInfo.editors.default;
}

export function getOperatorsInfo(fieldType) {
    return selectOperators(getFieldInfo(fieldType).operators);
}

export function getDefaultFieldValue(field) {
    const desc = getFieldInfo(field.type);
    return desc.defaultValue(field);
}
