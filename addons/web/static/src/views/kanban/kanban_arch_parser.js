/** @odoo-module **/

import {
    addFieldDependencies,
    archParseBoolean,
    getActiveActions,
    stringToOrderBy,
} from "@web/views/utils";
import { extractAttributes, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";

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
export const KANBAN_TOOLTIP_ATTRIBUTE = "kanban-tooltip";

export class KanbanArchParser extends XMLParser {
    parse(arch, models, modelName) {
        const fields = models[modelName];
        const xmlDoc = this.parseXML(arch);
        const className = xmlDoc.getAttribute("class") || null;
        let defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order") || null);
        const defaultGroupBy = xmlDoc.getAttribute("default_group_by");
        const limit = xmlDoc.getAttribute("limit");
        const recordsDraggable = archParseBoolean(xmlDoc.getAttribute("records_draggable"), true);
        const groupsDraggable = archParseBoolean(xmlDoc.getAttribute("groups_draggable"), true);
        const activeActions = {
            ...getActiveActions(xmlDoc),
            groupArchive: archParseBoolean(xmlDoc.getAttribute("archivable"), true),
            groupCreate: archParseBoolean(xmlDoc.getAttribute("group_create"), true),
            groupDelete: archParseBoolean(xmlDoc.getAttribute("group_delete"), true),
            groupEdit: archParseBoolean(xmlDoc.getAttribute("group_edit"), true),
        };
        const onCreate =
            activeActions.create &&
            archParseBoolean(xmlDoc.getAttribute("quick_create"), true) &&
            xmlDoc.getAttribute("on_create");
        const quickCreateView = xmlDoc.getAttribute("quick_create_view");
        const tooltipInfo = {};
        let handleField = null;
        const fieldNodes = {};
        const jsClass = xmlDoc.getAttribute("js_class");
        const action = xmlDoc.getAttribute("action");
        const type = xmlDoc.getAttribute("type");
        const openAction = action && type ? { action, type } : null;
        const templateDocs = {};
        const activeFields = {};
        // Root level of the template
        this.visitXML(xmlDoc, (node) => {
            if (node.hasAttribute("t-name")) {
                templateDocs[node.getAttribute("t-name")] = node;
                return;
            }
            // Case: field node
            if (node.tagName === "field") {
                // In kanban, we display many2many fields as tags by default
                const widget = node.getAttribute("widget");
                if (!widget && models[modelName][node.getAttribute("name")].type === "many2many") {
                    node.setAttribute("widget", "many2many_tags");
                }
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "kanban", jsClass);
                const name = fieldInfo.name;
                fieldNodes[name] = fieldInfo;
                node.setAttribute("field_id", name);
                if (fieldInfo.options.group_by_tooltip) {
                    tooltipInfo[name] = fieldInfo.options.group_by_tooltip;
                }
                if (fieldInfo.widget === "handle") {
                    handleField = name;
                }
                addFieldDependencies(activeFields, fieldInfo.FieldComponent.fieldDependencies);
            }
            if (node.tagName === "widget") {
                const { WidgetComponent } = Widget.parseWidgetNode(node);
                addFieldDependencies(activeFields, WidgetComponent.fieldDependencies);
            }

            // Keep track of last update so images can be reloaded when they may have changed.
            if (node.tagName === "img") {
                const attSrc = node.getAttribute("t-att-src");
                if (attSrc && /\bkanban_image\b/.test(attSrc) && !fieldNodes.__last_update) {
                    fieldNodes.__last_update = { type: "datetime" };
                }
            }
        });

        // Progressbar
        let progressAttributes = false;
        const progressBar = xmlDoc.querySelector("progressbar");
        if (progressBar) {
            const attrs = extractAttributes(progressBar, ["field", "colors", "sum_field", "help"]);
            progressAttributes = {
                fieldName: attrs.field,
                colors: JSON.parse(attrs.colors),
                sumField: fields[attrs.sum_field] || false,
                help: attrs.help,
            };
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

        for (const [key, field] of Object.entries(fieldNodes)) {
            activeFields[key] = field; // TODO process
        }

        return {
            arch,
            activeActions,
            activeFields,
            className,
            defaultGroupBy,
            fieldNodes,
            handleField,
            colorField,
            defaultOrder,
            onCreate,
            openAction,
            quickCreateView,
            recordsDraggable,
            groupsDraggable,
            limit: limit && parseInt(limit, 10),
            progressAttributes,
            cardColorField,
            templateDocs,
            tooltipInfo,
            examples: xmlDoc.getAttribute("examples"),
            __rawArch: arch,
        };
    }
}
