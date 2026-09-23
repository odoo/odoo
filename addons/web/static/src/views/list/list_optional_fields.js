// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";
import { exprToBoolean } from "@web/core/utils/format/strings";
/**
 * @param {string} keyOptionalFields
 * @param {string} keyDebugOpenView
 * @param {Pick<
 * import("./list_renderer").ListGridContext,
 * "getAllColumns" | "getOptionalActiveFields" | "onSave"
 * >} ctx
 * @returns {{
 * debugOpenView: boolean,
 * computeOptionalActiveFields: () => Record<string, boolean>,
 * saveOptionalActiveFields: () => void,
 * toggleOptionalField: (fieldName: string) => void,
 * toggleOptionalFieldGroup: (groupId: string) => void,
 * toggleDebugOpenView: () => void,
 * }}
 */
export function useListOptionalFields(keyOptionalFields, keyDebugOpenView, ctx) {
    const { getAllColumns, getOptionalActiveFields, onSave } = ctx;
    const self = {
        debugOpenView: exprToBoolean(browser.localStorage.getItem(keyDebugOpenView)),

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

        saveOptionalActiveFields() {
            const optionalActiveFields = getOptionalActiveFields();
            const activeFieldNames = Object.keys(optionalActiveFields).filter(
                (fieldName) => optionalActiveFields[fieldName],
            );
            browser.localStorage.setItem(keyOptionalFields, activeFieldNames.join(","));
        },

        /** @param {string} fieldName */
        toggleOptionalField(fieldName) {
            const optionalActiveFields = getOptionalActiveFields();
            optionalActiveFields[fieldName] = !optionalActiveFields[fieldName];
            onSave();
        },

        /** @param {string} groupId */
        toggleOptionalFieldGroup(groupId) {
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
        },

        toggleDebugOpenView() {
            this.debugOpenView = !this.debugOpenView;
            browser.localStorage.setItem(
                keyDebugOpenView,
                /** @type {any} */ (this.debugOpenView),
            );
        },
    };

    return /** @type {any} */ (self);
}
