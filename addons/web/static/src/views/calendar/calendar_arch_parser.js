// @ts-check
/** @odoo-module native */

import { evaluateExpr } from "@web/core/py_js/py";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { parseFieldNode } from "@web/views/field_arch";

import { ViewArchParser, visitIR } from "../view_arch_parser.js";

/**
 * @typedef {import("@web/views/ir/view_ir_schema").ViewIRNode} ViewIRNode
 * @typedef {import("@web/views/ir/view_ir_schema").CalendarCalendarAttrs} CalendarAttrs
 * @typedef {import("@web/views/ir/view_ir_schema").CalendarFieldAttrs} CalendarFieldAttrs
 */

const FIELD_ATTRIBUTE_NAMES = [
    "date_start",
    "date_delay",
    "date_stop",
    "all_day",
    "create_name_field",
    "color",
];
const SCALES = ["day", "week", "month", "year"];

class CalendarParseArchError extends Error {}

/** @type {string[]} */
const FILTER_ATTRIBUTE_NAMES = [
    "avatar_field",
    "write_model",
    "write_field",
    "color",
    "filters",
];

export class CalendarArchParser extends ViewArchParser {
    /** @type {"element" | "ir"} */
    static consumes = "ir";

    /**
     * @param {ViewIRNode | Element | string} arch
     * @param {Object} models
     * @param {string} modelName
     * @returns {Object}
     * @throws {CalendarParseArchError}
     */
    parse(arch, models, modelName) {
        const ir = this.toIR(arch);
        const fields = models[modelName].fields;
        const root = this.parseRootAttributes(ir, fields);
        const state = {
            models,
            modelName,
            fields,
            jsClass: root.jsClass,
            fieldNames: root.fieldNames,
            /** @type {Record<string, any>} */
            popoverFieldNodes: {},
            /** @type {Record<string, any>} */
            filtersInfo: {},
        };

        visitIR(ir, (node) => {
            if (node.kind === "field") {
                this.parseFieldNodeInArch(node, state);
            }
        });

        this.validate(root);

        return {
            aggregate: root.aggregate,
            canCreate: root.canCreate,
            canDelete: root.canDelete,
            canEdit: root.canEdit,
            eventLimit: root.eventLimit,
            fieldMapping: root.fieldMapping,
            fieldNames: [...state.fieldNames],
            filtersInfo: state.filtersInfo,
            formViewId: root.formViewId,
            hasEditDialog: root.hasEditDialog,
            multiCreateView: root.multiCreateView,
            quickCreate: root.quickCreate,
            quickCreateViewId: root.quickCreateViewId,
            isDateHidden: root.isDateHidden,
            isTimeHidden: root.isTimeHidden,
            monthOverflow: root.monthOverflow,
            popoverFieldNodes: state.popoverFieldNodes,
            scale: root.scale,
            scales: root.scales,
            showUnusualDays: root.showUnusualDays,
            showDatePicker: root.showDatePicker,
        };
    }

