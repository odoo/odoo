/** @odoo-module */

import { Field } from "../../fields/field";
import { evaluateExpr } from "../../core/py_js/py";
import { isAttr } from "../../core/utils/xml";
import { archParseBoolean } from "./utils";

const X2M_TYPES = ["one2many", "many2many"];
const RELATIONAL_TYPES = [...X2M_TYPES, "many2one"];

/**
 * @param {any} field
 * @returns {boolean}
 */
export const isRelational = (field) => field && RELATIONAL_TYPES.includes(field.type);

/**
 * @param {any} field
 * @returns {boolean}
 */
export const isX2Many = (field) => field && X2M_TYPES.includes(field.type);

/**
 * @param {string | string[]} [mode]
 * @returns {string[]}
 */
export const getX2MViewModes = (mode) => {
    if (!mode) {
        return ["list"];
    }
    const modes = Array.isArray(mode) ? mode : mode.split(",");
    return modes.map((m) => (m === "tree" ? "list" : m));
};

/**
 * @param {number | number[]} idsList
 * @returns {number[]}
 */
export const getIds = (idsList) => {
    if (Array.isArray(idsList)) {
        if (idsList.length === 2 && typeof idsList[1] === "string") {
            return [idsList[0]];
        } else {
            return idsList;
        }
    } else if (idsList) {
        return [idsList];
    } else {
        return [];
    }
};

export function processField(node, fields, viewType) {
    const name = node.getAttribute("name");
    const widget = node.getAttribute("widget");
    const modifiers = evaluateExpr(node.getAttribute("modifiers") || "{}");
    const field = fields[name];
    const fieldInfo = {
        name,
        string: node.getAttribute("string") || field.string,
        widget,
        onChange: archParseBoolean(node.getAttribute("on_change")),
        options: evaluateExpr(node.getAttribute("options") || "{}"),
        invisible: modifiers.invisible === true, // || modifiers.column_invisible === true;
        attrs: {},
    };
    for (const attribute of node.attributes) {
        // FIXME: black list special attributes like on_change, name... ?
        fieldInfo.attrs[attribute.name] = attribute.value;
    }
    if (!fieldInfo.invisible && X2M_TYPES.includes(field.type)) {
        fieldInfo.relation = field.relation;
        const relatedFields = {
            id: { name: "id", type: "integer", readonly: true },
        };
        const FieldClass = Field.getTangibleField({ fields, viewType }, widget, name);
        if (FieldClass.useSubView) {
            // FIXME: this part is incomplete, we have to parse the subview archs
            // and extract the field info
            fieldInfo.viewMode = getX2MViewModes(node.getAttribute("mode"))[0];
            fieldInfo.views = field.views;
            const firstView = fieldInfo.views[fieldInfo.viewMode];
            if (firstView) {
                Object.assign(relatedFields, firstView.fields);
            }
        }
        // add fields required by specific FieldComponents
        Object.assign(relatedFields, FieldClass.fieldsToFetch);
        // special case for color field
        const colorField = fieldInfo.options.color_field;
        if (colorField) {
            relatedFields[colorField] = { name: colorField, type: "integer" };
        }
        fieldInfo.relatedFields = relatedFields;
    }
    return fieldInfo;
}

export function getActiveActions(rootNode) {
    return {
        edit: isAttr(rootNode, "edit").truthy(true),
        create: isAttr(rootNode, "create").truthy(true),
        delete: isAttr(rootNode, "delete").truthy(true),
        duplicate: isAttr(rootNode, "duplicate").truthy(true),
    };
}
