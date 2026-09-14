// @ts-check
/** @odoo-module native */
import { deepCopy } from "@web/core/utils/collections/objects";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { stringToOrderBy } from "@web/core/utils/order_by";
import { parseFieldNode } from "@web/views/field_arch";
import { irToElement, literalNbsp } from "@web/views/ir/view_ir";
import { irParents, ViewArchParser, visitIR } from "@web/views/view_arch_parser";
import { getActiveActions } from "@web/views/view_utils";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").HierarchyHierarchyAttrs} HierarchyAttrs
 */

export class HierarchyArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * The parent of every node of the tree the last `parse()` walked.
     * @type {Map<ViewIRNode, ViewIRNode | null>}
     */
    parents = new Map();

    /**
     * The `field_id` annotations go on the parser's own copy of the tree;
     * `xmlDoc` and the `templateDocs` the renderer compiles are that copy
     * materialised.
     *
     * @param {ViewIRNode | Element | string} arch
     * @param {Record<string, any>} models
     * @param {string} modelName
     * @returns {Record<string, any>}
     */
    parse(arch, models, modelName) {
        const ir = deepCopy(this.toIR(arch));
        /** @type {HierarchyAttrs} */
        const attrs = ir.attrs || {};
        /** @type {Record<string, any>} */
        const archInfo = {
            activeActions: getActiveActions(ir),
            defaultOrder: stringToOrderBy(attrs.default_order || null),
            draggable: false,
            icon: "fa-share-alt fa-rotate-90 align-text-top",
            parentFieldName: "parent_id",
            fieldNodes: {},
            templateDocs: {},
        };
        /** @type {Record<string, number>} */
        const fieldNextIds = {};
        const fields = models[modelName].fields;
        this.parents = irParents(ir);

        visitIR(ir, (node) => {
            if (node.attrs?.["t-name"] !== undefined) {
                return;
            }
            if (node.kind === "hierarchy") {
                const parentFieldName = attrs.parent_field;
                if (parentFieldName !== undefined) {
                    if (!(parentFieldName in fields)) {
                        throw new Error(
                            `The parent field set (${parentFieldName}) is not defined in the model (${modelName}).`,
                        );
                    } else if (fields[parentFieldName].type !== "many2one") {
                        throw new Error(
                            `Invalid parent field, it should be a Many2One field.`,
                        );
                    } else if (fields[parentFieldName].relation !== modelName) {
                        throw new Error(
                            `Invalid parent field, the co-model should be same model than the current one (expected: ${modelName}).`,
                        );
                    }
                    archInfo.parentFieldName = parentFieldName;
                }
                const childFieldName = attrs.child_field;
                if (childFieldName !== undefined) {
                    if (!(childFieldName in fields)) {
                        throw new Error(
                            `The child field set (${childFieldName}) is not defined in the model (${modelName}).`,
                        );
                    } else if (fields[childFieldName].type !== "one2many") {
                        throw new Error(
                            `Invalid child field, it should be a One2Many field.`,
                        );
                    } else if (fields[childFieldName].relation !== modelName) {
                        throw new Error(
                            `Invalid child field, the co-model should be same model than the current one (expected: ${modelName}).`,
                        );
                    }
                    archInfo.childFieldName = childFieldName;
                }
                if (attrs.draggable !== undefined) {
                    archInfo.draggable = exprToBoolean(attrs.draggable);
                }
                if (attrs.icon !== undefined) {
                    archInfo.icon = attrs.icon;
                }
            } else if (node.kind === "field") {
                const fieldInfo = parseFieldNode(node, models, modelName, "hierarchy");
                const name = fieldInfo.name;
                if (!(name in fieldNextIds)) {
                    fieldNextIds[name] = 0;
                }
                const fieldId = `${name}_${fieldNextIds[name]++}`;
                archInfo.fieldNodes[fieldId] = fieldInfo;
                (node.attrs ??= {}).field_id = fieldId;
            }
        });

        const xmlDoc = irToElement(ir, { text: literalNbsp });
        for (const templateDoc of xmlDoc.querySelectorAll("[t-name]")) {
            archInfo.templateDocs[
                /** @type {string} */ (templateDoc.getAttribute("t-name"))
            ] = templateDoc;
        }
        archInfo.xmlDoc = xmlDoc;

        if (!archInfo.templateDocs["hierarchy-box"]) {
            throw new Error("Missing 'hierarchy-box' template.");
        }

        return archInfo;
    }
}
