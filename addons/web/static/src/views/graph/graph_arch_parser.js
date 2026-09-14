// @ts-check
/** @odoo-module native */

import { exprToBoolean } from "@web/core/utils/format/strings";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import {
    irAttribute,
    requiredIRAttribute,
    staticModifier,
    ViewArchParser,
} from "@web/views/view_arch_parser";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").GraphGraphAttrs} GraphAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").GraphFieldAttrs} GraphFieldAttrs
 */

const MODES = ["bar", "line", "pie", "scatter"];
const ORDERS = ["ASC", "DESC", "asc", "desc", null];

export class GraphArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * @param {ViewIRNode | Element | string} arch
     * @param {Record<string, any>} [models]
     * @param {string} [modelName]
     * @returns {{
     * fields: Object,
     * fieldAttrs: Object,
     * groupBy: string[],
     * measures: string[],
     * measure?: string,
     * mode?: string,
     * order?: string,
     * title?: string,
     * stacked?: boolean,
     * cumulated?: boolean,
     * cumulatedStart?: boolean,
     * disableLinking?: boolean,
     * }}
     */
    parse(arch, models, modelName) {
        const fields = (modelName && models?.[modelName]?.fields) || {};
        return this.visitIR(
            this.toIR(arch),
            /** @type {any} */ ({ fields, fieldAttrs: {}, groupBy: [], measures: [] }),
            { graph: this.parseRootNode, field: this.parseFieldNode },
        );
    }

    /**
     * @param {ViewIRNode} node
     * @param {any} archInfo
     */
    parseRootNode(node, archInfo) {
        /** @type {GraphAttrs} */
        const attrs = node.attrs || {};
        for (const [attr, key] of /** @type {const} */ ([
            ["disable_linking", "disableLinking"],
            ["stacked", "stacked"],
            ["cumulated", "cumulated"],
            ["cumulated_start", "cumulatedStart"],
        ])) {
            if (attr in attrs) {
                archInfo[key] = exprToBoolean(attrs[attr]);
            }
        }
        if (attrs.type && MODES.includes(attrs.type)) {
            archInfo.mode = attrs.type;
        }
        if (attrs.order && ORDERS.includes(attrs.order)) {
            archInfo.order = attrs.order.toUpperCase();
        }
        if (attrs.string) {
            archInfo.title = attrs.string;
        }
    }

    /**
     * @param {ViewIRNode} node
     * @param {any} archInfo
     */
    parseFieldNode(node, archInfo) {
        const fieldName = requiredIRAttribute(node, "name");
        if (fieldName === "id") {
            return;
        }
        /** @type {GraphFieldAttrs} */
        const attrs = node.attrs || {};
        /**
         * @param {string} key
         * @param {any} value
         */
        const setAttr = (key, value) => {
            archInfo.fieldAttrs[fieldName] ??= {};
            archInfo.fieldAttrs[fieldName][key] = value;
        };

        if (attrs.string) {
            setAttr("string", attrs.string);
        }
        if (attrs.widget) {
            setAttr("widget", attrs.widget);
        }
        const invisible = irAttribute(node, "invisible");
        const hidden = staticModifier(invisible);
        if (hidden) {
            setAttr("isInvisible", true);
            return;
        }
        if (hidden === undefined) {
            setAttr("invisible", invisible);
        }

        if (attrs.type === "measure") {
            archInfo.measures.push(fieldName);
            archInfo.measure = fieldName;
            return;
        }
        const { type } = archInfo.fields[fieldName];
        if (GROUPABLE_TYPES.includes(type)) {
            archInfo.groupBy.push(
                attrs.interval ? `${fieldName}:${attrs.interval}` : fieldName,
            );
        }
    }
}
