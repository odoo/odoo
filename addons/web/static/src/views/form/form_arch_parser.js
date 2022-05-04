/** @odoo-module **/

import { XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";
import { getActiveActions } from "@web/views/helpers/view_utils";

export class FormArchParser extends XMLParser {
    parse(arch, models, modelName) {
        const xmlDoc = this.parseXML(arch);
        const jsClass = xmlDoc.getAttribute("js_class");
        const activeActions = getActiveActions(xmlDoc);
        const activeFields = {};
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "form", jsClass);
                activeFields[fieldInfo.name] = fieldInfo;
                return false;
            } else if (node.tagName === "div") {
                // TODO TO FIX WITH MAIL
                if (node.className === "oe_chatter") {
                    return false;
                }
            }
        });
        return { arch, activeActions, activeFields, xmlDoc, __rawArch: arch };
    }
}
