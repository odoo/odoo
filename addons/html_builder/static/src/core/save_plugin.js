import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { groupBy } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef { Object } SaveShared
 * @property { SavePlugin['save'] } save
 * @property { SavePlugin['saveView'] } saveView
 * @property { SavePlugin['ignoreDirty'] } ignoreDirty
 * @property { SavePlugin['groupElements'] } groupElements
 */

/**
 * @typedef {(() => void)[]} after_save_handlers
 * @typedef {((el?: HTMLElement) => Promise<void>)[]} before_save_handlers
 * Called at the very beginning of the save process.
 *
 * @typedef {((groupedEls: Object.<string, HTMLElement[]>) => Promise<void>)[]} pre_save_handlers
 * Called before the save process with the grouped dirty elements.
 *
 * @typedef {((el: HTMLElement) => Promise<void>)[]} save_element_handlers
 * Called when saving an element (in parallel to saving the view).
 *
 * @typedef {(() => Promise<boolean>)[]} save_handlers
 * Called at the very end of the save process.
 *
 * @typedef {((cleanedEls: HTMLElement[]) => Promise<boolean>)[]} save_elements_overrides
 *
 * @typedef {(() => HTMLElement[] | NodeList)[]} get_dirty_els
 *
 * @typedef {CSSSelector[]} savable_selectors
 */

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["save", "saveView", "ignoreDirty", "groupElements"];
    static dependencies = ["history"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        handleNewRecords: this.handleMutations.bind(this),
        start_edition_handlers: this.startObserving.bind(this),
        // Resource definitions:
        savable_selectors: [
            "#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]",
            "#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])",
            "#wrapwrap .s_cover[data-res-model]",
        ],
        clean_for_save_handlers: [
            // ({root}) => {
            //     clean DOM before save (leaving edit mode)
            //     root is the clone of a node that was o_dirty
            // }
        ],
        save_element_handlers: [this.saveView.bind(this)],
        get_dirty_els: () => this.editable.querySelectorAll(".o_dirty"),
        // Do not change the sequence of this resource, it must stay the first
        // one to avoid marking dirty when not needed during the drag and drop.
        on_prepare_drag_handlers: withSequence(0, this.ignoreDirty.bind(this)),
    };

    setup() {
        this.canObserve = false;
        this.savableSelector = this.getResource("savable_selectors").join(", ");
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
            await Promise.all(this.getResource("before_save_handlers").map((handler) => handler()));
            await this._save();
            skipAfterSaveHandlers = await shouldSkipAfterSaveHandlers();
        } finally {
            if (!skipAfterSaveHandlers) {
                this.getResource("after_save_handlers").forEach((handler) => handler());
            }
        }
    }
    async _save() {
        const dirtyEls = [];
        for (const getDirtyEls of this.getResource("get_dirty_els")) {
            dirtyEls.push(...getDirtyEls());
        }
        // Group elements to save if possible
        const groupedElements = this.groupElements(dirtyEls);
        const preSaveHandlers = [];
        for (const preSaveHandler of this.getResource("pre_save_handlers")) {
            preSaveHandlers.push(preSaveHandler(groupedElements));
        }
        await Promise.all(preSaveHandlers);
        const saveProms = Object.values(groupedElements).map(async (dirtyEls) => {
            const cleanedEls = dirtyEls.map((dirtyEl) => {
                dirtyEl.classList.remove("o_dirty");
                const cleanedEl = dirtyEl.cloneNode(true);
                this.dispatchTo("clean_for_save_handlers", { root: cleanedEl });
                return cleanedEl;
            });
            for (const saveElementsOverride of this.getResource("save_elements_overrides")) {
                if (await saveElementsOverride(cleanedEls)) {
                    return;
                }
            }
            for (const cleanedEl of cleanedEls) {
                for (const saveElementHandler of this.getResource("save_element_handlers")) {
                    await saveElementHandler(cleanedEl);
                }
            }
        });
        // used to track dirty out of the editable scope, like header, footer or wrapwrap
        const willSaves = this.getResource("save_handlers").map((c) => c());
        await Promise.all(saveProms.concat(willSaves));
        this.dependencies.history.reset();
    }

    /**
     * Saves one (dirty) element of the page.
     *
     * @param {HTMLElement} el - the element to save.
     */
    saveView(el, delayTranslations = true) {
        const viewID = Number(el.dataset["oeId"]);
        if (!viewID) {
            return;
        }

        let context = {};
        if (this.services.website) {
            const delay = delayTranslations ? { delay_translations: true } : {};
            context = {
                website_id: this.services.website.currentWebsite.id,
                lang: this.services.website.currentWebsite.metadata.lang,
                ...delay,
            };
        }

        escapeTextNodes(el);
        return this.services.orm.call(
            "ir.ui.view",
            "save",
            [viewID, el.outerHTML, (!el.dataset["oeExpression"] && el.dataset["oeXpath"]) || null],
            { context }
        );
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
            const savableEl = targetEl.closest(this.savableSelector);
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
