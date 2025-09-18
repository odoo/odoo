// @ts-check

/** @module views/list/list_column_utils - Column processing utilities for ListRenderer */

/** @import { DynamicList } from "@web/model/relational_model/dynamic_list" */
/** @import { StaticList } from "@web/model/relational_model/static_list" */

/**
 * @typedef {Object} Column
 * @property {string} type
 * @property {string} name
 * @property {string} id
 * @property {string} [label]
 * @property {string} [widget]
 * @property {boolean} [hasLabel]
 * @property {string} [optional]
 * @property {string} [classNames]
 * @property {string} [column_invisible]
 * @property {Object} [attrs]
 * @property {Object} [relatedPropertyField]
 */

import { getPropertyFieldInfo } from "@web/fields/field";
import { combineModifiers } from "@web/model/relational_model/utils";

/**
 * Expand property fields into individual columns.
 *
 * @param {Column} column - a column of type "field" with a properties field
 * @param {DynamicList | StaticList} list
 * @returns {Column[]} expanded property columns
 */
export function getPropertyFieldColumns(column, list) {
    return /** @type {any[]} */ (Object.values(list.fields))
        .filter(
            (field) =>
                list.activeFields[field.name] &&
                field.relatedPropertyField &&
                field.relatedPropertyField.name === column.name &&
                field.type !== "separator",
        )
        .map((propertyField) => {
            const activeField = list.activeFields[propertyField.name];
            return {
                ...getPropertyFieldInfo(propertyField),
                relatedPropertyField: activeField.relatedPropertyField,
                id: `${column.id}_${propertyField.name}`,
                column_invisible: combineModifiers(
                    propertyField.column_invisible,
                    column.column_invisible,
                    "OR",
                ),
                classNames: column.classNames,
                optional: "hide",
                type: "field",
                hasLabel: true,
                label: propertyField.string,
                attrs: ["integer", "float"].includes(propertyField.type)
                    ? { sum: propertyField.string }
                    : {},
            };
        });
}

/**
 * Process all columns, expanding properties fields into individual columns.
 *
 * @param {Column[]} allColumns
 * @param {DynamicList | StaticList} list
 * @returns {Column[]}
 */
export function processAllColumns(allColumns, list) {
    return allColumns.flatMap((column) => {
        if (column.type === "field" && list.fields[column.name].type === "properties") {
            return getPropertyFieldColumns(column, list);
        } else {
            return [column];
        }
    });
}