    /**
     * @param {ViewIRNode} ir
     * @param {Record<string, any>} fields
     * @returns {Record<string, any>}
     */
    parseRootAttributes(ir, fields) {
        /** @type {CalendarAttrs} */
        const attrs = ir.attrs || {};
        /** @type {Record<string, string>} */
        const fieldMapping = {};
        /** @type {Set<string>} */
        const fieldNames = new Set(fields.display_name ? ["display_name"] : []);
        for (const fieldAttrName of FIELD_ATTRIBUTE_NAMES) {
            const fieldName = attrs[fieldAttrName];
            if (fieldName !== undefined) {
                fieldNames.add(fieldName);
                fieldMapping[fieldAttrName] = fieldName;
            }
        }
        const aggregate = attrs.aggregate || null;
        if (aggregate) {
            fieldNames.add(aggregate.split(":")[0]);
        }

        const scales = attrs.scales
            ? attrs.scales
                  .split(",")
                  .map((scale) => scale.trim())
                  .filter((scale) => SCALES.includes(scale))
            : [...SCALES];
        const scale = attrs.mode ?? (scales.includes("week") ? "week" : scales[0]);

        const quickCreate = exprToBoolean(attrs.quick_create, true);
        return {
            fieldMapping,
            fieldNames,
            aggregate,
            scales,
            scale,
            quickCreate,
            canCreate: exprToBoolean(attrs.create, true),
            canDelete: exprToBoolean(attrs.delete, true),
            canEdit: exprToBoolean(attrs.edit, true),
            eventLimit:
                attrs.event_limit !== undefined ? evaluateExpr(attrs.event_limit) : 5,
            formViewId: Number.parseInt(attrs.form_view_id ?? "", 10) || false,
            hasEditDialog: exprToBoolean(attrs.event_open_popup),
            isDateHidden: exprToBoolean(attrs.hide_date),
            isTimeHidden: exprToBoolean(attrs.hide_time),
            jsClass: attrs.js_class || null,
            monthOverflow: exprToBoolean(attrs.month_overflow, true),
            multiCreateView: attrs.multi_create_view ?? null,
            quickCreateViewId:
                (quickCreate &&
                    Number.parseInt(attrs.quick_create_view_id ?? "", 10)) ||
                null,
            showDatePicker: exprToBoolean(attrs.show_date_picker, true),
            showUnusualDays: exprToBoolean(attrs.show_unusual_days),
        };
    }

    /**
     * @param {ViewIRNode} node
     * @param {Record<string, any>} state
     */
    parseFieldNodeInArch(node, state) {
        /** @type {CalendarFieldAttrs} */
        const attrs = node.attrs || {};
        const fieldName = /** @type {string} */ (attrs.name);
        state.fieldNames.add(fieldName);
        const fieldInfo = parseFieldNode(
            node,
            state.models,
            state.modelName,
            "calendar",
            state.jsClass,
        );
        state.popoverFieldNodes[fieldName] = fieldInfo;

        if (attrs.invisible !== undefined && attrs.filters === undefined) {
            return;
        }
        if (!FILTER_ATTRIBUTE_NAMES.some((attr) => attr in attrs)) {
            return;
        }
        state.filtersInfo[fieldName] = this.getFilterInfo(node, fieldName, {
            field: state.fields[fieldName],
            context: fieldInfo.context || "{}",
            previous: state.filtersInfo[fieldName],
        });
    }

    /**
     * @param {ViewIRNode} node
     * @param {string} fieldName
     * @param {{ field: any, context: string, previous?: any }} params
     * @returns {Record<string, any>}
     */
    getFilterInfo(node, fieldName, { field, context, previous }) {
        /** @type {CalendarFieldAttrs} */
        const attrs = node.attrs || {};
        const filterInfo = previous || {
            avatarFieldName: null,
            colorFieldName: null,
            context,
            fieldName,
            filterFieldName: null,
            label: field.string,
            resModel: field.relation,
            writeFieldName: null,
            writeResModel: null,
        };
        filterInfo.avatarFieldName = attrs.avatar_field || null;
        filterInfo.colorFieldName =
            (attrs.filters !== undefined && attrs.color) || null;
        filterInfo.filterFieldName = attrs.filter_field || null;
        filterInfo.writeFieldName = attrs.write_field || null;
        filterInfo.writeResModel = attrs.write_model || null;
        return filterInfo;
    }

    /**
     * @param {Record<string, any>} root
     * @throws {CalendarParseArchError}
     */
    validate(root) {
        if (!root.fieldMapping.date_start) {
            throw new CalendarParseArchError(
                `Calendar view must define "date_start" attribute.`,
            );
        }
        if (!root.scales.includes(root.scale)) {
            throw new CalendarParseArchError(
                `Calendar view cannot display mode: ${root.scale}`,
            );
        }
        if (!Number.isInteger(root.eventLimit)) {
            throw new CalendarParseArchError(
                `Calendar view's event limit should be a number`,
            );
        }
    }
}
