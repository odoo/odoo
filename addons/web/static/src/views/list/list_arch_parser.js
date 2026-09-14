// @ts-check
/** @odoo-module native */

import { deepCopy } from "@web/core/utils/collections/objects";
import { getDecoration } from "@web/core/utils/decorations";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { stringToOrderBy } from "@web/core/utils/order_by";
import { combineModifiers } from "@web/model/relational_model";
import { parseFieldNode } from "@web/views/field_arch";
import { irToElement, literalNbsp } from "@web/views/ir/view_ir";
import { irParents, ViewArchParser, visitIR } from "@web/views/view_arch_parser";
import { processButton } from "@web/views/view_buttons";
import { encodeObjectForTemplate } from "@web/views/view_compiler";
import { getActiveActions } from "@web/views/view_utils";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").ListListAttrs} ListAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").ListFieldAttrs} ListFieldAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").ListButtonAttrs} ListButtonAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").ListWidgetAttrs} ListWidgetAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").ListGroupbyAttrs} ListGroupbyAttrs
 */

/**
 * The parser annotates the tree it walks (`field_id`, `widget_id`) for the
 * compiler; the annotation goes on the node's own attrs.
 *
 * @param {ViewIRNode} node
 * @param {string} name
 * @param {string} value
 */
function annotate(node, name, value) {
    (node.attrs ??= {})[name] = value;
}

class GroupListArchParser {
    /**
     * @param {ViewIRNode} arch
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
        visitIR(arch, (node) => {
            if (node.kind === "button") {
                buttons.push({
                    ...processButton(node),
                    id: buttonId++,
                });
                return false;
            } else if (node.kind === "field") {
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
                annotate(node, "field_id", fieldId);
                return false;
            }
        });
        return { fieldNodes, buttons };
    }
}

export class ListArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * The parent of every node of the tree the last `parse()` walked — what
     * a subclass that locates a node in the arch (web studio's xpath) reads.
     * @type {Map<ViewIRNode, ViewIRNode | null>}
     */
    parents = new Map();

