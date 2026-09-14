// @ts-check
/** @odoo-module native */

import { deepCopy } from "@web/core/utils/collections/objects";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { parseFieldNode } from "@web/views/field_arch";
import { irToElement, literalNbsp } from "@web/views/ir/view_ir";
import { getActiveActions } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

import { irParents, ViewArchParser, visitIR } from "../view_arch_parser.js";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").FormFormAttrs} FormAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").FormFieldAttrs} FormFieldAttrs
 */

/**
 * @param {ViewIRNode} node
 * @param {string} name
 * @param {string} value
 */
function annotate(node, name, value) {
    (node.attrs ??= {})[name] = value;
}

export class FormArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * The parent of every node of the tree the last `parse()` walked — what
     * a subclass that locates a node in the arch (web studio's xpath) reads.
     * @type {Map<ViewIRNode, ViewIRNode | null>}
     */
    parents = new Map();

    /**
     * The tree the parser annotates (`field_id`, `widget_id`) is its own
     * copy; `xmlDoc` is that copy materialised for the compiler.
     *
     * @param {ViewIRNode | Element | string} arch
     * @param {Object} models
     * @param {string} modelName
     * @returns {{ activeActions: Record<string, any>, autofocusFieldIds: string[], disableAutofocus: boolean, fieldNodes: Object, widgetNodes: Object, xmlDoc: Element }}
     */
    parse(arch, models, modelName) {
        const ir = deepCopy(this.toIR(arch));
        /** @type {FormAttrs} */
        const attrs = ir.attrs || {};
        const jsClass = attrs.js_class;
        const disableAutofocus = exprToBoolean(attrs.disable_autofocus || "");
        const activeActions = getActiveActions(ir);
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const fieldNextIds = {};
        const autofocusFieldIds = [];
        this.parents = irParents(ir);
        visitIR(ir, (node) => {
            if (node.kind === "field") {
                /** @type {FormFieldAttrs} */
                const fieldAttrs = node.attrs || {};
                const fieldInfo = parseFieldNode(
                    node,
                    models,
                    modelName,
                    "form",
                    jsClass,
                );
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                annotate(node, "field_id", fieldId);
                if (exprToBoolean(fieldAttrs.default_focus || "")) {
                    autofocusFieldIds.push(fieldId);
                }
                if (fieldInfo.type === "properties") {
                    /** @type {any} */ (activeActions).addPropertyFieldValue = true;
                }
                return false;
            } else if (node.kind === "widget") {
                const widgetInfo = Widget.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                annotate(node, "widget_id", widgetId);
            }
        });
        return {
            activeActions,
            autofocusFieldIds,
            disableAutofocus,
            fieldNodes,
            widgetNodes,
            xmlDoc: irToElement(ir, { text: literalNbsp }),
        };
    }
}
