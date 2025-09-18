// @ts-check

/** @module @web/views/kanban/kanban_arch_parser - Parses kanban view XML arch into card templates, field nodes, progress bars, and quick-create config */

import { extractAttributes, visitXML } from "@web/core/utils/dom/xml";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { stringToOrderBy } from "@web/core/utils/order_by";
import { Field } from "@web/fields/field";
import { processButton } from "@web/views/view_buttons";
import { getActiveActions } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

export const KANBAN_CARD_ATTRIBUTE = "card";
export const KANBAN_MENU_ATTRIBUTE = "menu";

/**
 * Parser for kanban view arch XML.
 *
 * Extracts field nodes, widget nodes, header buttons, control elements,
 * active actions, progress bar config, quick-create settings, and template
 * documents from the `<kanban>` arch definition.
 */
export class KanbanArchParser {
    /**
     * Parse a kanban arch XML document into a structured archInfo object.
     *
     * @param {XMLDocument} xmlDoc - Root `<kanban>` XML element.
     * @param {Object} models - Map of model name to `{ fields }` definitions.
     * @param {string} modelName - Technical name of the primary model.
     * @returns {{
     *   activeActions: Object,
     *   canOpenRecords: boolean,
     *   cardClassName: string,
     *   cardColorField: string | null,
     *   className: string | null,
     *   controls: Object[],
     *   defaultGroupBy: string[] | null,
     *   fieldNodes: Object,
     *   widgetNodes: Object,
     *   handleField: string | null,
     *   headerButtons: Object[],
     *   defaultOrder: Object[],
     *   onCreate: string | null,
     *   openAction: { action: string, type: string } | null,
     *   quickCreateView: string | null,
     *   recordsDraggable: boolean,
     *   groupsDraggable: boolean,
     *   limit: number | null,
     *   countLimit: number | null,
     *   progressAttributes: Object | false,
     *   templateDocs: Object,
     *   tooltipInfo: Object,
     *   examples: string | null,
     *   xmlDoc: XMLDocument,
     * }}
     */
    parse(xmlDoc, models, modelName) {
        const fields = models[modelName].fields;
        const className = xmlDoc.getAttribute("class") || null;
        const canOpenRecords = exprToBoolean(xmlDoc.getAttribute("can_open"), true);
        let defaultOrder = stringToOrderBy(
            xmlDoc.getAttribute("default_order") || null,
        );
        const limit = xmlDoc.getAttribute("limit");
        const countLimit = xmlDoc.getAttribute("count_limit");
        const recordsDraggable = exprToBoolean(
            xmlDoc.getAttribute("records_draggable"),
            true,
        );
        const groupsDraggable = exprToBoolean(
            xmlDoc.getAttribute("groups_draggable"),
            true,
        );
        /** @type {any} */
        const activeActions = getActiveActions(xmlDoc);
        activeActions.archiveGroup = exprToBoolean(
            xmlDoc.getAttribute("archivable"),
            true,
        );
        activeActions.createGroup = exprToBoolean(
            xmlDoc.getAttribute("group_create"),
            true,
        );
        activeActions.deleteGroup = exprToBoolean(
            xmlDoc.getAttribute("group_delete"),
            true,
        );
        activeActions.editGroup = exprToBoolean(
            xmlDoc.getAttribute("group_edit"),
            true,
        );
        activeActions.quickCreate =
            activeActions.create &&
            exprToBoolean(xmlDoc.getAttribute("quick_create"), true);
        const defaultGroupBy = xmlDoc.hasAttribute("default_group_by")
            ? xmlDoc.getAttribute("default_group_by").split(",")
            : null;
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
        const controls = [];
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
                        ...this.processButton(node),
                        type: "button",
                        id: button_id++,
                    }));
                return false;
            } else if (node.tagName === "control") {
                for (const childNode of node.children) {
                    if (childNode.tagName === "button") {
                        controls.push({
                            type: "button",
                            ...processButton(childNode),
                        });
                    } else if (childNode.tagName === "create") {
                        controls.push({
                            type: "create",
                            context: childNode.getAttribute("context"),
                            string: childNode.getAttribute("string"),
                            invisible: childNode.getAttribute("invisible"),
                            class: childNode.getAttribute("class"),
                        });
                    } else if (childNode.tagName === "delete") {
                        controls.push({
                            type: "delete",
                            invisible: childNode.getAttribute("invisible"),
                        });
                    }
                }
                return false;
            }
            // Case: field node
            if (node.tagName === "field") {
                // In kanban, we display many2many fields as tags by default
                const widget = node.getAttribute("widget");
                if (
                    !widget &&
                    models[modelName].fields[node.getAttribute("name")].type ===
                        "many2many"
                ) {
                    node.setAttribute("widget", "many2many_tags");
                }
                const fieldInfo = Field.parseFieldNode(
                    node,
                    models,
                    modelName,
                    "kanban",
                    jsClass,
                );
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
                    fieldNodes.write_date_0 = {
                        name: "write_date",
                        type: "datetime",
                    };
                }
            }
        });

        // Progressbar
        /** @type {any} */
        let progressAttributes = false;
        const progressBar = xmlDoc.querySelector("progressbar");
        if (progressBar) {
            progressAttributes = this.parseProgressBar(progressBar, fields);
        }

        // Concrete kanban box elements in the template
        const cardDoc = templateDocs[KANBAN_CARD_ATTRIBUTE];
        if (!cardDoc) {
            throw new Error(`Missing '${KANBAN_CARD_ATTRIBUTE}' template.`);
        }
        const cardClassName = cardDoc.getAttribute("class") || "";

        if (!defaultOrder.length && handleField) {
            const handleFieldSort = `${handleField}, id`;
            defaultOrder = stringToOrderBy(handleFieldSort);
        }

        return {
            activeActions,
            canOpenRecords,
            cardClassName,
            cardColorField: xmlDoc.getAttribute("highlight_color"),
            className,
            controls,
            defaultGroupBy,
            fieldNodes,
            widgetNodes,
            handleField,
            headerButtons,
            defaultOrder,
            onCreate,
            openAction,
            quickCreateView,
            recordsDraggable,
            groupsDraggable,
            limit: limit && parseInt(limit, 10),
            countLimit: countLimit && parseInt(countLimit, 10),
            progressAttributes,
            templateDocs,
            tooltipInfo,
            examples: xmlDoc.getAttribute("examples"),
            xmlDoc,
        };
    }

    /**
     * Parse a `<progressbar>` element into its configuration.
     *
     * @param {Element} progressBar - The `<progressbar>` XML element.
     * @param {Object} fields - Field definitions for the model.
     * @returns {{ fieldName: string, colors: Object, sumField: Object | false, help: string }}
     */
    parseProgressBar(progressBar, fields) {
        const attrs = extractAttributes(progressBar, [
            "field",
            "colors",
            "sum_field",
            "help",
        ]);
        return {
            fieldName: attrs.field,
            colors: JSON.parse(attrs.colors),
            sumField: fields[attrs.sum_field] || false,
            help: attrs.help,
        };
    }

    /**
     * Extract button attributes from a `<button>` node.
     *
     * @param {Element} node - A `<button>` XML element.
     * @returns {Object} Processed button descriptor.
     */
    processButton(node) {
        return processButton(node);
    }
}
