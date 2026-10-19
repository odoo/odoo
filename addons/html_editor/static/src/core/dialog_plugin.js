import { Plugin } from "../plugin";

/**
 * @typedef {typeof import("@odoo/owl").Component} Component
 * @typedef {import("@web/core/dialog/dialog_plugin").DialogOptionSchema} DialogOptionSchema
 */

/**
 * @typedef {Object} DialogShared
 * @property {DialogPlugin['addDialog']} addDialog
 */

export class DialogPlugin extends Plugin {
    static id = "dialog";
    static dependencies = ["selection"];
    static shared = ["addDialog"];

    /**
     * @param {Component} DialogClass
     * @param {Object} props
     * @param {DialogOptionSchema} options
     * @returns {Promise<void>}
     */
    addDialog(DialogClass, props, options = {}) {
        return new Promise((resolve) => {
            this.services.dialog.add(DialogClass, props, {
                onClose: () => {
                    this.dependencies.selection.focusEditable();
                    resolve();
                },
                ...options,
            });
        });
    }
}
