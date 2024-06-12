/** @odoo-module **/

import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";
import { archParseBoolean, getActiveActions } from "@web/views/utils";

export class FormArchParser {
    parse(xmlDoc, models, modelName) {
        const jsClass = xmlDoc.getAttribute("js_class");
        const disableAutofocus = archParseBoolean(xmlDoc.getAttribute("disable_autofocus") || "");
        const activeActions = getActiveActions(xmlDoc);
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const fieldNextIds = {};
        let autofocusFieldId = null;
        visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "form", jsClass);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                if (archParseBoolean(node.getAttribute("default_focus") || "")) {
                    autofocusFieldId = fieldId;
                }
                if (fieldInfo.type === "properties") {
                    activeActions.addPropertyFieldValue = true;
                }
                return false;
            } else if (node.tagName === "div" && node.classList.contains("oe_chatter")) {
                // remove this when chatter fields are declared as attributes on the root node
                return false;
            } else if (node.tagName === "widget") {
                const widgetInfo = Widget.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                node.setAttribute("widget_id", widgetId);
            }
        });
        return {
            activeActions,
            autofocusFieldId,
            disableAutofocus,
            fieldNodes,
            widgetNodes,
            xmlDoc,
        };
    }
}
