/** @odoo-module */

import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { archParseBoolean, getActiveActions } from "@web/views/utils";

export class HierarchyArchParser {
    parse(xmlDoc, models, modelName) {
        const archInfo = {
            activeActions: getActiveActions(xmlDoc),
            draggable: false,
            icon: "fa-share-alt o_hierarchy_icon",
            parentFieldName: "parent_id",
            fieldNodes: {},
            templateDocs: {},
            xmlDoc,
        };
        const fieldNextIds = {};
        const fields = models[modelName];

        visitXML(xmlDoc, (node) => {
            if (node.hasAttribute("t-name")) {
                archInfo.templateDocs[node.getAttribute("t-name")] = node;
                return;
            }
            if (node.tagName === "hierarchy") {
                if (node.hasAttribute("parent_field")) {
                    const parentFieldName = node.getAttribute("parent_field");
                    if (!(parentFieldName in fields)) {
                        throw new Error(`The parent field set (${parentFieldName}) is not defined in the model (${modelName}).`);
                    } else if (fields[parentFieldName].type !== "many2one") {
                        throw new Error(`Invalid parent field, it should be a Many2One field.`);
                    } else if (fields[parentFieldName].relation !== modelName) {
                        throw new Error(`Invalid parent field, the co-model should be same model than the current one (expected: ${modelName}).`);
                    }
                    archInfo.parentFieldName = parentFieldName;
                }
                if (node.hasAttribute("child_field")) {
                    const childFieldName = node.getAttribute("child_field");
                    if (!(childFieldName in fields)) {
                        throw new Error(`The child field set (${childFieldName}) is not defined in the model (${modelName}).`);
                    } else if (fields[childFieldName].type !== "one2many") {
                        throw new Error(`Invalid child field, it should be a One2Many field.`);
                    } else if (fields[childFieldName].relation !== modelName) {
                        throw new Error(`Invalid child field, the co-model should be same model than the current one (expected: ${modelName}).`);
                    }
                    archInfo.childFieldName = childFieldName;
                }
                if (node.hasAttribute("draggable")) {
                    archInfo.draggable = archParseBoolean(node.getAttribute("draggable"));
                }
                if (node.hasAttribute("icon")) {
                    archInfo.icon = node.getAttribute("icon");
                }
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "hierarchy");
                const name = fieldInfo.name;
                if (!(name in fieldNextIds)) {
                    fieldNextIds[name] = 0;
                }
                const fieldId = `${name}_${fieldNextIds[name]++}`;
                archInfo.fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
            }
        });

        const cardDoc = archInfo.templateDocs["hierarchy-box"];
        if (!cardDoc) {
            throw new Error("Missing 'hierarchy-box' template.");
        }

        return archInfo;
    }
}
