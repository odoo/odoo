import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["save", "isAlreadySaved"];
    static dependencies = ["history"];

    resources = {
        handleNewRecords: this.handleMutations.bind(this),
        start_edition_handlers: this.startObserving.bind(this),
        // Resource definitions:
        savable_selectors: [
            "#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]",
            "#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])",
            "#wrapwrap .s_cover[data-res-model]",
        ],
        before_save_handlers: [
            // async () => {
            //     called at the very beginning of the save process
            // }
        ],
        clean_for_save_handlers: [
            // ({root, preserveSelection = false}) => {
            //     clean DOM before save (leaving edit mode)
            //     root is the clone of a node that was o_dirty
            // }
        ],
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
        this.savableSelector = this.getResource("savable_selectors").join(", ");
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
        const saveProms = dirtyEls.map(async (dirtyEl) => {
            dirtyEl.classList.remove("o_dirty");
            const cleanedEl = dirtyEl.cloneNode(true);
            this.dispatchTo("clean_for_save_handlers", { root: cleanedEl });

            if (this.config.isTranslation) {
                await this.saveTranslationElement(cleanedEl);
            } else {
                const proms = this.getResource("save_element_handlers")
                    .map((h) => h(cleanedEl))
                    .filter(Boolean);
                if (!proms.length) {
                    console.warning("no save_element_handlers for dirty element", cleanedEl);
                }
                await Promise.all(proms);
            }
        });
        // used to track dirty out of the editable scope, like header, footer or wrapwrap
        const willSaves = this.getResource("save_handlers").map((c) => c());
        await Promise.all(saveProms.concat(willSaves));
        this.lastSavedStep = this.dependencies.history.getHistorySteps().at(-1);
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
    saveView(el) {
        const viewID = Number(el.dataset["oeId"]);
        if (!viewID) {
            return;
        }

        const context = {
            website_id: this.services.website.currentWebsite.id,
            lang: this.services.website.currentWebsite.metadata.lang,
            // TODO: Restore the delay translation feature once it's
            // fixed, see commit msg for more info.
            delay_translations: false,
        };

        return this.services.orm.call(
            "ir.ui.view",
            "save",
            [viewID, el.outerHTML, (!el.dataset["oeExpression"] && el.dataset["oeXpath"]) || null],
            { context }
        );
    }

    /**
     * If the element holds a translation, saves it. Otherwise, fallback to the
     * standard saving but with the lang kept.
     *
     * @param {HTMLElement} el - the element to save.
     */
    async saveTranslationElement(el) {
        if (el.dataset["oeTranslationSourceSha"]) {
            const translations = {};
            translations[this.services.website.currentWebsite.metadata.lang] = {
                [el.dataset["oeTranslationSourceSha"]]: this.getEscapedElement(el).innerHTML,
            };
            return rpc("/web_editor/field/translation/update", {
                model: el.dataset["oeModel"],
                record_id: [Number(el.dataset["oeId"])],
                field_name: el.dataset["oeField"],
                translations,
            });
        }
        // TODO: check what we want to modify in translate mode
        return this.saveView(el);
    }

    getEscapedElement(el) {
        const escapedEl = el.cloneNode(true);
        const allElements = [escapedEl, ...escapedEl.querySelectorAll("*")];
        const exclusion = [];
        for (const element of allElements) {
            if (
                element.matches(
                    "object,iframe,script,style,[data-oe-model]:not([data-oe-model='ir.ui.view'])"
                )
            ) {
                exclusion.push(element);
                exclusion.push(...element.querySelectorAll("*"));
            }
        }
        const exclusionSet = new Set(exclusion);
        const toEscapeEls = allElements.filter((el) => !exclusionSet.has(el));
        for (const toEscapeEl of toEscapeEls) {
            for (const child of Array.from(toEscapeEl.childNodes)) {
                if (child.nodeType === 3) {
                    const divEl = document.createElement("div");
                    divEl.textContent = child.nodeValue;
                    child.nodeValue = divEl.innerHTML;
                }
            }
        }
        return escapedEl;
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
}

registry.category("translation-plugins").add(SavePlugin.id, SavePlugin);
