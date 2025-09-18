// @ts-check

/** @module @web/views/pivot/pivot_arch_parser - Parses pivot view XML arch into measures, row/column groupBy, and display flags */

/** Parser for `<pivot>` view architecture definitions. */
import { evaluateExpr } from "@web/core/py_js/py";
import { visitXML } from "@web/core/utils/dom/xml";
import { exprToBoolean } from "@web/core/utils/format/strings";
export class PivotArchParser {
    /**
     * Parse a pivot arch XML node into a structured descriptor.
     *
     * Extracts measures, row/column group-bys, default ordering, field
     * attributes, widgets, and display flags from `<pivot>` and `<field>`
     * elements.
     *
     * @param {Element} arch - the root `<pivot>` XML element
     * @returns {{
     *   activeMeasures: string[],
     *   colGroupBys: string[],
     *   defaultOrder: string | null,
     *   fieldAttrs: Object,
     *   rowGroupBys: string[],
     *   widgets: Object,
     *   title?: string,
     *   disableLinking?: boolean,
     *   displayQuantity?: boolean,
     * }}
     */
    parse(arch) {
        const archInfo = {
            activeMeasures: [], // store the defined active measures
            colGroupBys: [], // store the defined group_by used on cols
            defaultOrder: null,
            fieldAttrs: {},
            rowGroupBys: [], // store the defined group_by used on rows
            widgets: {}, // wigdets defined in the arch
        };

        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "pivot": {
                    if (node.hasAttribute("disable_linking")) {
                        archInfo.disableLinking = exprToBoolean(
                            node.getAttribute("disable_linking"),
                        );
                    }
                    if (node.hasAttribute("default_order")) {
                        archInfo.defaultOrder = node.getAttribute("default_order");
                    }
                    if (node.hasAttribute("string")) {
                        archInfo.title = node.getAttribute("string");
                    }
                    if (node.hasAttribute("display_quantity")) {
                        archInfo.displayQuantity = exprToBoolean(
                            node.getAttribute("display_quantity"),
                        );
                    }
                    break;
                }
                case "field": {
                    let fieldName = node.getAttribute("name"); // exists (rng validation)

                    archInfo.fieldAttrs[fieldName] = {};
                    if (node.hasAttribute("string")) {
                        archInfo.fieldAttrs[fieldName].string =
                            node.getAttribute("string");
                    }
                    if (
                        node.getAttribute("invisible") === "True" ||
                        node.getAttribute("invisible") === "1"
                    ) {
                        archInfo.fieldAttrs[fieldName].isInvisible = true;
                        break;
                    }
                    for (const { name, value } of node.attributes) {
                        if (
                            [
                                "name",
                                "type",
                                "operator",
                                "interval",
                                "string",
                                "widget",
                            ].includes(name)
                        ) {
                            continue;
                        }
                        if (name === "options") {
                            archInfo.fieldAttrs[fieldName].options =
                                evaluateExpr(value);
                        } else {
                            archInfo.fieldAttrs[fieldName][name] = value;
                        }
                    }

                    if (node.hasAttribute("interval")) {
                        fieldName += `:${node.getAttribute("interval")}`;
                    }
                    if (node.hasAttribute("widget")) {
                        archInfo.widgets[fieldName] = node.getAttribute("widget");
                    }
                    if (
                        node.getAttribute("type") === "measure" ||
                        node.hasAttribute("operator")
                    ) {
                        archInfo.activeMeasures.push(fieldName);
                    }
                    if (node.getAttribute("type") === "col") {
                        archInfo.colGroupBys.push(fieldName);
                    }
                    if (node.getAttribute("type") === "row") {
                        archInfo.rowGroupBys.push(fieldName);
                    }
                    break;
                }
            }
        });

        return archInfo;
    }
}
