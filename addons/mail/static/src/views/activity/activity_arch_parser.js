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
                const name = fieldInfo.name;
                fieldNodes[name] = fieldInfo;
                node.setAttribute("field_id", name);

                addFieldDependencies(
                    activeFields,
                    models[modelName],
                    fieldInfo.field.fieldDependencies
                );
            }

            // Keep track of last update so images can be reloaded when they may have changed.
            if (node.tagName === "img") {
                const attSrc = node.getAttribute("t-att-src");
                if (attSrc && /\bactivity_image\b/.test(attSrc) && !fieldNodes.write_date) {
                    fieldNodes.write_date = { type: "datetime" };
                }
            }

            for (const [key, field] of Object.entries(fieldNodes)) {
                activeFields[key] = field;
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
