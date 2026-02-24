import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { groupBy } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef { Object } SaveShared
 * @property { SavePlugin['save'] } save
 * @property { SavePlugin['ignoreDirty'] } ignoreDirty
 * @property { SavePlugin['groupElements'] } groupElements
 */

/**
 * @typedef {((el?: HTMLElement) => void)[]} on_saved_handlers
 * @typedef {((el?: HTMLElement, groupedEls?: Object.<string, HTMLElement[]>) => Promise<void>)[]} on_will_save_handlers
 * Called before the save process.
 *
 * @typedef {((el: HTMLElement) => Promise<void>)[]} on_will_save_element_handlers
 * Called when saving an element (in parallel to saving the view).
 *
 * @typedef {(() => Promise<boolean>)[]} on_will_reset_history_after_saving_handlers
 * Called at the very end of the save process.
 *
 * @typedef {((cleanedEls: HTMLElement[]) => Promise<boolean>)[]} save_elements_overrides
 *
 * @typedef {(() => HTMLElement[] | NodeList)[]} dirty_els_providers
 */

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["save", "ignoreDirty", "groupElements"];
    static dependencies = ["history"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        on_new_records_handled_handlers: this.handleMutations.bind(this),
        on_editor_started_handlers: this.startObserving.bind(this),
        // Resource definitions:
        clean_for_save_processors: [
            // (root) => {
            //     clean DOM before save (leaving edit mode)
            //     root is the clone of a node that was o_dirty
            // }
        ],
        dirty_els_providers: () => this.editable.querySelectorAll(".o_dirty"),
        // Do not change the sequence of this resource, it must stay the first
        // one to avoid marking dirty when not needed during the drag and drop.
        on_prepare_drag_handlers: withSequence(0, this.ignoreDirty.bind(this)),
    };

    setup() {
        this.canObserve = false;
    }

    groupElements(toGroupEls) {
        return groupBy(toGroupEls, (toGroupEl) => {
            const model = toGroupEl.dataset.oeModel;
            const recordId = toGroupEl.dataset.oeId;
            const field = toGroupEl.dataset.oeField;

            // There are elements which have no linked model as something
            // special is to be done "to save them". In that case, do not group
            // those elements.
            if (!model) {
                return uniqueId("special-element-to-save-");
            }

            // Group elements which are from the same field of the same record.
            return `${model}::${recordId}::${field}`;
        });
    }

    async save({ shouldSkipAfterSaveHandlers = async () => true } = {}) {
        let skipAfterSaveHandlers;
        try {
            // Get elements to save, then group them if possible.
            const dirtyEls = this.getResource("dirty_els_providers").flatMap((p) => [...p()]);
            const groupedElements = this.groupElements(dirtyEls);
            await Promise.all(
                this.trigger("on_will_save_handlers", this.editable, groupedElements)
            );
            await this._save(groupedElements);
            skipAfterSaveHandlers = await shouldSkipAfterSaveHandlers();
        } finally {
            if (!skipAfterSaveHandlers) {
                this.trigger("on_saved_handlers");
            }
        }
    }
    async _save(groupedElements) {
        const saveProms = Object.values(groupedElements).map(async (dirtyEls) => {
            const cleanedEls = dirtyEls.map((dirtyEl) => {
                dirtyEl.classList.remove("o_dirty");
                return this.processThrough("clean_for_save_processors", dirtyEl.cloneNode(true));
            });
            for (const saveElementsOverride of this.getResource("save_elements_overrides")) {
                if (await saveElementsOverride(cleanedEls)) {
                    return;
                }
            }
            for (const cleanedEl of cleanedEls) {
                await Promise.all(this.trigger("on_will_save_element_handlers", cleanedEl));
            }
        });
        // used to track dirty out of the editable scope, like header, footer or wrapwrap
        const willSaves = this.trigger("on_will_reset_history_after_saving_handlers");
        await Promise.all(saveProms.concat(willSaves));
        this.dependencies.history.reset();
    }

    startObserving() {
        this.canObserve = true;
    }
    /**
     * Handles the flag of the closest savable element to the mutation as dirty
     *
     * @param {Object} records - The observed mutations
     * @param {String} currentOperation - The name of the current operation
     */
    handleMutations(records, currentOperation) {
        if (!this.canObserve) {
            return;
        }
        if (currentOperation === "undo" || currentOperation === "redo") {
            // Do nothing as `o_dirty` has already been handled by the history
            // plugin.
            return;
        }
        for (const record of records) {
            if (record.attributeName === "contenteditable") {
                continue;
            }
            let targetEl = record.target;
            if (!targetEl.isConnected) {
                continue;
            }
            if (targetEl.nodeType !== Node.ELEMENT_NODE) {
                targetEl = targetEl.parentElement;
            }
            if (!targetEl) {
                continue;
            }
            const savableEl = targetEl.closest(".o_savable");
            if (
                !savableEl ||
                savableEl.classList.contains("o_dirty") ||
                savableEl.hasAttribute("data-oe-readonly")
            ) {
                continue;
            }
            savableEl.classList.add("o_dirty");
        }
    }

    /**
     * Prevents elements to be marked as dirty until it is reactivated with the
     * returned callback.
     *
     * @returns {Function}
     */
    ignoreDirty() {
        this.canObserve = false;
        return () => {
            this.canObserve = true;
        };
    }
}
