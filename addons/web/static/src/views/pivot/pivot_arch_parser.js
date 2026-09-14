// @ts-check
/** @odoo-module native */

import { evaluateExpr } from "@web/core/py_js/py";
import { exprToBoolean } from "@web/core/utils/format/strings";
import {
    irAttribute,
    requiredIRAttribute,
    staticModifier,
    ViewArchParser,
} from "@web/views/view_arch_parser";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").PivotPivotAttrs} PivotAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").PivotFieldAttrs} PivotFieldAttrs
 */

/** @type {string[]} */
const PIVOT_FIELD_ATTRS = ["name", "type", "operator", "interval", "string", "widget"];

export class PivotArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * @param {ViewIRNode | Element | string} arch
     * @param {Record<string, any>} [_models]
     * @param {string} [_modelName]
     * @returns {{
     * activeMeasures: string[],
     * colGroupBys: string[],
     * defaultOrder: string | null,
     * fieldAttrs: Record<string, Record<string, any>>,
     * rowGroupBys: string[],
     * widgets: Object,
     * title?: string,
     * disableLinking?: boolean,
     * displayQuantity?: boolean,
     * }}
     */
    parse(arch, _models, _modelName) {
        return this.visitIR(
            this.toIR(arch),
            /** @type {any} */ ({
                activeMeasures: [],
                colGroupBys: [],
                defaultOrder: null,
                fieldAttrs: {},
                rowGroupBys: [],
                widgets: {},
            }),
            { pivot: this.parseRootNode, field: this.parseFieldNode },
        );
    }

    /**
     * @param {ViewIRNode} node
     * @param {any} archInfo
     */
    parseRootNode(node, archInfo) {
        /** @type {PivotAttrs} */
        const attrs = node.attrs || {};
        if (attrs.disable_linking !== undefined) {
            archInfo.disableLinking = exprToBoolean(attrs.disable_linking);
        }
        if (attrs.default_order !== undefined) {
            archInfo.defaultOrder = attrs.default_order;
        }
        if (attrs.string !== undefined) {
            archInfo.title = attrs.string;
        }
        if (attrs.display_quantity !== undefined) {
            archInfo.displayQuantity = exprToBoolean(attrs.display_quantity);
        }
    }

    /**
     * @param {ViewIRNode} node
     * @param {any} archInfo
     */
    parseFieldNode(node, archInfo) {
        const name = requiredIRAttribute(node, "name");
        /** @type {PivotFieldAttrs} */
        const nodeAttrs = node.attrs || {};
        const attrs = (archInfo.fieldAttrs[name] ??= {});
        if (nodeAttrs.string !== undefined) {
            attrs.string = nodeAttrs.string;
        }
        if (staticModifier(irAttribute(node, "invisible"))) {
            attrs.isInvisible = true;
            return;
        }
        for (const [attribute, value] of Object.entries(nodeAttrs)) {
            if (PIVOT_FIELD_ATTRS.includes(attribute)) {
                continue;
            }
            attrs[attribute] = attribute === "options" ? evaluateExpr(value) : value;
        }

        const groupBy = nodeAttrs.interval ? `${name}:${nodeAttrs.interval}` : name;
        if (nodeAttrs.widget !== undefined) {
            archInfo.widgets[groupBy] = nodeAttrs.widget;
        }
        const type = nodeAttrs.type;
        if (type === "measure" || nodeAttrs.operator !== undefined) {
            archInfo.activeMeasures.push(groupBy);
        }
        if (type === "col") {
            archInfo.colGroupBys.push(groupBy);
        }
        if (type === "row") {
            archInfo.rowGroupBys.push(groupBy);
        }
    }
}
