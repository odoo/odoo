// @ts-check

/** @module @web/views/list/list_arch_parser - Parses list view XML arch into column definitions, groupby configs, buttons, and decorations */

import { getDecoration } from "@web/core/utils/decorations";
import { visitXML } from "@web/core/utils/dom/xml";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { stringToOrderBy } from "@web/core/utils/order_by";
import { Field } from "@web/fields/field";
import { combineModifiers } from "@web/model/relational_model/utils";
import { processButton } from "@web/views/view_buttons";
import { encodeObjectForTemplate } from "@web/views/view_compiler";
import { getActiveActions } from "@web/views/view_utils";
import { Widget } from "@web/views/widgets/widget";

/**
 * Arch parser for `<groupby>` sub-trees inside a list view.
 *
 * Extracts field nodes and buttons declared inside a `<groupby name="...">` element
 * so they can be rendered when the list is grouped by that field.
 */
class GroupListArchParser {
    /**
     * Parse a `<groupby>` XML node.
     *
     * @param {Element} arch - the `<groupby>` DOM element
     * @param {Record<string, any>} models - model metadata keyed by model name
     * @param {string} modelName - the co-model of the groupby field
     * @param {string} [jsClass] - optional js_class override
     * @returns {{ fieldNodes: Record<string, any>, buttons: any[] }}
     */
    parse(arch, models, modelName, jsClass) {
        const fieldNodes = {};
        const fieldNextIds = {};
        const buttons = [];
        let buttonId = 0;
        visitXML(arch, (node) => {
            if (node.tagName === "button") {
                buttons.push({
                    ...processButton(node),
                    id: buttonId++,
                });
                return false;
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(
                    node,
                    models,
                    modelName,
                    "list",
                    jsClass,
                );
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                return false;
            }
        });
        return { fieldNodes, buttons };
    }
}

/**
 * Arch parser for the `<list>` (tree) view.
 *
 * Walks the XML arch and extracts columns (fields, buttons, widgets),
 * header buttons, `<control>` elements, `<groupby>` sub-parsers, decorations,
 * active actions, and all view-level attributes (editable, limit, etc.).
 */
export class ListArchParser {
    /**
     * Parse a `<field>` node into a field descriptor.
     *
     * @param {Element} node - the `<field>` element
     * @param {Record<string, any>} models - model metadata
     * @param {string} modelName - current model name
     * @returns {any} parsed field info
     */
    parseFieldNode(node, models, modelName) {
        return Field.parseFieldNode(node, models, modelName, "list");
    }

    /**
     * Parse a `<widget>` node into a widget descriptor.
     *
     * @param {Element} node - the `<widget>` element
     * @param {Record<string, any>} models - model metadata (unused, kept for API symmetry)
     * @param {string} modelName - current model name (unused)
     * @returns {any} parsed widget info
     */
    parseWidgetNode(node, models, modelName) {
        return Widget.parseWidgetNode(node);
    }

    /**
     * Extract button metadata from a `<button>` element.
     *
     * @param {Element} node - the `<button>` element
     * @returns {any} button descriptor
     */
    processButton(node) {
        return processButton(node);
    }

