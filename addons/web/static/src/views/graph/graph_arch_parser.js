/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import { XMLParser } from "@web/core/utils/xml";
import { archParseBoolean } from "../helpers/utils";

const MODES = ["bar", "line", "pie"];
const ORDERS = ["ASC", "DESC", "asc", "desc", null];

export class GraphArchParser extends XMLParser {
    parse(arch, fields = {}) {
        const archInfo = { fields, fieldAttrs: {}, groupBy: [] };
        this.visitXML(arch, (node) => {
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
                    let fieldName = node.getAttribute("name"); // exists (rng validation)
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
                    const isInvisible = Boolean(
                        evaluateExpr(node.getAttribute("invisible") || "0")
                    );
                    if (isInvisible) {
                        if (!archInfo.fieldAttrs[fieldName]) {
                            archInfo.fieldAttrs[fieldName] = {};
                        }
                        archInfo.fieldAttrs[fieldName].isInvisible = true;
                        break;
                    }
                    const isMeasure = node.getAttribute("type") === "measure";
                    if (isMeasure) {
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
