// @ts-check
/** @odoo-module native */

import { exprToBoolean } from "@web/core/utils/format/strings";
import { combineModifiers } from "@web/model/relational_model";
import { nodeAttrs } from "@web/views/ir/view_ir";

/** @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode */

export const BUTTON_MODIFIERS = [
    "invisible",
    "column_invisible",
    "readonly",
    "required",
];

export const BUTTON_PRESENTATION = [
    "class",
    "string",
    "icon",
    "title",
    "display",
    "options",
    "disabled",
];

export const BUTTON_CLICK_PARAMS = [
    "name",
    "type",
    "args",
    "block-ui",
    "context",
    "close",
    "cancel-label",
    "confirm",
    "confirm-title",
    "confirm-label",
    "special",
    "effect",
    "help",
    "debounce",
    "noSaveDialog",
];

/**
 * @param {Record<string, string>} attrs
 * @returns {Object}
 */
function parseButtonOptions(attrs) {
    const raw = attrs.options || "{}";
    try {
        return JSON.parse(raw);
    } catch (e) {
        throw new Error(`Invalid JSON in button "options" attribute: ${raw}`, {
            cause: e,
        });
    }
}

/**
 * @param {ViewIRNode | Element} node
 * @returns {{ className: string, disabled: boolean, icon: string|false, title: string|undefined, string: string|undefined, options: Object, display: string, clickParams: Object, column_invisible: string|null, invisible: string|boolean|null|undefined, readonly: string|null, required: string|null, modifiers: Object, attrs: Object }}
 */
export function processButton(node) {
    const nodeAttributes = nodeAttrs(node);
    /** @type {Record<string, (val: string) => any>} */
    const withDefault = {
        close: (val) => exprToBoolean(val, false),
        context: (val) => val || "{}",
    };
    /** @type {Record<string, any>} */
    const clickParams = {};
    /** @type {Record<string, any>} */
    const attrs = {};
    /** @type {Record<string, any>} */
    const modifiers = {};
    for (const [name, value] of Object.entries(nodeAttributes)) {
        if (BUTTON_CLICK_PARAMS.includes(name)) {
            clickParams[name] = withDefault[name] ? withDefault[name](value) : value;
        } else if (BUTTON_MODIFIERS.includes(name)) {
            modifiers[name] = value;
        } else if (!BUTTON_PRESENTATION.includes(name)) {
            attrs[name] = value;
        }
    }
    return {
        modifiers,
        className: nodeAttributes.class || "",
        disabled: exprToBoolean(nodeAttributes.disabled),
        icon: nodeAttributes.icon || false,
        title: nodeAttributes.title || undefined,
        string: nodeAttributes.string || undefined,
        options: parseButtonOptions(nodeAttributes),
        display: nodeAttributes.display || "selection",
        clickParams,
        column_invisible: nodeAttributes.column_invisible ?? null,
        invisible: combineModifiers(
            nodeAttributes.column_invisible ?? null,
            nodeAttributes.invisible ?? null,
            "OR",
        ),
        readonly: nodeAttributes.readonly ?? null,
        required: nodeAttributes.required ?? null,
        attrs,
    };
}
