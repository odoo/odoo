import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";
import { getActiveActions } from "../utils";

export const CARD_ATTRIBUTE = "card";

export class CardArchParser {
    parse(xmlDoc, models, modelName) {
        const templateDocs = {};
        const fieldNodes = {};
        const widgetNodes = {};
        const nextFieldIds = {};
        let nextWidgetId = 0;

        visitXML(xmlDoc, (node) => {
            if (node.hasAttribute("t-name")) {
                templateDocs[node.getAttribute("t-name")] = node;
                return;
            }
            switch (node.tagName) {
                case "field": {
                    const widget = node.getAttribute("widget");
                    const field = models[modelName].fields[node.getAttribute("name")];
                    if (!widget && field.type === "many2many") {
                        // in cards, we display many2many fields as tags by default
                        node.setAttribute("widget", "many2many_tags");
                    }
                    const fieldInfo = Field.parseFieldNode(node, models, modelName, "card");
                    if (!(fieldInfo.name in nextFieldIds)) {
                        nextFieldIds[fieldInfo.name] = 0;
                    }
                    const fieldId = `${fieldInfo.name}_${nextFieldIds[fieldInfo.name]++}`;
                    fieldNodes[fieldId] = fieldInfo;
                    node.setAttribute("field_id", fieldId);
                    break;
                }
                case "widget": {
                    const widgetInfo = Widget.parseWidgetNode(node);
                    const widgetId = `widget_${nextWidgetId++}`;
                    widgetNodes[widgetId] = widgetInfo;
                    node.setAttribute("widget_id", widgetId);
                    break;
                }
            }
        });

        const cardDoc = templateDocs[CARD_ATTRIBUTE];
        if (!cardDoc) {
            throw new Error(`Missing '${CARD_ATTRIBUTE}' template.`);
        }

        return {
            activeActions: getActiveActions(xmlDoc),
            cardClassName: cardDoc.getAttribute("class") || "",
            fieldNodes: fieldNodes,
            widgetNodes: widgetNodes,
            templateDocs: templateDocs,
            xmlDoc,
        };
    }
}
