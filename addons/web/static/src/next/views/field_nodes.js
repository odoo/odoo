import { getTag } from "@web/core/utils/xml";
import { FallbackField } from "../fields/fallback_field";
import { fieldRegistry } from "../fields/field";

/**
 * @typedef {import("../fields/field").FieldNode} FieldNode
 * @typedef {import("./view_models").Specification} Specification
 * @typedef {import("./view_models").RelatedModels} RelatedModels
 */

/**
 * Describes a field node of an arch: its component, and the columns of its
 * list for an x2many. Its id is its name: a view that displays a field more
 * than once makes the ids unique.
 *
 * @param {Element} el
 * @param {string} modelName
 * @param {RelatedModels} relatedModels
 * @returns {FieldNode}
 */
export function parseFieldNode(el, modelName, relatedModels) {
    const name = el.getAttribute("name");
    const field = relatedModels[modelName]?.fields[name];
    if (!field) {
        throw new Error(`Field "${name}" does not exist on model "${modelName}"`);
    }
    const widget = el.getAttribute("widget") || null;
    /** @type {FieldNode} */
    const node = {
        id: name,
        name,
        type: field.type,
        relation: field.relation || null,
        field,
        widget,
        string: el.getAttribute("string") || field.string || name,
        readonly: Boolean(field.readonly),
        className: el.getAttribute("class"),
        style: el.getAttribute("style"),
        Widget: getFieldComponent(widget, field.type),
    };
    if (field.type === "one2many" || field.type === "many2many") {
        const list = [...el.children].find((child) => getTag(child, true) === "list");
        node.list = {
            columns: list
                ? parseListColumns(list, field.relation, relatedModels)
                : [displayNameColumn()],
        };
    }
    return node;
}

/**
 * The columns of a list arch: its fields, without the ones that are always
 * hidden (`column_invisible="1"`) or hidden by default (`optional="hide"`).
 *
 * @param {Element} list
 * @param {string} modelName
 * @param {RelatedModels} relatedModels
 * @returns {FieldNode[]}
 */
export function parseListColumns(list, modelName, relatedModels) {
    const columns = [];
    for (const el of list.children) {
        const isHidden =
            isTrue(el.getAttribute("column_invisible")) || el.getAttribute("optional") === "hide";
        if (getTag(el, true) !== "field" || isHidden) {
            continue;
        }
        const column = parseFieldNode(el, modelName, relatedModels);
        column.id = `${column.name}_${columns.length}`;
        if (isTrue(el.getAttribute("nolabel"))) {
            column.string = "";
        }
        columns.push(column);
    }
    return columns;
}

/**
 * The `specification` of `web_read`, `web_search_read` and `web_save` for the
 * given field nodes: the fields of x2many sub-views, and the display name of
 * other relations.
 *
 * @param {FieldNode[]} nodes
 * @returns {Specification}
 */
export function buildSpecification(nodes) {
    /** @type {Specification} */
    const specification = {};
    for (const node of nodes) {
        let fieldSpec = {};
        if (node.list) {
            fieldSpec = { fields: buildSpecification(node.list.columns) };
        } else if (node.relation) {
            fieldSpec = { fields: { display_name: {} } };
        }
        specification[node.name] = mergeSpecifications(specification[node.name], fieldSpec);
    }
    return specification;
}

/**
 * A field can appear more than once in an arch: it reads what all its nodes
 * read.
 *
 * @param {{ fields?: Specification } | undefined} a
 * @param {{ fields?: Specification }} b
 */
function mergeSpecifications(a, b) {
    if (!a?.fields || !b.fields) {
        return a?.fields ? a : b;
    }
    const fields = { ...a.fields };
    for (const [name, spec] of Object.entries(b.fields)) {
        fields[name] = mergeSpecifications(fields[name], spec);
    }
    return { fields };
}

/**
 * The component of a field: the one of its widget, else the one of its type,
 * else one that displays its value as text.
 *
 * @param {string | null} widget
 * @param {string} type
 */
function getFieldComponent(widget, type) {
    return (
        (widget && fieldRegistry.get(widget, null)) ||
        fieldRegistry.get(type, null) ||
        FallbackField
    );
}

/**
 * The column of an x2many without list sub-view: the display name of its
 * records.
 *
 * @returns {FieldNode}
 */
function displayNameColumn() {
    return {
        id: "display_name_0",
        name: "display_name",
        type: "char",
        relation: null,
        field: { type: "char" },
        widget: null,
        string: "",
        readonly: true,
        className: null,
        style: null,
        Widget: getFieldComponent(null, "char"),
    };
}

/**
 * @param {string | null} value an attribute that is a constant boolean
 */
function isTrue(value) {
    return value === "1" || value === "True";
}
