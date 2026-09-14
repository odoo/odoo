// @ts-check
/** @odoo-module native */

import { isX2ManyType } from "@web/core/field_types";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { getFieldFromRegistry, getSupportedOptionNames } from "@web/fields/field";
import { utils } from "@web/ui/viewport";
import { elementToIR, irToElement, isMarkup, literalNbsp } from "@web/views/ir/view_ir";

/** @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode */

const isSmall = utils.isSmall;
const viewRegistry = registry.category("views");

const FRAMEWORK_FIELD_OPTIONS = new Set(["group_by_tooltip"]);

/** @type {Set<string>} */
const warnedUnknownOptions = new Set();

export function resetUnknownOptionWarnings() {
    warnedUnknownOptions.clear();
}

/**
 * @param {string} widget
 * @param {ReturnType<typeof getFieldFromRegistry>} field
 * @param {Record<string, unknown>} options
 */
function warnUnknownOptions(widget, field, options) {
    const supported = getSupportedOptionNames(field);
    if (!supported) {
        return;
    }
    const unknown = Object.keys(options).filter(
        (name) => !supported.has(name) && !FRAMEWORK_FIELD_OPTIONS.has(name),
    );
    if (!unknown.length) {
        return;
    }
    const key = `${widget}|${unknown.join(",")}`;
    if (warnedUnknownOptions.has(key)) {
        return;
    }
    warnedUnknownOptions.add(key);
    console.warn(
        `[field_arch] widget "${widget}" does not support option(s) ` +
            `${unknown.map((n) => `"${n}"`).join(", ")}; they are ignored. ` +
            `Supported: ${[...supported].join(", ") || "(none)"}.`,
    );
}

/**
 * @param {ViewIRNode} node
 * @param {Record<string, any>} fieldInfo
 * @param {Record<string, any>} models
 * @param {{ relation?: string, [k: string]: any }} field
 */
function parseX2ManyViews(node, fieldInfo, models, field) {
    const views = {};
    let relatedFields = fieldInfo.field.relatedFields;
    if (relatedFields) {
        if (relatedFields instanceof Function) {
            relatedFields = relatedFields(fieldInfo);
        }
        const relatedFieldsArr = /** @type {any[]} */ (relatedFields);
        for (const relatedField of relatedFieldsArr) {
            if (!("readonly" in relatedField)) {
                relatedField.readonly = true;
            }
        }
        relatedFields = Object.fromEntries(relatedFieldsArr.map((f) => [f.name, f]));
        views.default = {
            fieldNodes: relatedFields,
            fields: relatedFields,
        };
        if (!fieldInfo.field.useSubView) {
            fieldInfo.viewMode = "default";
        }
    }
    const relation = /** @type {string} */ (field.relation);
    for (const child of node.children || []) {
        if (isMarkup(child)) {
            continue;
        }
        const viewType = child.kind;
        const { ArchParser } =
            /** @type {{ ArchParser: { consumes?: string, new (): { parse: (n: ViewIRNode | Element, m: any, r?: string) => any } } }} */ (
                viewRegistry.get(viewType)
            );
        // a sub-view parser still on the element gets a fresh element built
        // from the child node; one on the IR gets the node itself
        const subArch =
            ArchParser.consumes === "ir"
                ? child
                : irToElement(child, { text: literalNbsp });
        const archInfo = new ArchParser().parse(subArch, models, relation);
        views[viewType] = {
            ...archInfo,
            limit: archInfo.limit || 40,
            fields: models[relation].fields,
        };
    }

    let viewMode = node.attrs?.mode ?? null;
    if (viewMode) {
        if (viewMode.split(",").length !== 1) {
            viewMode = isSmall() ? "kanban" : "list";
        }
    } else {
        if (views.list && !views.kanban) {
            viewMode = "list";
        } else if (!views.list && views.kanban) {
            viewMode = "kanban";
        } else if (views.list && views.kanban) {
            viewMode = isSmall() ? "kanban" : "list";
        }
    }
    if (viewMode) {
        fieldInfo.viewMode = viewMode;
    }
    if (Object.keys(views).length) {
        fieldInfo.relatedFields = models[relation]?.fields;
        fieldInfo.views = views;
    }
}

