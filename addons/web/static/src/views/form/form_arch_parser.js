// @ts-check

/** @module @web/views/form/form_arch_parser - Parses form view XML arch into field/widget descriptors, active actions, and autofocus targets */

import { visitXML } from "@web/core/utils/dom/xml";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { Field } from "@web/fields/field";
import { getActiveActions } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

/**
 * Arch parser for the form view.
 *
 * Walks the arch XML, extracts field/widget node descriptors, active actions,
 * autofocus targets, and the js_class identifier.
 */
export class FormArchParser {
    /**
     * @param {Element} xmlDoc - the parsed form arch XML document
     * @param {Object} models - related model field definitions
     * @param {string} modelName - the model's technical name
     * @returns {{ activeActions: Object, autofocusFieldIds: string[], disableAutofocus: boolean, fieldNodes: Object, widgetNodes: Object, xmlDoc: Element }}
     */
    parse(xmlDoc, models, modelName) {
        const jsClass = xmlDoc.getAttribute("js_class");
        const disableAutofocus = exprToBoolean(
            xmlDoc.getAttribute("disable_autofocus") || "",
        );
        const activeActions = getActiveActions(xmlDoc);
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const fieldNextIds = {};
        const autofocusFieldIds = [];
        visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(
                    node,
                    models,
                    modelName,
                    "form",
                    jsClass,
                );
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
                    /** @type {any} */ (activeActions).addPropertyFieldValue = true;
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
