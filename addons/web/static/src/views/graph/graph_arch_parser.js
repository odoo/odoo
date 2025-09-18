// @ts-check

/** @module @web/views/graph/graph_arch_parser - Parses graph view XML arch into chart mode, measures, groupBy, and display flags */

import { visitXML } from "@web/core/utils/dom/xml";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";

const MODES = ["bar", "line", "pie"];
const ORDERS = ["ASC", "DESC", "asc", "desc", null];

/** Parser for `<graph>` view architecture definitions. */
export class GraphArchParser {
    /**
     * Parse a graph arch XML node into a structured descriptor.
     *
     * Extracts chart mode, stacking/cumulation flags, ordering, title,
     * measures and groupBy definitions from `<graph>` and `<field>` elements.
     *
     * @param {Element} arch - the root `<graph>` XML element
     * @param {Object} [fields={}] - field definitions keyed by field name
     * @returns {{
     *   fields: Object,
     *   fieldAttrs: Object,
     *   groupBy: string[],
     *   measures: string[],
     *   measure?: string,
     *   mode?: string,
     *   order?: string,
     *   title?: string,
     *   stacked?: boolean,
     *   cumulated?: boolean,
     *   cumulatedStart?: boolean,
     *   disableLinking?: boolean,
     * }}
     */
    parse(arch, fields = {}) {
        const archInfo = { fields, fieldAttrs: {}, groupBy: [], measures: [] };
        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "graph": {
                    if (node.hasAttribute("disable_linking")) {
                        archInfo.disableLinking = exprToBoolean(
                            node.getAttribute("disable_linking"),
                        );
                    }
                    if (node.hasAttribute("stacked")) {
                        archInfo.stacked = exprToBoolean(node.getAttribute("stacked"));
                    }
                    if (node.hasAttribute("cumulated")) {
                        archInfo.cumulated = exprToBoolean(
                            node.getAttribute("cumulated"),
                        );
                    }
                    if (node.hasAttribute("cumulated_start")) {
                        archInfo.cumulatedStart = exprToBoolean(
                            node.getAttribute("cumulated_start"),
                        );
                    }
                    const mode = node.getAttribute("type");
                    if (mode && MODES.includes(mode)) {
                        archInfo.mode = mode;
                    }
                    const order = node.getAttribute("order");
                    if (order && ORDERS.includes(order)) {
                        archInfo.order = order.toUpperCase();
                    }
                    const title = node.getAttribute("string");
                    if (title) {
                        archInfo.title = title;
                    }
                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name"); // exists (rng validation)
                    if (fieldName === "id") {
                        break;
                    }
                    const string = node.getAttribute("string");
                    if (string) {
                        if (!archInfo.fieldAttrs[fieldName]) {
                            archInfo.fieldAttrs[fieldName] = {};
                        }
                        archInfo.fieldAttrs[fieldName].string = string;
                    }
                    const widget = node.getAttribute("widget");
                    if (widget) {
                        if (!archInfo.fieldAttrs[fieldName]) {
                            archInfo.fieldAttrs[fieldName] = {};
                        }
                        archInfo.fieldAttrs[fieldName].widget = widget;
                    }
                    if (
                        node.getAttribute("invisible") === "True" ||
                        node.getAttribute("invisible") === "1"
                    ) {
                        if (!archInfo.fieldAttrs[fieldName]) {
                            archInfo.fieldAttrs[fieldName] = {};
                        }
                        archInfo.fieldAttrs[fieldName].isInvisible = true;
                        break;
                    }
                    const isMeasure = node.getAttribute("type") === "measure";
                    if (isMeasure) {
                        archInfo.measures.push(fieldName);
                        // the last field with type="measure" (if any) will be used as measure else __count
                        archInfo.measure = fieldName;
                    } else {
                        const { type } = archInfo.fields[fieldName]; // exists (rng validation)
                        if (GROUPABLE_TYPES.includes(type)) {
                            let groupBy = fieldName;
                            const interval = node.getAttribute("interval");
                            if (interval) {
                                groupBy += `:${interval}`;
                            }
                            archInfo.groupBy.push(groupBy);
                        }
                    }
                    break;
                }
            }
        });
        return archInfo;
    }
}
