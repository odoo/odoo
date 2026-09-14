// @ts-check
/** @odoo-module native */

import { deepCopy } from "@web/core/utils/collections/objects";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { stringToOrderBy } from "@web/core/utils/order_by";
import { parseFieldNode } from "@web/views/field_arch";
import { irToElement, literalNbsp } from "@web/views/ir/view_ir";
import {
    irParents,
    requiredIRAttribute,
    ViewArchParser,
    visitIR,
} from "@web/views/view_arch_parser";
import { getActiveActions } from "@web/views/view_utils";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").KanbanKanbanAttrs} KanbanAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").KanbanFieldAttrs} KanbanFieldAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").KanbanProgressbarAttrs} KanbanProgressbarAttrs
 */

/** @param {string | null | undefined} value */
function parseIntAttribute(value) {
    return value ? Number.parseInt(value, 10) : null;
}

/**
 * @param {ViewIRNode} node
 * @param {string} name
 * @param {string} value
 */
function annotate(node, name, value) {
    (node.attrs ??= {})[name] = value;
}

/**
 * @param {ViewIRNode} ir
 * @param {string} kind
 * @returns {ViewIRNode | null}
 */
function findKind(ir, kind) {
    /** @type {ViewIRNode | null} */
    let found = null;
    visitIR(ir, (node) => {
        if (found) {
            return false;
        }
        if (node.kind === kind) {
            found = node;
            return false;
        }
    });
    return found;
}

export const KANBAN_CARD_ATTRIBUTE = "card";
export const KANBAN_MENU_ATTRIBUTE = "menu";

