/** @odoo-module **/

import { addFieldDependencies, archParseBoolean, getActiveActions } from "@web/views/utils";
import { Field } from "@web/views/fields/field";
import { XMLParser } from "@web/core/utils/xml";
import { Widget } from "@web/views/widgets/widget";
import { Domain } from "@web/core/domain";

export class FormArchParser extends XMLParser {
    combineDomain(d1, d2) {
        if (d1 === true || d2 === true) {
            return true;
        } else if (d1 && d2) {
            return Domain.or([d1 || [], d2 || []]).ast.value;
        }
    }

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
                addFieldDependencies(
                    activeFields,
                    models[modelName],
                    fieldInfo.FieldComponent.fieldDependencies
                );
                return false;
            } else if (node.tagName === "div" && node.classList.contains("oe_chatter")) {
                // remove this when chatter fields are declared as attributes on the root node
                return false;
            } else if (node.tagName === "widget") {
                const { WidgetComponent } = Widget.parseWidgetNode(node);
                addFieldDependencies(
                    activeFields,
                    models[modelName],
                    WidgetComponent.fieldDependencies
                );
            }
        });
        // TODO: generate activeFields for the model based on fieldNodes (merge duplicated fields)
        for (const fieldNode of Object.values(fieldNodes)) {
            const fieldName = fieldNode.name;
            if (activeFields[fieldName]) {
                const { alwaysInvisible, onChange, modifiers } = fieldNode;
                const readonly = this.combineDomain(
                    modifiers.readonly,
                    activeFields[fieldNode.name].modifiers.readonly
                );
                const required = this.combineDomain(
                    modifiers.required,
                    activeFields[fieldNode.name].modifiers.required
                );
                activeFields[fieldName] = {
                    ...fieldNode,
                    // a field can only be considered to be always invisible
                    // if all its nodes are always invisible
                    alwaysInvisible: activeFields[fieldName].alwaysInvisible && alwaysInvisible,
                    modifiers: {
                        ...(readonly && { readonly }),
                        ...(required && { required }),
                    },
                    onChange: activeFields[fieldNode.name].onChange || onChange,
                };
            } else {
                activeFields[fieldName] = fieldNode;
            }
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
