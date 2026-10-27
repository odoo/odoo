/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { combineModifiers } from "@web/model/relational_model/utils";

export const X2M_TYPES = ["one2many", "many2many"];
const NUMERIC_TYPES = ["integer", "float", "monetary"];

/**
 * @typedef ViewActiveActions {
 * @property {"view"} type
 * @property {boolean} edit
 * @property {boolean} create
 * @property {boolean} delete
 * @property {boolean} duplicate
 */

export const BUTTON_CLICK_PARAMS = [
    "name",
    "type",
    "args",
    "context",
    "close",
    "confirm",
    "confirm-title",
    "confirm-label",
    "special",
    "effect",
    "help",
    // WOWL SAD: is adding the support for debounce attribute here justified or should we
    // just override compileButton in kanban compiler to add the debounce?
    "debounce",
    // WOWL JPP: is adding the support for not oppening the dialog of confirmation in the settings view
    // This should be refactor someday
    "noSaveDialog",
];

/**
 * Parse the arch to check if is true or false
 * If the string is empty, 0, False or false it's considered as false
 * The rest is considered as true
 *
 * @param {string} str
 * @param {boolean} [trueIfEmpty=false]
 * @returns {boolean}
 */
export function archParseBoolean(str, trueIfEmpty = false) {
    return str ? !/^false|0$/i.test(str) : trueIfEmpty;
}

/**
 * @param {string?} type
 * @returns {string | false}
 */
function getViewClass(type) {
    const isValidType = Boolean(type) && registry.category("views").contains(type);
    return isValidType && `o_${type}_view`;
}

/**
 * @param {string?} viewType
 * @param {Element?} rootNode
 * @param {string[]} additionalClassList
 * @returns {string}
 */
export function computeViewClassName(viewType, rootNode, additionalClassList = []) {
    const subType = rootNode?.getAttribute("js_class");
    const classList = rootNode?.getAttribute("class")?.split(" ") || [];
    const uniqueClasses = new Set([
        getViewClass(viewType),
        getViewClass(subType),
        ...classList,
        ...additionalClassList,
    ]);
    return Array.from(uniqueClasses)
        .filter((c) => c) // remove falsy values
        .join(" ");
}

/**
 * TODO: doc
 *
 * @param {Object} fields
 * @param {Object} fieldAttrs
 * @param {string[]} activeMeasures
 * @returns {Object}
 */
export const computeReportMeasures = (fields, fieldAttrs, activeMeasures) => {
    const measures = {
        __count: { name: "__count", string: _t("Count"), type: "integer" },
    };
    for (const [fieldName, field] of Object.entries(fields)) {
        if (fieldName === "id" || !field.store) {
            continue;
        }
        const { isInvisible } = fieldAttrs[fieldName] || {};
        if (isInvisible) {
            continue;
        }
        if (
            ["integer", "float", "monetary"].includes(field.type) &&
            field.group_operator !== undefined
        ) {
            measures[fieldName] = field;
        }
    }

    // add active measures to the measure list.  This is very rarely
    // necessary, but it can be useful if one is working with a
    // functional field non stored, but in a model with an overridden
    // read_group method.  In this case, the pivot view could work, and
    // the measure should be allowed.  However, be careful if you define
    // a measure in your pivot view: non stored functional fields will
    // probably not work (their aggregate will always be 0).
    for (const measure of activeMeasures) {
        if (!measures[measure]) {
            measures[measure] = fields[measure];
        }
    }

    for (const fieldName in fieldAttrs) {
        if (fieldAttrs[fieldName].string && fieldName in measures) {
            measures[fieldName].string = fieldAttrs[fieldName].string;
        }
    }

    const sortedMeasures = Object.entries(measures).sort(([m1, f1], [m2, f2]) => {
        if (m1 === "__count" || m2 === "__count") {
            return m1 === "__count" ? 1 : -1; // Count is always last
        }
        return f1.string.toLowerCase().localeCompare(f2.string.toLowerCase());
    });

    return Object.fromEntries(sortedMeasures);
};

/**
 * @param {String} fieldName
 * @param {Object} rawAttrs
 * @param {Record} record
 * @returns {String}
 */
export function getFormattedValue(record, fieldName, attrs) {
    const field = record.fields[fieldName];
    const formatter = registry.category("formatters").get(field.type, (val) => val);
    const formatOptions = {
        escape: false,
        data: record.data,
        isPassword: "password" in attrs,
        digits: attrs.digits ? JSON.parse(attrs.digits) : field.digits,
        field: record.fields[fieldName],
    };
    return record.data[fieldName] !== undefined
        ? formatter(record.data[fieldName], formatOptions)
        : "";
}

