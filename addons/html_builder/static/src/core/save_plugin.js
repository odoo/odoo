import { Plugin } from "@html_editor/plugin";

const oeStructureSelector = "#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]";
const oeFieldSelector = "#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])";
const OE_RECORD_COVER_SELECTOR = "#wrapwrap .o_record_cover_container[data-res-model]";
const oeCoverSelector = `#wrapwrap .s_cover[data-res-model], ${OE_RECORD_COVER_SELECTOR}`;
const SAVABLE_SELECTOR = `${oeStructureSelector}, ${oeFieldSelector}, ${oeCoverSelector}`;

export class SavePlugin extends Plugin {
    static id = "savePlugin";
    static shared = ["save"];

    resources = {
        handleNewRecords: this.handleMutations,
        // Resource definitions:
        before_save_handlers: [
            // () => {
            //     called at the very beginning of the save process
            // }
        ],
        clean_for_save_handlers: [
            // ({root, preserveSelection = false}) => {
            //     clean DOM before save (leaving edit mode)
            //     root is the clone of a node that was o_dirty
            // }
        ],
        save_handlers: [
            // () => {
            //     called at the very end of the save process
            // }
        ],
    };

    async save() {
        const proms = [];
        for (const fn of this.getResource("before_save_handlers")) {
            proms.push(fn());
        }
        await Promise.all(proms);
        const saveProms = [...this.editable.querySelectorAll(".o_dirty")].map(async (dirtyEl) => {
            dirtyEl.classList.remove("o_dirty");
            const cleanedEl = dirtyEl.cloneNode(true);
            this.dispatchTo("clean_for_save_handlers", { root: cleanedEl });

            if (this.config.isTranslation) {
                await this.saveTranslationElement(cleanedEl);
            } else {
                await this.saveView(cleanedEl);
            }
        });
        // used to track dirty out of the editable scope, like header, footer or wrapwrap
        const willSaves = this.getResource("save_handlers").map((c) => c());
        await Promise.all(saveProms.concat(willSaves));
    }

    /**
     * Saves one (dirty) element of the page.
     *
     * @param {HTMLElement} el - the element to save.
     */
    async saveView(el) {
        const viewID = Number(el.dataset["oeId"]);
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
                [el.dataset["oeTranslationSourceSha"]]: el.innerHTML,
            };
            return this.services.orm.call(el.dataset["oeModel"], "web_update_field_translations", [
                [Number(el.dataset["oeId"])],
                el.dataset["oeField"],
                translations,
            ]);
        }
        // TODO: check what we want to modify in translate mode
        return this.saveView(el);
    }

    /**
     * Handles the flag of the closest savable element to the mutation as dirty
     *
     * @param {Object} records - The observed mutations
     * @param {String} currentOperation - The name of the current operation
     */
    handleMutations(records, currentOperation) {
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
            const savableEl = targetEl.closest(SAVABLE_SELECTOR);
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
