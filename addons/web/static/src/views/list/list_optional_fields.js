// @ts-check

/** @module @web/views/list/list_optional_fields - Hook managing localStorage-backed optional column visibility for the list view */

/** @odoo-module **/

/**
 * Hook encapsulating optional field visibility management for the list view.
 *
 * Handles reading/writing the localStorage-backed set of visible optional columns,
 * as well as the debug "open form view" toggle.
 *
 * @param {string} keyOptionalFields - localStorage key for optional field state
 * @param {string} keyDebugOpenView - localStorage key for debug open-view toggle
 * @param {object} options
 * @param {() => import("./list_renderer").Column[]} options.getAllColumns - returns allColumns
 * @param {() => Record<string, boolean>} options.getOptionalActiveFields - returns the shared state
 * @param {() => void} options.onSave - callback to persist (routes through class for override support)
 * @returns {{
 *   debugOpenView: boolean,
 *   computeOptionalActiveFields: () => Record<string, boolean>,
 *   saveOptionalActiveFields: () => void,
 *   refreshDebugOpenView: () => void,
 *   toggleOptionalField: (fieldName: string, render: () => void) => void,
 *   toggleOptionalFieldGroup: (groupId: string, render: () => void) => void,
 *   toggleDebugOpenView: (render: () => void) => void,
 * }}
 */
import { browser } from "@web/core/browser/browser";
import { exprToBoolean } from "@web/core/utils/format/strings";
export function useListOptionalFields(
    keyOptionalFields,
    keyDebugOpenView,
    { getAllColumns, getOptionalActiveFields, onSave },
) {
    const self = {
        debugOpenView: false,

        /**
         * Compute which optional fields are active from localStorage or defaults.
         */
        computeOptionalActiveFields() {
            const localStorageValue = browser.localStorage.getItem(keyOptionalFields);
            const optionalColumns = getAllColumns().filter(
                (col) => col.type === "field" && col.optional,
            );
            const result = {};
            if (localStorageValue !== null) {
                const active = localStorageValue.split(",");
                for (const col of optionalColumns) {
                    result[col.name] = active.includes(col.name);
                }
            } else {
                for (const col of optionalColumns) {
                    result[col.name] = col.optional === "show";
                }
            }
            return result;
        },

        /**
         * Persist the current optional field visibility to localStorage.
         */
        saveOptionalActiveFields() {
            const optionalActiveFields = getOptionalActiveFields();
            browser.localStorage.setItem(
                keyOptionalFields,
                /** @type {any} */ (
                    Object.keys(optionalActiveFields).filter(
                        (fieldName) => optionalActiveFields[fieldName],
                    )
                ),
            );
        },

        /**
         * Reload debug open-view state from localStorage.
         */
        refreshDebugOpenView() {
            self.debugOpenView = exprToBoolean(
                browser.localStorage.getItem(keyDebugOpenView),
            );
        },

        /**
         * Toggle a single optional field's visibility and persist.
         *
         * @param {string} fieldName
         * @param {() => void} render
         */
        toggleOptionalField(fieldName, render) {
            const optionalActiveFields = getOptionalActiveFields();
            optionalActiveFields[fieldName] = !optionalActiveFields[fieldName];
            onSave();
            render();
        },

        /**
         * Toggle all optional fields in a property-field group and persist.
         *
         * @param {string} groupId
         * @param {() => void} render
         */
        toggleOptionalFieldGroup(groupId, render) {
            const optionalActiveFields = getOptionalActiveFields();
            const fieldNames = getAllColumns()
                .filter(
                    (col) =>
                        col.type === "field" &&
                        col.relatedPropertyField &&
                        /** @type {any} */ (col.relatedPropertyField).id === groupId,
                )
                .map((col) => col.name);
            const active = !fieldNames.every(
                (fieldName) => optionalActiveFields[fieldName],
            );
            for (const fieldName of fieldNames) {
                optionalActiveFields[fieldName] = active;
            }
            onSave();
            render();
        },

        /**
         * Toggle the debug "open form view" column and persist.
         *
         * @param {() => void} render
         */
        toggleDebugOpenView(render) {
            self.debugOpenView = !self.debugOpenView;
            browser.localStorage.setItem(
                keyDebugOpenView,
                /** @type {any} */ (self.debugOpenView),
            );
            render();
        },
    };

    return /** @type {any} */ (self);
}
