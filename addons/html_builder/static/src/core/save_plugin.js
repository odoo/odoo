import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { groupBy } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["save", "isAlreadySaved", "saveView", "ignoreDirty"];
    static dependencies = ["history"];

    resources = {
        handleNewRecords: this.handleMutations.bind(this),
        start_edition_handlers: this.startObserving.bind(this),
        // Resource definitions:
        before_save_handlers: [
            // async () => {
            //     called at the very beginning of the save process
            // }
        ],
        clean_for_save_handlers: [
            // ({root}) => {
            //     clean DOM before save (leaving edit mode)
            //     root is the clone of a node that was o_dirty
            // }
        ],
        group_element_save_handlers: withSequence(30, this.groupElementHandler.bind(this)),
        save_element_handlers: [
            // async (el) => {
            //     called when saving an element (in parallel to saving the view)
            // }
            this.saveView.bind(this),
        ],
        save_handlers: [
            // async () => {
            //     called at the very end of the save process
            // }
        ],
        get_dirty_els: () => this.editable.querySelectorAll(".o_dirty"),
    };

    setup() {
        this.canObserve = false;
    }

    async save() {
        // TODO: implement the "group by" feature for save
        const proms = [];
        for (const fn of this.getResource("before_save_handlers")) {
            proms.push(fn());
        }
        await Promise.all(proms);
        const dirtyEls = [];
        for (const getDirtyEls of this.getResource("get_dirty_els")) {
            dirtyEls.push(...getDirtyEls());
        }
        // Group elements to save if possible
        const groupedElements = groupBy(dirtyEls, (dirtyEl) => {
            const model = dirtyEl.dataset.oeModel;
            const field = dirtyEl.dataset.oeField;

            // There are elements which have no linked model as something
            // special is to be done "to save them". In that case, do not group
            // those elements.
            if (!model) {
                return uniqueId("special-element-to-save-");
            }

            const groupElementHandler = this.getResource("group_element_save_handlers")[0];
            // If not defined, group elements which are from the same field of
            // the same record.
            return (
                groupElementHandler(model, field) || `${model}::${dirtyEl.dataset.oeId}::${field}`
            );
        });
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
            const proms = this.getResource("save_element_handlers")
                .map((saveElementHandler) => saveElementHandler(cleanedEls[0]))
                .filter(Boolean);
            if (!proms.length) {
                console.warn("no save_element_handlers for dirty element", cleanedEls[0]);
            }
            await Promise.all(proms);
        });
        // used to track dirty out of the editable scope, like header, footer or wrapwrap
        const willSaves = this.getResource("save_handlers").map((c) => c());
        await Promise.all(saveProms.concat(willSaves));
        this.lastSavedStep = this.dependencies.history.getHistorySteps().at(-1);
    }

    groupElementHandler(model, field) {
        return model === "ir.ui.view" && field === "arch" ? uniqueId("view-part-to-save-") : "";
    }

    isAlreadySaved() {
        return (
            !this.dependencies.history.getHistorySteps().length ||
            this.lastSavedStep === this.dependencies.history.getHistorySteps().at(-1)
        );
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

        // TODO: Restore the delay translation feature once it's fixed, see
        // commit msg for more info.
        const delay = delayTranslations ? { delay_translations: false } : {};
        const context = {
            website_id: this.services.website.currentWebsite.id,
            lang: this.services.website.currentWebsite.metadata.lang,
            ...delay,
        };

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
            const savableEl = targetEl.closest(".o_editable");
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
