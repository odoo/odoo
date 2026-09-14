// @ts-check
/** @odoo-module native */

import { getDecoration } from "@web/core/utils/decorations";
import { visitXML } from "@web/core/utils/dom/xml";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { stringToOrderBy } from "@web/core/utils/order_by";
import { combineModifiers } from "@web/model/relational_model";
import { parseFieldNode } from "@web/views/field_arch";
import { nodeAttrs } from "@web/views/ir/view_ir";
import { ViewArchParser } from "@web/views/view_arch_parser";
import { processButton } from "@web/views/view_buttons";
import { encodeObjectForTemplate } from "@web/views/view_compiler";
import { getActiveActions } from "@web/views/view_utils";

class GroupListArchParser {
    /**
     * @param {Element} arch
     * @param {Record<string, any>} models
     * @param {string} modelName
     * @param {string} [jsClass]
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
                const fieldInfo = parseFieldNode(
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

export class ListArchParser extends ViewArchParser {
    /**
     * @param {Element} node
     * @param {Record<string, any>} models
     * @param {string} modelName
     * @param {string} [jsClass]
     * @returns {any}
     */
    parseFieldNode(node, models, modelName, jsClass) {
        return parseFieldNode(node, models, modelName, "list", jsClass);
    }

    /**
     * @typedef {{
     * xmlDoc: Element,
     * models: Record<string, any>,
     * modelName: string,
     * jsClass: string | undefined,
     * fields: import("fields").FieldDefinitionMap,
     * fieldNodes: Record<string, any>,
     * widgetNodes: Record<string, any>,
     * widgetNextId: number,
     * columns: any[],
     * buttonId: number,
     * nextId: number,
     * fieldNextIds: Record<string, number>,
     * groupBy: { buttons: Record<string, any[]>, fields: Record<string, any> },
     * headerButtons: any[],
     * controls: any[],
     * buttonGroup: any,
     * handleField: string | null,
     * treeAttr: { activeActions: Record<string, any>, defaultOrder: any[], [key: string]: any },
     * groupListArchParser: GroupListArchParser,
     * }} ListParseState
     */

    /**
     * @param {Element} xmlDoc
     * @param {Record<string, any>} models
     * @param {string} modelName
     * @returns {ListParseState}
     */
    newParseState(xmlDoc, models, modelName) {
        return {
            xmlDoc,
            models,
            modelName,
            jsClass: xmlDoc.getAttribute("js_class") ?? undefined,
            fields: models[modelName].fields,
            fieldNodes: {},
            widgetNodes: {},
            widgetNextId: 0,
            columns: [],
            buttonId: 0,
            nextId: 0,
            fieldNextIds: {},
            groupBy: { buttons: {}, fields: {} },
            headerButtons: [],
            controls: [],
            buttonGroup: undefined,
            handleField: null,
            treeAttr: {
                /** @type {Record<string, any>} */
                activeActions: {},
                /** @type {any[]} */
                defaultOrder: [],
            },
            groupListArchParser: new GroupListArchParser(),
        };
    }

    /**
     * @param {Element} node
     * @param {ListParseState} state
     * @returns {false | undefined}
     */
    visitNode(node, state) {
        if (node.tagName !== "button") {
            state.buttonGroup = undefined;
        }
        switch (node.tagName) {
            case "button":
                return this.parseButtonNode(node, state);
            case "field":
                return this.parseFieldColumn(node, state);
            case "widget":
                return this.parseWidgetColumn(node, state);
            case "groupby":
                return node.getAttribute("name")
                    ? this.parseGroupByNode(node, state)
                    : undefined;
            case "header":
                return this.parseHeaderNode(node, state);
            case "control":
                return this.parseControlNode(node, state);
            case "list":
                return this.parseRootNode(node, state);
            default:
                return undefined;
        }
    }

