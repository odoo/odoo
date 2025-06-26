import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { Domain } from "@web/core/domain";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { connector, Expression, formatValue, isTree } from "@web/core/tree_editor/condition_tree";
import {
    DATE_TODAY_STRING_EXPRESSION,
    DATETIME_END_OF_TODAY_STRING_EXPRESSION,
    DATETIME_TODAY_STRING_EXPRESSION,
    isEndOfTodayExpr,
    isTodayExpr,
} from "@web/core/tree_editor/virtual_operators";

import {
    DomainSelectorAutocomplete,
    DomainSelectorSingleAutocomplete,
} from "@web/core/tree_editor/tree_editor_autocomplete";
import { Input, List, Range, Select, Within } from "@web/core/tree_editor/tree_editor_components";
import { disambiguate, getResModel, isId } from "@web/core/tree_editor/utils";
import { unique } from "@web/core/utils/arrays";

const { DateTime } = luxon;

// ============================================================================

const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

function parseValue(fieldType, value) {
    const parser = parsers.get(fieldType, (value) => value);
    try {
        return parser(value);
    } catch {
        return value;
    }
}

function isParsable(fieldType, value) {
    const parser = parsers.get(fieldType, (value) => value);
    try {
        parser(value);
    } catch {
        return false;
    }
    return true;
}

function genericSerializeDate(type, value) {
    return type === "date" ? serializeDate(value) : serializeDateTime(value);
}

function genericDeserializeDate(type, value) {
    return type === "date" ? deserializeDate(value) : deserializeDateTime(value);
}

function placeholderForSelect(displayPlaceholder) {
    if (displayPlaceholder) {
        return _t(`Select one or several criteria`);
    }
}

function placeholderForInput(displayPlaceholder) {
    if (displayPlaceholder) {
        return _t(`Press "Enter" to add criterion`);
    }
}

const STRING_EDITOR = {
    component: Input,
    extractProps: ({ value, update, displayPlaceholder }) => ({
        value,
        update,
        placeholder: placeholderForInput(displayPlaceholder),
    }),
    isSupported: (value) => typeof value === "string",
    defaultValue: () => "",
};

function makeSelectEditor(options, params = {}) {
    const getOption = (value) => options.find(([v]) => v === value) || null;
    return {
        component: Select,
        extractProps: ({ value, update, displayPlaceholder }) => ({
            value,
            update,
            options,
            addBlankOption: params.addBlankOption,
            placeholder: placeholderForSelect(displayPlaceholder),
        }),
        isSupported: (value) => Boolean(getOption(value)),
        defaultValue: () => options[0]?.[0] ?? false,
        stringify: (value, disambiguate) => {
            const option = getOption(value);
            return option ? option[1] : disambiguate ? formatValue(value) : String(value);
        },
        message: _t("Value not in selection"),
    };
}

function getDomain(fieldDef) {
    if (fieldDef.type === "many2one") {
        return [];
    }
    try {
        return new Domain(fieldDef.domain || []).toList();
    } catch {
        return [];
    }
}

function makeAutoCompleteEditor(fieldDef) {
    return {
        component: DomainSelectorAutocomplete,
        extractProps: ({ value, update }) => ({
            resModel: getResModel(fieldDef),
            fieldString: fieldDef.string,
            domain: getDomain(fieldDef),
            update: (value) => update(unique(value)),
            resIds: unique(value),
            placeholder: placeholderForSelect(true),
        }),
        isSupported: (value) => Array.isArray(value),
        defaultValue: () => [],
    };
}

function isLitteralObject(value) {
    return typeof value === "object" && !Array.isArray(value) && value !== null;
}

// ============================================================================

