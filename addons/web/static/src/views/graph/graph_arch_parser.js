/** @odoo-module **/

import { visitXML } from "@web/core/utils/xml";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import { archParseBoolean } from "@web/views/utils";

const MODES = ["bar", "line", "pie"];
const ORDERS = ["ASC", "DESC", "asc", "desc", null];

export class GraphArchParser {
    parse(arch, fields = {}) {
        const archInfo = { fields, fieldAttrs: {}, groupBy: [], measures: [] };
        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "graph": {
                    if (node.hasAttribute("disable_linking")) {
                        archInfo.disableLinking = archParseBoolean(
                            node.getAttribute("disable_linking")
                        );
                    }
                    if (node.hasAttribute("stacked")) {
                        archInfo.stacked = archParseBoolean(node.getAttribute("stacked"));
                    }
                    if (node.hasAttribute("cumulated")) {
                        archInfo.cumulated = archParseBoolean(node.getAttribute("cumulated"));
                    }
                    if (node.hasAttribute("cumulated_start")) {
                        archInfo.cumulatedStart = archParseBoolean(
                            node.getAttribute("cumulated_start")
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
