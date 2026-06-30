import { exprToBoolean } from "@web/core/utils/strings";
import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { getActiveActions } from "@web/views/utils";
import { Widget } from "@web/views/widgets/widget";

export class FormArchParser {
    parse(xmlDoc, models, modelName) {
        const jsClass = xmlDoc.getAttribute("js_class");
        const disableAutofocus = exprToBoolean(xmlDoc.getAttribute("disable_autofocus") || "");
        const activeActions = getActiveActions(xmlDoc);
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const fieldNextIds = {};
        const autofocusFieldIds = [];
        visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "form", jsClass);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                if (exprToBoolean(node.getAttribute("default_focus") || "")) {
                    autofocusFieldIds.push(fieldId);
                }
                if (fieldInfo.type === "properties") {
                    activeActions.addPropertyFieldValue = true;
                }
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
            autofocusFieldIds,
            disableAutofocus,
            fieldNodes,
            widgetNodes,
            xmlDoc,
        };
    }
}
