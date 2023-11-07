/** @odoo-module **/

import { extractAttributes, visitXML } from "@web/core/utils/xml";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";
import { archParseBoolean, getActiveActions, processButton } from "@web/views/utils";

/**
 * NOTE ON 't-name="kanban-box"':
 *
 * Multiple roots are supported in kanban box template definitions, however there
 * are a few things to keep in mind when doing so:
 *
 * - each root will generate its own card, so it would be preferable to make the
 * roots mutually exclusive to avoid rendering multiple cards for the same record;
 *
 * - certain fields such as the kanban 'color' or the 'handle' field are based on
 * the last encountered node, so it is advised to keep the same values for those
 * fields within all roots to avoid inconsistencies.
 */

export const KANBAN_BOX_ATTRIBUTE = "kanban-box";
export const KANBAN_MENU_ATTRIBUTE = "kanban-menu";
export const KANBAN_TOOLTIP_ATTRIBUTE = "kanban-tooltip";

export class KanbanArchParser {
    parse(xmlDoc, models, modelName) {
        const fields = models[modelName];
        const className = xmlDoc.getAttribute("class") || null;
        let defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order") || null);
        const defaultGroupBy = xmlDoc.getAttribute("default_group_by");
        const limit = xmlDoc.getAttribute("limit");
        const countLimit = xmlDoc.getAttribute("count_limit");
        const recordsDraggable = archParseBoolean(xmlDoc.getAttribute("records_draggable"), true);
        const groupsDraggable = archParseBoolean(xmlDoc.getAttribute("groups_draggable"), true);
        const activeActions = getActiveActions(xmlDoc);
        activeActions.archiveGroup = archParseBoolean(xmlDoc.getAttribute("archivable"), true);
        activeActions.createGroup = archParseBoolean(xmlDoc.getAttribute("group_create"), true);
        activeActions.deleteGroup = archParseBoolean(xmlDoc.getAttribute("group_delete"), true);
        activeActions.editGroup = archParseBoolean(xmlDoc.getAttribute("group_edit"), true);
        activeActions.quickCreate =
            activeActions.create && archParseBoolean(xmlDoc.getAttribute("quick_create"), true);
        const onCreate = xmlDoc.getAttribute("on_create");
        const quickCreateView = xmlDoc.getAttribute("quick_create_view");
        const tooltipInfo = {};
        let handleField = null;
        const fieldNodes = {};
        const fieldNextIds = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const jsClass = xmlDoc.getAttribute("js_class");
        const action = xmlDoc.getAttribute("action");
        const type = xmlDoc.getAttribute("type");
        const openAction = action && type ? { action, type } : null;
        const templateDocs = {};
        let headerButtons = [];
        const creates = [];
        let button_id = 0;
        // Root level of the template
        visitXML(xmlDoc, (node) => {
            if (node.hasAttribute("t-name")) {
                templateDocs[node.getAttribute("t-name")] = node;
                return;
            }
            if (node.tagName === "header") {
                headerButtons = [...node.children]
                    .filter((node) => node.tagName === "button")
                    .map((node) => ({
                        ...processButton(node),
                        type: "button",
                        id: button_id++,
                    }))
                    .filter((button) => button.invisible !== "True" && button.invisible !== "1");
                return false;
            } else if (node.tagName === "control") {
                for (const childNode of node.children) {
                    if (childNode.tagName === "button") {
                        creates.push({
                            type: "button",
                            ...processButton(childNode),
                        });
                    } else if (childNode.tagName === "create") {
                        creates.push({
                            type: "create",
                            context: childNode.getAttribute("context"),
                            string: childNode.getAttribute("string"),
                        });
                    }
                }
                return false;
            }
            // Case: field node
            if (node.tagName === "field") {
                // In kanban, we display many2many fields as tags by default
                const widget = node.getAttribute("widget");
                if (!widget && models[modelName][node.getAttribute("name")].type === "many2many") {
                    node.setAttribute("widget", "many2many_tags");
                }
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "kanban", jsClass);
                if (!node.hasAttribute("force_save")) {
                    // Force save is true by default on kanban views:
                    // this allows to write on any field regardless of its modifiers.
                    fieldInfo.forceSave = true;
                }
                const name = fieldInfo.name;
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                if (fieldInfo.options.group_by_tooltip) {
                    tooltipInfo[name] = fieldInfo.options.group_by_tooltip;
                }
                if (fieldInfo.isHandle) {
                    handleField = name;
                }
            }
            if (node.tagName === "widget") {
                const widgetInfo = Widget.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                node.setAttribute("widget_id", widgetId);
            }

            // Keep track of last update so images can be reloaded when they may have changed.
            if (node.tagName === "img") {
                const attSrc = node.getAttribute("t-att-src");
                if (
                    attSrc &&
                    /\bkanban_image\b/.test(attSrc) &&
                    !Object.values(fieldNodes).some((f) => f.name === "write_date")
                ) {
                    fieldNodes.write_date_0 = { name: "write_date", type: "datetime" };
                }
            }
        });

        // Progressbar
        let progressAttributes = false;
        const progressBar = xmlDoc.querySelector("progressbar");
        if (progressBar) {
            progressAttributes = this.parseProgressBar(progressBar, fields);
        }

        // Concrete kanban box elements in the template
        const cardDoc = templateDocs[KANBAN_BOX_ATTRIBUTE];
        if (!cardDoc) {
            throw new Error(`Missing '${KANBAN_BOX_ATTRIBUTE}' template.`);
        }

        // Color and color picker (first node found is taken for each)
        const cardColorEl = cardDoc.querySelector("[color]");
        const cardColorField = cardColorEl && cardColorEl.getAttribute("color");

        const colorEl = cardDoc.querySelector(".oe_kanban_colorpicker[data-field]");
        const colorField = (colorEl && colorEl.getAttribute("data-field")) || "color";

        if (!defaultOrder.length && handleField) {
            defaultOrder = stringToOrderBy(handleField);
        }

        return {
            activeActions,
            className,
            creates,
            defaultGroupBy,
            fieldNodes,
            widgetNodes,
            handleField,
            headerButtons,
            colorField,
            defaultOrder,
            onCreate,
            openAction,
            quickCreateView,
            recordsDraggable,
            groupsDraggable,
            limit: limit && parseInt(limit, 10),
            countLimit: countLimit && parseInt(countLimit, 10),
            progressAttributes,
            cardColorField,
            templateDocs,
            tooltipInfo,
            examples: xmlDoc.getAttribute("examples"),
            xmlDoc,
        };
    }

    parseProgressBar(progressBar, fields) {
        const attrs = extractAttributes(progressBar, ["field", "colors", "sum_field", "help"]);
        return {
            fieldName: attrs.field,
            colors: JSON.parse(attrs.colors),
            sumField: fields[attrs.sum_field] || false,
            help: attrs.help,
        };
    }
}
