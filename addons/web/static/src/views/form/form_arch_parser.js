/** @odoo-module **/

import { addFieldDependencies, archParseBoolean, getActiveActions } from "@web/views/utils";
import { Field } from "@web/views/fields/field";
import { XMLParser } from "@web/core/utils/xml";
import { Widget } from "@web/views/widgets/widget";

export class FormArchParser extends XMLParser {
    parse(arch, models, modelName) {
        const xmlDoc = this.parseXML(arch);
        const jsClass = xmlDoc.getAttribute("js_class");
        const disableAutofocus = archParseBoolean(xmlDoc.getAttribute("disable_autofocus") || "");
        const activeActions = getActiveActions(xmlDoc);
        const fieldNodes = {};
        const fieldNextIds = {};
        let autofocusFieldId = null;
        const activeFields = {};
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "form", jsClass);
                let fieldId = fieldInfo.name;
                if (fieldInfo.name in fieldNextIds) {
                    fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                } else {
                    fieldNextIds[fieldInfo.name] = 1;
                }
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                if (archParseBoolean(node.getAttribute("default_focus") || "")) {
                    autofocusFieldId = fieldId;
                }
                addFieldDependencies(activeFields, fieldInfo.FieldComponent.fieldDependencies);
                return false;
            } else if (node.tagName === "div" && node.classList.contains("oe_chatter")) {
                // remove this when chatter fields are declared as attributes on the root node
                return false;
            } else if (node.tagName === "widget") {
                const { WidgetComponent } = Widget.parseWidgetNode(node);
                addFieldDependencies(activeFields, WidgetComponent.fieldDependencies);
            }
        });
        // TODO: generate activeFields for the model based on fieldNodes (merge duplicated fields)
        for (const fieldNode of Object.values(fieldNodes)) {
            activeFields[fieldNode.name] = fieldNode;
            // const { onChange, modifiers } = fieldNode;
            // let readonly = modifiers.readonly || [];
            // let required = modifiers.required || [];
            // if (activeFields[fieldNode.name]) {
            //     activeFields[fieldNode.name].readonly = Domain.combine([activeFields[fieldNode.name].readonly, readonly], "|");
            //     activeFields[fieldNode.name].required = Domain.combine([activeFields[fieldNode.name].required, required], "|");
            //     activeFields[fieldNode.name].onChange = activeFields[fieldNode.name].onChange || onChange;
            // } else {
            //     activeFields[fieldNode.name] = { readonly, required, onChange };
            // }
        }
        return {
            arch,
            activeActions,
            activeFields,
            autofocusFieldId,
            disableAutofocus,
            fieldNodes,
            xmlDoc,
            __rawArch: arch,
        };
    }
}