    /**
     * @param {Element} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseButtonNode(node, state) {
        const button = {
            ...this.processButton(node),
            defaultRank: "btn-link",
            type: "button",
            id: state.buttonId++,
        };
        const width = button.attrs.width;
        if (state.buttonGroup && !width) {
            state.buttonGroup.buttons.push(button);
            state.buttonGroup.column_invisible = combineModifiers(
                state.buttonGroup.column_invisible,
                node.getAttribute("column_invisible"),
                "AND",
            );
        } else {
            state.buttonGroup = /** @type {any} */ ({
                id: `column_${state.nextId++}`,
                type: "button_group",
                buttons: [button],
                hasLabel: false,
                column_invisible: node.getAttribute("column_invisible"),
            });
            state.columns.push(state.buttonGroup);
            if (width) {
                state.buttonGroup.attrs = { width };
                state.buttonGroup = undefined;
            }
        }
        return false;
    }

    /**
     * @param {Element} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseFieldColumn(node, state) {
        const fieldInfo = this.parseFieldNode(
            node,
            state.models,
            state.modelName,
            state.jsClass,
        );
        if (!(fieldInfo.name in state.fieldNextIds)) {
            state.fieldNextIds[fieldInfo.name] = 0;
        }
        const fieldId = `${fieldInfo.name}_${state.fieldNextIds[fieldInfo.name]++}`;
        state.fieldNodes[fieldId] = fieldInfo;
        node.setAttribute("field_id", fieldId);
        if (fieldInfo.isHandle) {
            state.handleField = fieldInfo.name;
        }
        const label = fieldInfo.field.label;
        state.columns.push({
            ...fieldInfo,
            id: `column_${state.nextId++}`,
            className: node.getAttribute("class"),
            optional: node.getAttribute("optional") || false,
            type: "field",
            fieldType: fieldInfo.type,
            fieldDefinition: state.fields[fieldInfo.name],
            hasLabel: !(
                fieldInfo.field.label === false ||
                exprToBoolean(fieldInfo.attrs.nolabel) === true
            ),
            label: (fieldInfo.widget && label && label.toString()) || fieldInfo.string,
        });
        return false;
    }

    /**
     * @param {Element} node
     * @param {ListParseState} state
     * @returns {undefined}
     */
    parseWidgetColumn(node, state) {
        const widgetInfo = this.parseWidgetNode(node);
        const widgetId = `widget_${++state.widgetNextId}`;
        state.widgetNodes[widgetId] = widgetInfo;
        node.setAttribute("widget_id", widgetId);

        const widgetProps = {
            name: widgetInfo.name,
            node: encodeObjectForTemplate({ attrs: widgetInfo.attrs }).slice(1, -1),
            className: node.getAttribute("class") || "",
            widgetInfo,
        };
        state.columns.push({
            ...widgetInfo,
            props: widgetProps,
            id: `column_${state.nextId++}`,
            type: "widget",
        });
        return undefined;
    }

    /**
     * @param {Element} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseGroupByNode(node, state) {
        const fieldName = /** @type {string} */ (node.getAttribute("name"));
        const coModelName = state.fields[fieldName].relation;
        const groupByArchInfo = state.groupListArchParser.parse(
            node,
            state.models,
            coModelName,
            state.jsClass,
        );
        state.groupBy.buttons[fieldName] = groupByArchInfo.buttons;
        state.groupBy.fields[fieldName] = {
            fieldNodes: groupByArchInfo.fieldNodes,
            fields: state.models[coModelName].fields,
        };
        return false;
    }

    /**
     * @param {Element} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseHeaderNode(node, state) {
        state.headerButtons = this.parseHeaderButtons(node, state.buttonId);
        state.buttonId += state.headerButtons.length;
        return false;
    }

    /**
     * @param {Element} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseControlNode(node, state) {
        state.controls.push(...this.parseControls(node));
        return false;
    }

    /**
     * @param {Element} _node
     * @param {ListParseState} state
     * @returns {undefined}
     */
    parseRootNode(_node, state) {
        const { xmlDoc, treeAttr } = state;
        const activeActions = {
            ...getActiveActions(xmlDoc),
            exportXlsx: exprToBoolean(xmlDoc.getAttribute("export_xlsx"), true),
            createGroup: exprToBoolean(xmlDoc.getAttribute("group_create"), true),
            editGroup: exprToBoolean(xmlDoc.getAttribute("group_edit"), true),
            deleteGroup: exprToBoolean(xmlDoc.getAttribute("group_delete"), true),
        };
        treeAttr.activeActions = activeActions;

        treeAttr.className = xmlDoc.getAttribute("class") || null;
        treeAttr.editable = xmlDoc.getAttribute("editable");
        treeAttr.multiEdit = activeActions.edit
            ? exprToBoolean(xmlDoc.getAttribute("multi_edit") || "")
            : false;

        treeAttr.openFormView = treeAttr.editable
            ? exprToBoolean(xmlDoc.getAttribute("open_form_view") || "")
            : false;
        treeAttr.defaultGroupBy = xmlDoc.hasAttribute("default_group_by")
            ? /** @type {string} */ (xmlDoc.getAttribute("default_group_by")).split(",")
            : null;

        const limitAttr = xmlDoc.getAttribute("limit");
        treeAttr.limit = limitAttr && Number.parseInt(limitAttr, 10);

        const countLimitAttr = xmlDoc.getAttribute("count_limit");
        treeAttr.countLimit = countLimitAttr && Number.parseInt(countLimitAttr, 10);

        const groupsLimitAttr = xmlDoc.getAttribute("groups_limit");
        treeAttr.groupsLimit = groupsLimitAttr && Number.parseInt(groupsLimitAttr, 10);

        treeAttr.noOpen = exprToBoolean(xmlDoc.getAttribute("no_open") || "");
        treeAttr.rawExpand = xmlDoc.getAttribute("expand");
        treeAttr.decorations = getDecoration(nodeAttrs(xmlDoc));

        treeAttr.defaultOrder = stringToOrderBy(
            xmlDoc.getAttribute("default_order") || null,
        );

        const action = xmlDoc.getAttribute("action");
        const type = xmlDoc.getAttribute("type");
        treeAttr.openAction = action && type ? { action, type } : null;
        return undefined;
    }

    /**
     * @param {Element} xmlDoc
     * @param {Record<string, any>} models
     * @param {string} modelName
     * @returns {{
     * controls: any[],
     * headerButtons: any[],
     * fieldNodes: Record<string, any>,
     * widgetNodes: Record<string, any>,
     * columns: any[],
     * groupBy: { buttons: Record<string, any[]>, fields: Record<string, any> },
     * xmlDoc: Element,
     * activeActions: Record<string, any>,
     * [key: string]: any,
     * }}
     */
    parse(xmlDoc, models, modelName) {
        const state = this.newParseState(xmlDoc, models, modelName);
        visitXML(xmlDoc, (node) => this.visitNode(node, state));

        const { treeAttr, handleField } = state;
        if (!treeAttr.defaultOrder.length && handleField) {
            treeAttr.defaultOrder = stringToOrderBy(`${handleField}, id`);
        }

        return {
            controls: state.controls,
            headerButtons: state.headerButtons,
            fieldNodes: state.fieldNodes,
            widgetNodes: state.widgetNodes,
            columns: state.columns,
            groupBy: state.groupBy,
            xmlDoc,
            ...treeAttr,
        };
    }
}