    /**
     * Parse a complete `<list>` arch into a structured descriptor.
     *
     * The returned object contains columns (fields, buttons, widgets), header
     * buttons, controls, groupBy info, decorations, active actions, and all
     * view-level settings (editable, limit, defaultOrder, etc.).
     *
     * @param {Element} xmlDoc - the root `<list>` element
     * @param {Record<string, any>} models - model metadata keyed by model name
     * @param {string} modelName - the primary model name
     * @returns {{
     *   controls: any[],
     *   headerButtons: any[],
     *   fieldNodes: Record<string, any>,
     *   widgetNodes: Record<string, any>,
     *   columns: any[],
     *   groupBy: { buttons: Record<string, any[]>, fields: Record<string, any> },
     *   xmlDoc: Element,
     *   activeActions: Record<string, boolean>,
     *   [key: string]: any,
     * }}
     */
    parse(xmlDoc, models, modelName) {
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const columns = [];
        const fields = models[modelName].fields;
        let buttonId = 0;
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let headerButtons = [];
        const controls = [];
        const groupListArchParser = new GroupListArchParser();
        let buttonGroup;
        let handleField = null;
        const treeAttr = {};
        let nextId = 0;
        const fieldNextIds = {};
        visitXML(xmlDoc, (node) => {
            if (node.tagName !== "button") {
                buttonGroup = undefined;
            }
            if (node.tagName === "button") {
                const button = {
                    ...this.processButton(node),
                    defaultRank: "btn-link",
                    type: "button",
                    id: buttonId++,
                };
                const width = button.attrs.width;
                if (buttonGroup && !width) {
                    buttonGroup.buttons.push(button);
                    buttonGroup.column_invisible = combineModifiers(
                        buttonGroup.column_invisible,
                        node.getAttribute("column_invisible"),
                        "AND",
                    );
                } else {
                    buttonGroup = /** @type {any} */ ({
                        id: `column_${nextId++}`,
                        type: "button_group",
                        buttons: [button],
                        hasLabel: false,
                        column_invisible: node.getAttribute("column_invisible"),
                    });
                    columns.push(buttonGroup);
                    if (width) {
                        buttonGroup.attrs = { width };
                        buttonGroup = undefined;
                    }
                }
            } else if (node.tagName === "field") {
                const fieldInfo = this.parseFieldNode(node, models, modelName);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                if (fieldInfo.isHandle) {
                    handleField = fieldInfo.name;
                }
                const label = fieldInfo.field.label;
                columns.push({
                    ...fieldInfo,
                    id: `column_${nextId++}`,
                    className: node.getAttribute("class"), // for oe_edit_only and oe_read_only
                    optional: node.getAttribute("optional") || false,
                    type: "field",
                    fieldType: fieldInfo.type,
                    hasLabel: !(
                        fieldInfo.field.label === false ||
                        exprToBoolean(fieldInfo.attrs.nolabel) === true
                    ),
                    label:
                        (fieldInfo.widget && label && label.toString()) ||
                        fieldInfo.string,
                });
                return false;
            } else if (node.tagName === "widget") {
                const widgetInfo = this.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                node.setAttribute("widget_id", widgetId);

                const widgetProps = {
                    name: widgetInfo.name,
                    // FIXME: this is dumb, we encode it into a weird object so that the widget
                    // can decode it later...
                    node: encodeObjectForTemplate({
                        attrs: widgetInfo.attrs,
                    }).slice(1, -1),
                    className: node.getAttribute("class") || "",
                    widgetInfo,
                };
                columns.push({
                    ...widgetInfo,
                    props: widgetProps,
                    id: `column_${nextId++}`,
                    type: "widget",
                });
            } else if (node.tagName === "groupby" && node.getAttribute("name")) {
                const fieldName = node.getAttribute("name");
                const coModelName = fields[fieldName].relation;
                const groupByArchInfo = groupListArchParser.parse(
                    node,
                    models,
                    coModelName,
                );
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    fieldNodes: groupByArchInfo.fieldNodes,
                    fields: models[coModelName].fields,
                };
                return false;
            } else if (node.tagName === "header") {
                headerButtons = [...node.children].map((node) => ({
                    ...this.processButton(node),
                    type: "button",
                    id: buttonId++,
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
                        });
                    } else if (childNode.tagName === "delete") {
                        controls.push({
                            type: "delete",
                            invisible: childNode.getAttribute("invisible"),
                        });
                    }
                }
                return false;
            } else if ("list" === node.tagName) {
                const activeActions = {
                    ...getActiveActions(xmlDoc),
                    exportXlsx: exprToBoolean(xmlDoc.getAttribute("export_xlsx"), true),
                    createGroup: exprToBoolean(
                        xmlDoc.getAttribute("group_create"),
                        true,
                    ),
                    editGroup: exprToBoolean(xmlDoc.getAttribute("group_edit"), true),
                    deleteGroup: exprToBoolean(
                        xmlDoc.getAttribute("group_delete"),
                        true,
                    ),
                };
                treeAttr.activeActions = activeActions;

                treeAttr.className = xmlDoc.getAttribute("class") || null;
                treeAttr.editable = xmlDoc.getAttribute("editable");
                treeAttr.multiEdit = activeActions.edit
                    ? exprToBoolean(node.getAttribute("multi_edit") || "")
                    : false;

                treeAttr.openFormView = treeAttr.editable
                    ? exprToBoolean(xmlDoc.getAttribute("open_form_view") || "")
                    : false;
                treeAttr.defaultGroupBy = xmlDoc.hasAttribute("default_group_by")
                    ? xmlDoc.getAttribute("default_group_by").split(",")
                    : null;

                const limitAttr = node.getAttribute("limit");
                treeAttr.limit = limitAttr && parseInt(limitAttr, 10);

                const countLimitAttr = node.getAttribute("count_limit");
                treeAttr.countLimit = countLimitAttr && parseInt(countLimitAttr, 10);

                const groupsLimitAttr = node.getAttribute("groups_limit");
                treeAttr.groupsLimit = groupsLimitAttr && parseInt(groupsLimitAttr, 10);

                treeAttr.noOpen = exprToBoolean(node.getAttribute("no_open") || "");
                treeAttr.rawExpand = xmlDoc.getAttribute("expand");
                treeAttr.decorations = getDecoration(xmlDoc);

                treeAttr.defaultOrder = stringToOrderBy(
                    xmlDoc.getAttribute("default_order") || null,
                );

                // custom open action when clicking on record row
                const action = xmlDoc.getAttribute("action");
                const type = xmlDoc.getAttribute("type");
                treeAttr.openAction = action && type ? { action, type } : null;
            }
        });

        if (!treeAttr.defaultOrder.length && handleField) {
            const handleFieldSort = `${handleField}, id`;
            treeAttr.defaultOrder = stringToOrderBy(handleFieldSort);
        }

        return {
            controls,
            headerButtons,
            fieldNodes,
            widgetNodes,
            columns,
            groupBy,
            xmlDoc,
            ...treeAttr,
        };
    }
}