function getPartialValueEditorInfo(fieldDef, operator, params = {}) {
    switch (operator) {
        case "set":
        case "not_set":
            return {
                component: null,
                extractProps: null,
                isSupported: (value) =>
                    value === false || (fieldDef.type === "boolean" && value === true),
                defaultValue: () => false,
            };
        case "=like":
        case "=ilike":
        case "like":
        case "not like":
        case "ilike":
        case "not ilike":
            return STRING_EDITOR;
        case "not_between":
        case "between": {
            const editorInfo = getValueEditorInfo(fieldDef, "=", params);
            const { defaultValue } = getValueEditorInfo(fieldDef, "=", {
                ...params,
                forBetween: true,
            });
            return {
                component: Range,
                extractProps: ({ value, update }) => ({
                    value,
                    update,
                    editorInfo,
                }),
                isSupported: (value) => Array.isArray(value) && value.length === 2,
                defaultValue: () => {
                    const value = defaultValue();
                    return isLitteralObject(value) ? [value.start, value.end] : [value, value];
                },
                shouldResetValue: (value) =>
                    !editorInfo.isSupported(value[0]) || !editorInfo.isSupported(value[1]),
            };
        }
        case "last":
        case "not_last":
        case "next":
        case "not_next": {
            return {
                component: Within,
                extractProps: ({ value, update }) => ({
                    value,
                    update,
                    amountEditorInfo: {
                        ...getValueEditorInfo({ type: "integer" }, "=", params),
                        isSupported: (value) => Number.isInteger(value) && value >= 0,
                        message: _t("Positive integer expected"),
                    },
                    optionEditorInfo: makeSelectEditor(Within.options),
                }),
                isSupported: (value) =>
                    Array.isArray(value) && value.length === 3 && value[2] === fieldDef.type,
                defaultValue: () => [1, "months", fieldDef.type],
                shouldResetValue: (value) =>
                    !Number.isInteger(value[0]) ||
                    value[0] < 0 ||
                    !Within.options.some((o) => o[0] === value[1]),
            };
        }
        case "in":
        case "not in": {
            switch (fieldDef.type) {
                case "tags":
                    return STRING_EDITOR;
                case "many2one":
                case "many2many":
                case "one2many":
                    return makeAutoCompleteEditor(fieldDef);
                default: {
                    const editorInfo = getValueEditorInfo(fieldDef, "=", {
                        ...params,
                        addBlankOption: true,
                        startEmpty: true,
                    });
                    return {
                        component: List,
                        extractProps: ({ value, update }) => {
                            if (!disambiguate(value)) {
                                const { stringify } = editorInfo;
                                editorInfo.stringify = (val) => stringify(val, false);
                            }
                            return {
                                value,
                                update,
                                editorInfo,
                            };
                        },
                        isSupported: (value) => Array.isArray(value),
                        defaultValue: () => [],
                        shouldResetValue: (value) => !value.every(editorInfo.isSupported),
                    };
                }
            }
        }
        case "any":
        case "not any": {
            switch (fieldDef.type) {
                case "many2one":
                case "many2many":
                case "one2many": {
                    return {
                        component: null,
                        extractProps: null,
                        isSupported: isTree,
                        defaultValue: () => connector("&"),
                    };
                }
            }
        }
    }

    const { type } = fieldDef;
    switch (type) {
        case "integer":
        case "float":
        case "monetary": {
            const formatType = type === "integer" ? "integer" : "float";
            return {
                component: Input,
                extractProps: ({ value, update, displayPlaceholder }) => ({
                    value: String(value),
                    update: (value) => update(parseValue(formatType, value)),
                    startEmpty: params.startEmpty,
                    placeholder: placeholderForInput(displayPlaceholder),
                }),
                isSupported: () => true,
                defaultValue: () => (params.forBetween ? { start: 1, end: 1 } : 1),
                shouldResetValue: (value) => parseValue(formatType, value) === value,
            };
        }
        case "date":
        case "datetime":
            if (["today", "not_today"].includes(operator)) {
                return {
                    component: null,
                    extractProps: null,
                    isSupported: (value) => {
                        if (type === "date") {
                            return isTodayExpr(value, type);
                        }
                        return (
                            Array.isArray(value) &&
                            value.length === 2 &&
                            isTodayExpr(value[0], type) &&
                            isEndOfTodayExpr(value[1])
                        );
                    },
                    defaultValue: () => {
                        if (type === "date") {
                            return new Expression(DATE_TODAY_STRING_EXPRESSION);
                        }
                        return [
                            new Expression(DATETIME_TODAY_STRING_EXPRESSION),
                            new Expression(DATETIME_END_OF_TODAY_STRING_EXPRESSION),
                        ];
                    },
                };
            }
            return {
                component: DateTimeInput,
                extractProps: ({ value, update, displayPlaceholder }) => ({
                    value:
                        params.startEmpty || value === false
                            ? false
                            : genericDeserializeDate(type, value),
                    type,
                    onApply: (value) => {
                        if (!params.startEmpty || value) {
                            update(
                                genericSerializeDate(type, value || DateTime.local().startOf("day"))
                            );
                        }
                    },
                    placeholder: placeholderForSelect(displayPlaceholder),
                }),
                isSupported: (value) => typeof value === "string" && isParsable(type, value),
                defaultValue: () => {
                    const datetime = DateTime.local();
                    const defaultValue = genericSerializeDate(type, datetime.startOf("day"));
                    if (params.forBetween) {
                        return {
                            start: defaultValue,
                            end: genericSerializeDate(type, datetime.endOf("day")),
                        };
                    }
                    return defaultValue;
                },
                stringify: (value) => {
                    if (value === false) {
                        return _t("False");
                    }
                    if (typeof value === "string" && isParsable(type, value)) {
                        const formatter = formatters.get(type, formatValue);
                        return formatter(genericDeserializeDate(type, value));
                    }
                    return formatValue(value);
                },
                message: _t("Not a valid %s", type),
            };
        case "char":
        case "html":
        case "text":
            return STRING_EDITOR;
        case "many2one": {
            if (["=", "!="].includes(operator)) {
                return {
                    component: DomainSelectorSingleAutocomplete,
                    extractProps: ({ value, update }) => ({
                        resModel: getResModel(fieldDef),
                        fieldString: fieldDef.string,
                        update,
                        resId: value,
                    }),
                    isSupported: () => true,
                    defaultValue: () => false,
                    shouldResetValue: (value) => value !== false && !isId(value),
                };
            } else if (["parent_of", "child_of"].includes(operator)) {
                return makeAutoCompleteEditor(fieldDef);
            }
            break;
        }
        case "many2many":
        case "one2many":
            if (["=", "!="].includes(operator)) {
                return makeAutoCompleteEditor(fieldDef);
            }
            break;
        case "selection": {
            const options = fieldDef.selection || [];
            return makeSelectEditor(options, params);
        }
        case undefined: {
            const options = [[1, "1"]];
            return makeSelectEditor(options, params);
        }
    }

    // Global default for visualization mainly. It is there to visualize what
    // has been produced in the debug textarea (in o_domain_selector_debug_container)
    // It is hardly useful to produce a string in general.
    return {
        component: Input,
        extractProps: ({ value, update }) => ({
            value: String(value),
            update,
        }),
        isSupported: () => true,
        defaultValue: () => "",
    };
}

export function getValueEditorInfo(fieldDef, operator, options = {}) {
    const info = getPartialValueEditorInfo(fieldDef || {}, operator, options);
    return {
        extractProps: ({ value, update }) => ({ value, update }),
        message: _t("Value not supported"),
        stringify: (val, disambiguate = true) => {
            if (disambiguate) {
                return formatValue(val);
            }
            return String(val);
        },
        ...info,
    };
}

export function getDefaultValue(fieldDef, operator, value = null) {
    const { isSupported, shouldResetValue, defaultValue } = getValueEditorInfo(fieldDef, operator);
    if (value === null || !isSupported(value) || shouldResetValue?.(value)) {
        return defaultValue();
    }
    return value;
}
