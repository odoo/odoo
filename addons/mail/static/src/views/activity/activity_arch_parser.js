/** @odoo-module */

import { addFieldDependencies } from "@web/views/utils";
import { Field } from "@web/views/fields/field";
import { XMLParser } from "@web/core/utils/xml";

export class ActivityArchParser extends XMLParser {
    parse(arch, models, modelName) {
        const xmlDoc = this.parseXML(arch);
        const jsClass = xmlDoc.getAttribute("js_class");
        const title = xmlDoc.getAttribute("string");

        const fieldNodes = {};
        const templateDocs = {};
        const fieldNextIds = {};
        const activeFields = {};

        this.visitXML(xmlDoc, (node) => {
            if (node.hasAttribute("t-name")) {
                templateDocs[node.getAttribute("t-name")] = node;
                return;
            }

            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(
                    node,
                    models,
                    modelName,
                    "activity",
                    jsClass
                );
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);

                addFieldDependencies(fieldInfo, activeFields, models[modelName]);
            }

            // Keep track of last update so images can be reloaded when they may have changed.
            if (node.tagName === "img") {
                const attSrc = node.getAttribute("t-att-src");
                if (
                    attSrc &&
                    /\bactivity_image\b/.test(attSrc) &&
                    !Object.values(fieldNodes).some((f) => f.name === "write_date")
                ) {
                    fieldNodes.write_date_0 = { name: "write_date", type: "datetime" };
                }
            }

            // TODO: generate activeFields for the model based on fieldNodes (merge duplicated fields)
            for (const fieldNode of Object.values(fieldNodes)) {
                const fieldName = fieldNode.name;
                if (activeFields[fieldName]) {
                    const { alwaysInvisible } = fieldNode;
                    activeFields[fieldName] = {
                        ...fieldNode,
                        // a field can only be considered to be always invisible
                        // if all its nodes are always invisible
                        alwaysInvisible: activeFields[fieldName].alwaysInvisible && alwaysInvisible,
                    };
                } else {
                    activeFields[fieldName] = fieldNode;
                }
            }
        });
        return {
            arch,
            activeFields,
            fieldNodes,
            templateDocs,
            title,
            __rawArch: arch,
        };
    }
}