export class KanbanArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * The parent of every node of the tree the last `parse()` walked — what
     * a subclass that locates a node in the arch (web studio's xpath) reads.
     * @type {Map<ViewIRNode, ViewIRNode | null>}
     */
    parents = new Map();

    /**
     * @typedef {{
     * ir: ViewIRNode,
     * models: Record<string, any>,
     * modelName: string,
     * jsClass: string | undefined,
     * templateNames: string[],
     * headerButtons: any[],
     * controls: any[],
     * fieldNodes: Record<string, any>,
     * fieldNextIds: Record<string, number>,
     * widgetNodes: Record<string, any>,
     * widgetNextId: number,
     * tooltipInfo: Record<string, any>,
     * handleField: string | null,
     * }} KanbanParseState
     */

    /**
     * @param {ViewIRNode} ir
     * @returns {{
     * activeActions: any,
     * className: string | null,
     * canOpenRecords: boolean,
     * defaultOrder: any[],
     * limit: number | null,
     * countLimit: number | null,
     * recordsDraggable: boolean,
     * groupsDraggable: boolean,
     * defaultGroupBy: string[] | null,
     * onCreate: string | null,
     * quickCreateView: string | null,
     * openAction: { action: string, type: string } | null,
     * }}
     */
    parseRootAttributes(ir) {
        /** @type {KanbanAttrs} */
        const attrs = ir.attrs || {};
        /** @type {any} */
        const activeActions = getActiveActions(ir);
        activeActions.archiveGroup = exprToBoolean(attrs.archivable, true);
        activeActions.createGroup = exprToBoolean(attrs.group_create, true);
        activeActions.deleteGroup = exprToBoolean(attrs.group_delete, true);
        activeActions.editGroup = exprToBoolean(attrs.group_edit, true);
        activeActions.quickCreate =
            activeActions.create && exprToBoolean(attrs.quick_create, true);

        const action = attrs.action;
        const type = attrs.type;
        return {
            activeActions,
            className: attrs.class || null,
            canOpenRecords: exprToBoolean(attrs.can_open, true),
            defaultOrder: stringToOrderBy(attrs.default_order || null),
            limit: parseIntAttribute(attrs.limit),
            countLimit: parseIntAttribute(attrs.count_limit),
            recordsDraggable: exprToBoolean(attrs.records_draggable, true),
            groupsDraggable: exprToBoolean(attrs.groups_draggable, true),
            defaultGroupBy:
                attrs.default_group_by !== undefined
                    ? attrs.default_group_by.split(",")
                    : null,
            onCreate: attrs.on_create ?? null,
            quickCreateView: attrs.quick_create_view ?? null,
            openAction: action && type ? { action, type } : null,
        };
    }

    /**
     * @param {ViewIRNode} ir
     * @param {Record<string, any>} models
     * @param {string} modelName
     * @returns {KanbanParseState}
     */
    newParseState(ir, models, modelName) {
        return {
            ir,
            models,
            modelName,
            jsClass: ir.attrs?.js_class ?? undefined,
            templateNames: [],
            headerButtons: [],
            controls: [],
            fieldNodes: {},
            fieldNextIds: {},
            widgetNodes: {},
            widgetNextId: 0,
            tooltipInfo: {},
            handleField: null,
        };
    }

    /**
     * @param {ViewIRNode} node
     * @param {KanbanParseState} state
     * @returns {false | undefined}
     */
    visitNode(node, state) {
        const templateName = node.attrs?.["t-name"];
        if (templateName !== undefined) {
            state.templateNames.push(templateName);
            return undefined;
        }
        switch (node.kind) {
            case "header":
                state.headerButtons = this.parseHeaderButtons(node);
                return false;
            case "control":
                state.controls.push(...this.parseControls(node));
                return false;
            case "field":
                return this.parseFieldNodeInArch(node, state);
            case "widget":
                return this.parseWidgetNodeInArch(node, state);
            case "img":
                return this.parseImageNode(node, state);
            default:
                return undefined;
        }
    }

    /**
     * @param {ViewIRNode} node
     * @param {KanbanParseState} state
     * @returns {undefined}
     */
    parseFieldNodeInArch(node, state) {
        const { models, modelName } = state;
        const fieldName = requiredIRAttribute(node, "name");
        const field = models[modelName].fields[fieldName];
        if (!field) {
            throw new Error(
                `Kanban arch parsing error: <field name="${fieldName}"/> does not exist on model "${modelName}"`,
            );
        }
        const widget = /** @type {KanbanFieldAttrs} */ (node.attrs || {}).widget;
        if (!widget && field.type === "many2many") {
            annotate(node, "widget", "many2many_tags");
        }
        const fieldInfo = parseFieldNode(
            node,
            models,
            modelName,
            "kanban",
            state.jsClass,
        );
        const name = fieldInfo.name;
        if (!(fieldInfo.name in state.fieldNextIds)) {
            state.fieldNextIds[fieldInfo.name] = 0;
        }
        const fieldId = `${fieldInfo.name}_${state.fieldNextIds[fieldInfo.name]++}`;
        state.fieldNodes[fieldId] = fieldInfo;
        annotate(node, "field_id", fieldId);
        if (fieldInfo.options.group_by_tooltip) {
            state.tooltipInfo[name] = fieldInfo.options.group_by_tooltip;
        }
        if (fieldInfo.isHandle) {
            state.handleField = name;
        }
        return undefined;
    }

    /**
     * @param {ViewIRNode} node
     * @param {KanbanParseState} state
     * @returns {undefined}
     */
    parseWidgetNodeInArch(node, state) {
        const widgetInfo = this.parseWidgetNode(node);
        const widgetId = `widget_${++state.widgetNextId}`;
        state.widgetNodes[widgetId] = widgetInfo;
        annotate(node, "widget_id", widgetId);
        return undefined;
    }

    /**
     * @param {ViewIRNode} node
     * @param {KanbanParseState} state
     * @returns {undefined}
     */
    parseImageNode(node, state) {
        const attSrc = node.attrs?.["t-att-src"];
        if (
            attSrc &&
            /\bkanban_image\b/.test(attSrc) &&
            !Object.values(state.fieldNodes).some((f) => f.name === "write_date")
        ) {
            state.fieldNodes.write_date_0 = {
                name: "write_date",
                type: "datetime",
            };
        }
        return undefined;
    }

    /**
     * The tree the parser annotates is its own copy (the node handed in may be
     * the view cache's IR, or a child of the parent view's tree for an x2many
     * sub-view); `xmlDoc` and the `templateDocs` the compiler walks are that
     * annotated copy materialised.
     *
     * @param {ViewIRNode | Element | string} arch
     * @param {Object} models
     * @param {string} modelName
     * @returns {{
     * activeActions: Object,
     * canOpenRecords: boolean,
     * cardClassName: string,
     * cardColorField: string | null,
     * className: string | null,
     * controls: Object[],
     * defaultGroupBy: string[] | null,
     * fieldNodes: Object,
     * widgetNodes: Object,
     * handleField: string | null,
     * headerButtons: Object[],
     * defaultOrder: Object[],
     * onCreate: string | null,
     * openAction: { action: string, type: string } | null,
     * quickCreateView: string | null,
     * recordsDraggable: boolean,
     * groupsDraggable: boolean,
     * limit: number | null,
     * countLimit: number | null,
     * progressAttributes: Object | false,
     * templateDocs: Object,
     * tooltipInfo: Object,
     * examples: string | null,
     * xmlDoc: Element,
     * }}
     */
    parse(arch, models, modelName) {
        const ir = deepCopy(this.toIR(arch));
        const root = this.parseRootAttributes(ir);
        const state = this.newParseState(ir, models, modelName);
        this.parents = irParents(ir);
        visitIR(ir, (node) => this.visitNode(node, state));

        /** @type {any} */
        let progressAttributes = false;
        const progressBar = findKind(ir, "progressbar");
        if (progressBar) {
            progressAttributes = this.parseProgressBar(
                progressBar,
                models[modelName].fields,
            );
        }

        if (!state.templateNames.includes(KANBAN_CARD_ATTRIBUTE)) {
            throw new Error(`Missing '${KANBAN_CARD_ATTRIBUTE}' template.`);
        }
        const xmlDoc = irToElement(ir, { text: literalNbsp });
        /** @type {Record<string, Element>} */
        const templateDocs = {};
        for (const templateDoc of xmlDoc.querySelectorAll("[t-name]")) {
            templateDocs[/** @type {string} */ (templateDoc.getAttribute("t-name"))] =
                templateDoc;
        }
        const cardDoc = templateDocs[KANBAN_CARD_ATTRIBUTE];

        let { defaultOrder } = root;
        if (!defaultOrder.length && state.handleField) {
            defaultOrder = stringToOrderBy(`${state.handleField}, id`);
        }

        return {
            ...root,
            defaultOrder,
            cardClassName: cardDoc.getAttribute("class") || "",
            cardColorField: ir.attrs?.highlight_color ?? null,
            controls: state.controls,
            fieldNodes: state.fieldNodes,
            widgetNodes: state.widgetNodes,
            handleField: state.handleField,
            headerButtons: state.headerButtons,
            progressAttributes,
            templateDocs,
            tooltipInfo: state.tooltipInfo,
            examples: ir.attrs?.examples ?? null,
            xmlDoc,
        };
    }

    /**
     * @param {ViewIRNode} progressBar
     * @param {Object} fields
     * @returns {{ fieldName: string, colors: Object, sumField: Object | false, help: string }}
     */
    parseProgressBar(progressBar, fields) {
        /** @type {KanbanProgressbarAttrs} */
        const nodeAttributes = progressBar.attrs || {};
        // extractAttributes' contract: an absent attribute reads ""
        const attrs = {
            field: nodeAttributes.field ?? "",
            colors: nodeAttributes.colors ?? "",
            sum_field: nodeAttributes.sum_field ?? "",
            help: nodeAttributes.help ?? "",
        };
        let colors;
        try {
            colors = JSON.parse(attrs.colors);
        } catch (error) {
            throw new Error(
                `Kanban arch parsing error: invalid "colors" attribute on <progressbar/> (must be a JSON object mapping field values to color names): ${error.message}`,
                { cause: error },
            );
        }
        return {
            fieldName: attrs.field,
            colors,
            sumField: fields[attrs.sum_field] || false,
            help: attrs.help,
        };
    }
}