/** @param {Record<string, any>} fieldInfo */
function parseMany2OneViews(fieldInfo) {
    /** @type {any} */
    let relatedFields = fieldInfo.field.relatedFields;
    if (!relatedFields) {
        return;
    }
    relatedFields = Object.fromEntries(relatedFields.map((f) => [f.name, f]));
    fieldInfo.viewMode = "default";
    fieldInfo.views = {
        default: {
            fieldNodes: relatedFields,
            fields: relatedFields,
        },
    };
}

/**
 * The field node as the view IR; a parser still walking the element hands
 * its `<field>` over and it is converted here, nested sub-views included.
 *
 * @param {ViewIRNode | Element} archNode
 * @param {Record<string, { fields: Record<string, { type: string, string?: string, relation?: string, readonly?: boolean, [k: string]: any }> }>} models
 * @param {string} modelName
 * @param {string} viewType
 * @param {string} [jsClass]
 * @returns {{ name: string, type: string, viewType: string, widget: string | null, field: ReturnType<typeof getFieldFromRegistry>, context: string, string?: string, help?: string, onChange: boolean, forceSave: boolean, options: Object, decorations: Record<string, string>, attrs: Record<string, string>, domain?: string, readonly?: string | null, required?: string | null, invisible?: string | null, column_invisible?: string | null, viewMode?: string, views?: Object, relatedFields?: Object, isHandle?: boolean }}
 */
export function parseFieldNode(archNode, models, modelName, viewType, jsClass) {
    const node = "kind" in archNode ? archNode : elementToIR(archNode);
    const attrs = node.attrs || {};
    const name = /** @type {string} */ (attrs.name);
    const widget = attrs.widget ?? null;
    const fields = models[modelName].fields;
    if (!fields[name]) {
        throw new Error(`"${modelName}"."${name}" field is undefined.`);
    }
    const field = getFieldFromRegistry(
        fields[name].type,
        widget ?? undefined,
        viewType,
        jsClass,
    );
    const fieldInfo = {
        name,
        type: fields[name].type,
        viewType,
        widget,
        field,
        context: "{}",
        string: fields[name].string,
        help: undefined,
        onChange: false,
        forceSave: false,
        options: {},
        decorations: {},
        attrs: {},
        domain: undefined,
    };

    for (const attr of ["invisible", "column_invisible", "readonly", "required"]) {
        fieldInfo[attr] = attrs[attr] ?? null;
        if (fieldInfo[attr] === "True" || fieldInfo[attr] === "1") {
            if (attr === "column_invisible") {
                fieldInfo.invisible = "True";
            }
        } else if (fieldInfo[attr] === null && fields[name][attr]) {
            fieldInfo[attr] = "True";
        }
    }

    for (const [name, value] of Object.entries(attrs)) {
        if (["name", "widget"].includes(name)) {
            continue;
        }
        if (["context", "string", "help", "domain"].includes(name)) {
            fieldInfo[name] = value;
        } else if (name === "on_change") {
            fieldInfo.onChange = exprToBoolean(value);
        } else if (name === "options") {
            fieldInfo.options = evaluateExpr(value);
        } else if (name === "force_save") {
            fieldInfo.forceSave = exprToBoolean(value);
        } else if (name.startsWith("decoration-")) {
            fieldInfo.decorations[name.replace("decoration-", "")] = value;
        } else if (!name.startsWith("t-att")) {
            fieldInfo.attrs[name] = value;
        }
    }
    if (name === "id") {
        fieldInfo.readonly = "True";
    }

    if (odoo.debug && widget && Object.keys(fieldInfo.options).length) {
        warnUnknownOptions(widget, field, fieldInfo.options);
    }

    if (widget === "handle") {
        fieldInfo.isHandle = true;
    }

    if (isX2ManyType(fields[name].type)) {
        parseX2ManyViews(node, fieldInfo, models, fields[name]);
    }
    if (["many2one", "many2one_reference"].includes(fields[name].type)) {
        parseMany2OneViews(fieldInfo);
    }

    return fieldInfo;
}
