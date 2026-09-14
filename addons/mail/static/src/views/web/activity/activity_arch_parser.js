// @ts-check
/** @odoo-module native */
import { deepCopy } from "@web/core/utils/collections/objects";
import { parseFieldNode } from "@web/views/field_arch";
import { irToElement, literalNbsp } from "@web/views/ir/view_ir";
import { irParents, ViewArchParser, visitIR } from "@web/views/view_arch_parser";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").ActivityActivityAttrs} ActivityAttrs
 */

export class ActivityArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * The parent of every node of the tree the last `parse()` walked.
     * @type {Map<ViewIRNode, ViewIRNode | null>}
     */
    parents = new Map();

    /**
     * The `field_id` annotations go on the parser's own copy of the tree;
     * the `templateDocs` the renderer compiles are that copy materialised.
     *
     * @param {ViewIRNode | Element | string} arch
     * @param {Object<string, Object>} models
     * @param {string} modelName
     * @returns {Object}
     */
    parse(arch, models, modelName) {
        const ir = deepCopy(this.toIR(arch));
        /** @type {ActivityAttrs} */
        const attrs = ir.attrs || {};
        const jsClass = attrs.js_class;
        const title = attrs.string ?? null;

        const fieldNodes = {};
        const fieldNextIds = {};
        this.parents = irParents(ir);

        visitIR(ir, (node) => {
            if (node.attrs?.["t-name"] !== undefined) {
                return;
            }

            if (node.kind === "field") {
                const fieldInfo = parseFieldNode(
                    node,
                    models,
                    modelName,
                    "activity",
                    jsClass,
                );
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                (node.attrs ??= {}).field_id = fieldId;
            }

            if (node.kind === "img") {
                const attSrc = node.attrs?.["t-att-src"];
                if (
                    attSrc &&
                    /\bactivity_image\b/.test(attSrc) &&
                    !Object.values(fieldNodes).some((f) => f.name === "write_date")
                ) {
                    fieldNodes.write_date_0 = {
                        name: "write_date",
                        type: "datetime",
                    };
                }
            }
        });
        const xmlDoc = irToElement(ir, { text: literalNbsp });
        /** @type {Record<string, Element>} */
        const templateDocs = {};
        for (const templateDoc of xmlDoc.querySelectorAll("[t-name]")) {
            templateDocs[/** @type {string} */ (templateDoc.getAttribute("t-name"))] =
                templateDoc;
        }
        return {
            fieldNodes,
            templateDocs,
            title,
        };
    }
}