/**
 * @param {Element} rootNode
 * @returns {ViewActiveActions}
 */
export function getActiveActions(rootNode) {
    const activeActions = {
        type: "view",
        edit: archParseBoolean(rootNode.getAttribute("edit"), true),
        create: archParseBoolean(rootNode.getAttribute("create"), true),
        delete: archParseBoolean(rootNode.getAttribute("delete"), true),
    };
    activeActions.duplicate =
        activeActions.create && archParseBoolean(rootNode.getAttribute("duplicate"), true);
    return activeActions;
}

export function getClassNameFromDecoration(decoration) {
    if (decoration === "bf") {
        return "fw-bold";
    } else if (decoration === "it") {
        return "fst-italic";
    }
    return `text-${decoration}`;
}

export function getDecoration(rootNode) {
    const decorations = [];
    for (const name of rootNode.getAttributeNames()) {
        if (name.startsWith("decoration-")) {
            decorations.push({
                class: getClassNameFromDecoration(name.replace("decoration-", "")),
                condition: rootNode.getAttribute(name),
            });
        }
    }
    return decorations;
}

/**
 * @param {any} field
 * @returns {boolean}
 */
export function isX2Many(field) {
    return field && X2M_TYPES.includes(field.type);
}

/**
 * @param {Object} field
 * @returns {boolean} true iff the given field is a numeric field
 */
export function isNumeric(field) {
    return NUMERIC_TYPES.includes(field.type);
}

/**
 * @param {any} value
 * @returns {boolean}
 */
export function isNull(value) {
    return [null, undefined].includes(value);
}

export function processButton(node) {
    const withDefault = {
        close: (val) => archParseBoolean(val, false),
        context: (val) => val || "{}",
    };
    const clickParams = {};
    for (const { name, value } of node.attributes) {
        if (BUTTON_CLICK_PARAMS.includes(name)) {
            clickParams[name] = withDefault[name] ? withDefault[name](value) : value;
        }
    }
    return {
        className: node.getAttribute("class") || "",
        disabled: !!node.getAttribute("disabled") || false,
        icon: node.getAttribute("icon") || false,
        title: node.getAttribute("title") || undefined,
        string: node.getAttribute("string") || undefined,
        options: JSON.parse(node.getAttribute("options") || "{}"),
        display: node.getAttribute("display") || "selection",
        clickParams,
        column_invisible: node.getAttribute("column_invisible"),
        invisible: combineModifiers(
            node.getAttribute("column_invisible"),
            node.getAttribute("invisible"),
            "OR"
        ),
        readonly: node.getAttribute("readonly"),
        required: node.getAttribute("required"),
    };
}

/**
 * In the preview implementation of reporting views, the virtual field used to
 * display the number of records was named __count__, whereas __count is
 * actually the one used in xml. So basically, activating a filter specifying
 * __count as measures crashed. Unfortunately, as __count__ was used in the JS,
 * all filters saved as favorite at that time were saved with __count__, and
 * not __count. So in order the make them still work with the new
 * implementation, we handle both __count__ and __count.
 *
 * This function replaces occurences of '__count__' by '__count' in the given
 * element(s).
 *
 * @param {any | any[]} [measures]
 * @returns {any}
 */
export function processMeasure(measure) {
    if (Array.isArray(measure)) {
        return measure.map(processMeasure);
    }
    return measure === "__count__" ? "__count" : measure;
}

/**
 * Transforms a string into a valid expression to be injected
 * in a template as a props via setAttribute.
 * Example: myString = `Some weird language quote (") `;
 *     should become in the template:
 *      <Component label="&quot;Some weird language quote (\\&quot;)&quot; " />
 *     which should be interpreted by owl as a JS expression being a string:
 *      `Some weird language quote (") `
 *
 * @param  {string} str The initial value: a pure string to be interpreted as such
 * @return {string}     the valid string to be injected into a component's node props.
 */
export function toStringExpression(str) {
    return `\`${str.replaceAll("`", "\\`")}\``;
}

/**
 * Generate a unique identifier (64 bits) in hexadecimal.
 *
 * @returns {string}
 */
export function uuid() {
    const array = new Uint8Array(8);
    window.crypto.getRandomValues(array);
    // Uint8Array to hex
    return [...array].map((b) => b.toString(16).padStart(2, "0")).join("");
}
