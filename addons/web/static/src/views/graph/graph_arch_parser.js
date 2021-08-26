/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
import { XMLParser } from "@web/core/utils/xml";
import { archParseBoolean } from "../helpers/utils";

export const MODES = ["bar", "line", "pie"];
export const ORDERS = ["ASC", "DESC", null];

export class GraphArchParser extends XMLParser {
    parse(arch, fields = {}) {
        const metaData = { fields, fieldModif: {}, groupBy: [] };
        this.visitXML(arch, (node) => {
            switch (node.tagName) {
                case "graph":
                    if (node.hasAttribute("disable_linking")) {
                        metaData.disableLinking = archParseBoolean(
                            node.getAttribute("disable_linking")
                        );
                    }
                    if (node.hasAttribute("stacked")) {
                        metaData.stacked = archParseBoolean(node.getAttribute("stacked"));
                    }
                    const mode = node.getAttribute("type");
                    if (mode && MODES.includes(mode)) {
                        metaData.mode = mode;
                    }
                    const order = node.getAttribute("order");
                    if (order && ORDERS.includes(order)) {
                        metaData.order = order;
                    }
                    const title = node.getAttribute("string");
                    if (title) {
                        metaData.title = title;
                    }
                    break;
                case "field":
                    let fieldName = node.getAttribute("name"); // exists (rng validation)
                    if (fieldName === "id") {
                        break;
                    }
                    const string = node.getAttribute("string");
                    if (string) {
                        if (!metaData.fieldModif[fieldName]) {
                            metaData.fieldModif[fieldName] = {};
                        }
                        metaData.fieldModif[fieldName].string = string;
                    }
                    const isInvisible = Boolean(
                        evaluateExpr(node.getAttribute("invisible") || "0")
                    );
                    if (isInvisible) {
                        if (!metaData.fieldModif[fieldName]) {
                            metaData.fieldModif[fieldName] = {};
                        }
                        metaData.fieldModif[fieldName].isInvisible = true;
                        break;
                    }
                    const isMeasure = node.getAttribute("type") === "measure";
                    if (isMeasure) {
                        // the last field with type="measure" (if any) will be used as measure else __count
                        metaData.measure = fieldName;
                    } else {
                        const { type } = metaData.fields[fieldName]; // exists (rng validation)
                        if (GROUPABLE_TYPES.includes(type)) {
                            let groupBy = fieldName;
                            const interval = node.getAttribute("interval");
                            if (interval) {
                                groupBy += `:${interval}`;
                            }
                            metaData.groupBy.push(groupBy);
                        }
                    }
                    break;
            }
        });
        return metaData;
    }
}
