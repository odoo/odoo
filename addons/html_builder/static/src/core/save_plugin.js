import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";

/**
 * @typedef { Object } SaveShared
 * @property { SavePlugin['save'] } save
 * @property { SavePlugin['hasUnsaveData'] } hasUnsaveData
 * @property { SavePlugin['prepareElementForSave'] } prepareElementForSave
 */

/**
 * @typedef {(() => void)[]} after_save_handlers
 * @typedef {((el?: HTMLElement) => Promise<void>)[]} before_save_handlers
 * Called at the very beginning of the save process.
 * @typedef {((arg: { root: HTMLElement }) => void)[]} clean_for_save_handlers
 * Clean DOM node before save, root is the clone of a dirty node
 * @typedef {(() => Promise<void>)[]} save_handlers
 *
 * @typedef {(() => boolean)[]} has_unsaved_data_predicates
 */

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["hasUnsaveData", "save", "prepareElementForSave"];

    async save({ shouldSkipAfterSaveHandlers = async () => true } = {}) {
        let skipAfterSaveHandlers;
        try {
            await Promise.all(this.getResource("before_save_handlers").map((handler) => handler()));
            await Promise.all(this.getResource("save_handlers").map((c) => c()));
            skipAfterSaveHandlers = await shouldSkipAfterSaveHandlers();
        } finally {
            if (!skipAfterSaveHandlers) {
                this.getResource("after_save_handlers").forEach((handler) => handler());
            }
        }
    }

    hasUnsaveData() {
        return this.getResource("has_unsaved_data_predicates").some((p) => p());
    }

    /**
     * Clone `el` and run the handlers needed to get it ready for save
     * @param {HTMLElement} el
     * @returns {HTMLElement}
     */
    prepareElementForSave(el) {
        const cleanedEl = el.cloneNode(true);
        this.dispatchTo("clean_for_save_handlers", { root: cleanedEl });
        escapeTextNodes(cleanedEl);
        return cleanedEl;
    }
}
