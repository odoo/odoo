import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class SaveTranslationPlugin extends Plugin {
    static id = "saveTranslation";
    static dependencies = ["savePlugin", "websiteSavePlugin"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_will_save_handlers: this.saveDelayTranslations.bind(this),
        save_elements_overrides: withSequence(20, this.saveTranslationElements.bind(this)),
    };

    async saveDelayTranslations(root = this.editable, groupedDirtyElements) {
        // Don't take dirty elements as they will be saved
        const cleanDelayTranslationEls = [
            ...root.querySelectorAll(".o_delay_translation:not(.o_dirty)"),
        ];
        const groupedDelayTranslationElements =
            this.dependencies.savePlugin.groupElements(cleanDelayTranslationEls);
        const updateTranslationProms = [];
        const currentWebsiteLang = this.services.website.currentWebsite.metadata.lang;
        const translations = {};
        translations[currentWebsiteLang] = {};
        for (const [key, els] of Object.entries(groupedDelayTranslationElements)) {
            // Keep only delay translation related to particular field that will
            // not be updated by a modified (dirty) element
            if (groupedDirtyElements[key]) {
                continue;
            }
            updateTranslationProms.push(
                rpc("/website/field/translation/update", {
                    model: els[0].dataset["oeModel"],
                    record_id: [Number(els[0].dataset["oeId"])],
                    field_name: els[0].dataset["oeField"],
                    translations,
                })
            );
        }
        return Promise.all(updateTranslationProms);
    }
    /**
     * If the elements hold a translation, saves it. Otherwise, fallback to the
     * standard saving with the lang kept.
     *
     * @param {Array<HTMLElement>} els - the elements to save.
     */
    async saveTranslationElements(els) {
        if (els[0].dataset["oeTranslationSourceSha"]) {
            const translations = {};
            translations[this.services.website.currentWebsite.metadata.lang] = Object.assign(
                {},
                ...els.map((el) => {
                    escapeTextNodes(el);
                    return { [el.dataset["oeTranslationSourceSha"]]: el.innerHTML };
                })
            );
            return rpc("/website/field/translation/update", {
                model: els[0].dataset["oeModel"],
                record_id: [Number(els[0].dataset["oeId"])],
                field_name: els[0].dataset["oeField"],
                translations,
            });
        }
        await this.dependencies.websiteSavePlugin.saveView(els[0], false);
        return true;
    }
}

registry.category("translation-plugins").add(SaveTranslationPlugin.id, SaveTranslationPlugin);