    /**
     * @param {ViewIRNode} node
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
     * ir: ViewIRNode,
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
     * @param {ViewIRNode} ir
     * @param {Record<string, any>} models
     * @param {string} modelName
     * @returns {ListParseState}
     */
    newParseState(ir, models, modelName) {
        return {
            ir,
            models,
            modelName,
            jsClass: ir.attrs?.js_class ?? undefined,
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
     * @param {ViewIRNode} node
     * @param {ListParseState} state
     * @returns {false | undefined}
     */
    visitNode(node, state) {
        if (node.kind !== "button") {
            state.buttonGroup = undefined;
        }
        switch (node.kind) {
            case "button":
                return this.parseButtonNode(node, state);
            case "field":
                return this.parseFieldColumn(node, state);
            case "widget":
                return this.parseWidgetColumn(node, state);
            case "groupby":
                return /** @type {ListGroupbyAttrs} */ (node.attrs || {}).name
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
     * @param {ViewIRNode} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseButtonNode(node, state) {
        /** @type {ListButtonAttrs} */
        const attrs = node.attrs || {};
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
                attrs.column_invisible ?? null,
                "AND",
            );
        } else {
            state.buttonGroup = /** @type {any} */ ({
                id: `column_${state.nextId++}`,
                type: "button_group",
                buttons: [button],
                hasLabel: false,
                column_invisible: attrs.column_invisible ?? null,
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
     * @param {ViewIRNode} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseFieldColumn(node, state) {
        /** @type {ListFieldAttrs} */
        const attrs = node.attrs || {};
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
        annotate(node, "field_id", fieldId);
        if (fieldInfo.isHandle) {
            state.handleField = fieldInfo.name;
        }
        const label = fieldInfo.field.label;
        state.columns.push({
            ...fieldInfo,
            id: `column_${state.nextId++}`,
            className: attrs.class ?? null,
            optional: attrs.optional || false,
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
     * @param {ViewIRNode} node
     * @param {ListParseState} state
     * @returns {undefined}
     */
    parseWidgetColumn(node, state) {
        const widgetInfo = this.parseWidgetNode(node);
        const widgetId = `widget_${++state.widgetNextId}`;
        state.widgetNodes[widgetId] = widgetInfo;
        annotate(node, "widget_id", widgetId);

        const widgetProps = {
            name: widgetInfo.name,
            node: encodeObjectForTemplate({ attrs: widgetInfo.attrs }).slice(1, -1),
            className: /** @type {ListWidgetAttrs} */ (node.attrs || {}).class || "",
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
     * @param {ViewIRNode} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseGroupByNode(node, state) {
        const fieldName = /** @type {string} */ (node.attrs?.name);
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
     * @param {ViewIRNode} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseHeaderNode(node, state) {
        state.headerButtons = this.parseHeaderButtons(node, state.buttonId);
        state.buttonId += state.headerButtons.length;
        return false;
    }

    /**
     * @param {ViewIRNode} node
     * @param {ListParseState} state
     * @returns {false}
     */
    parseControlNode(node, state) {
        state.controls.push(...this.parseControls(node));
        return false;
    }

    /**
     * @param {ViewIRNode} _node
     * @param {ListParseState} state
     * @returns {undefined}
     */
    parseRootNode(_node, state) {
        const { ir, treeAttr } = state;
        /** @type {ListAttrs} */
        const attrs = ir.attrs || {};
        const activeActions = {
            ...getActiveActions(ir),
            exportXlsx: exprToBoolean(attrs.export_xlsx, true),
            createGroup: exprToBoolean(attrs.group_create, true),
            editGroup: exprToBoolean(attrs.group_edit, true),
            deleteGroup: exprToBoolean(attrs.group_delete, true),
        };
        treeAttr.activeActions = activeActions;

        treeAttr.className = attrs.class || null;
        treeAttr.editable = attrs.editable ?? null;
        treeAttr.multiEdit = activeActions.edit
            ? exprToBoolean(attrs.multi_edit || "")
            : false;

        treeAttr.openFormView = treeAttr.editable
            ? exprToBoolean(attrs.open_form_view || "")
            : false;
        treeAttr.defaultGroupBy =
            attrs.default_group_by !== undefined
                ? attrs.default_group_by.split(",")
                : null;

        const limitAttr = attrs.limit ?? null;
        treeAttr.limit = limitAttr && Number.parseInt(limitAttr, 10);

        const countLimitAttr = attrs.count_limit ?? null;
        treeAttr.countLimit = countLimitAttr && Number.parseInt(countLimitAttr, 10);

        const groupsLimitAttr = attrs.groups_limit ?? null;
        treeAttr.groupsLimit = groupsLimitAttr && Number.parseInt(groupsLimitAttr, 10);

        treeAttr.noOpen = exprToBoolean(attrs.no_open || "");
        treeAttr.rawExpand = attrs.expand ?? null;
        treeAttr.decorations = getDecoration(
            /** @type {Record<string, string>} */ (attrs),
        );

        treeAttr.defaultOrder = stringToOrderBy(attrs.default_order || null);

        const action = attrs.action;
        const type = attrs.type;
        treeAttr.openAction = action && type ? { action, type } : null;
        return undefined;
    }

    /**
     * The tree the parser annotates is its own copy: the node handed in may
     * be the view cache's IR, or a child of the parent view's tree when this
     * is an x2many sub-view. `xmlDoc` is that annotated copy materialised
     * for the compiler, the way `View` materialises a top-level arch.
     *
     * @param {ViewIRNode | Element | string} arch
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
    parse(arch, models, modelName) {
        const ir = deepCopy(this.toIR(arch));
        const state = this.newParseState(ir, models, modelName);
        this.parents = irParents(ir);
        visitIR(ir, (node) => this.visitNode(node, state));

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
            xmlDoc: irToElement(ir, { text: literalNbsp }),
            ...treeAttr,
        };
    }
}
