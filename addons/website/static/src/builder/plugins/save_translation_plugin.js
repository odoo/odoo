/** @odoo-module native */
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";

const log = makeLogger("website.builder.translation.save_translation");

export class SaveTranslationPlugin extends Plugin {
    static id = "saveTranslation";
    static dependencies = ["savePlugin"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        pre_save_handlers: this.saveDelayTranslations.bind(this),
        save_elements_overrides: withSequence(
            20,
            this.saveTranslationElements.bind(this),
        ),
    };

    async saveDelayTranslations(groupedDirtyElements) {
        const cleanDelayTranslationEls = [
            ...this.editable.querySelectorAll(".o_delay_translation:not(.o_dirty)"),
        ];
        const groupedDelayTranslationElements =
            this.dependencies.savePlugin.groupElements(cleanDelayTranslationEls);
        const updateTranslationProms = [];
        const currentWebsiteLang = this.services.website.currentWebsite.metadata.lang;
        const translations = {};
        translations[currentWebsiteLang] = {};
        for (const [key, els] of Object.entries(groupedDelayTranslationElements)) {
            if (groupedDirtyElements[key]) {
                log.logic("saveDelayTranslations: skip dirty group", { key });
                continue;
            }
            for (const el of els) {
                const sha = el.dataset["oeTranslationSourceSha"];
                if (sha) {
                    translations[currentWebsiteLang][sha] =
                        this.getEscapedElement(el).innerHTML;
                }
            }
            updateTranslationProms.push(
                rpc("/website/field/translation/update", {
                    model: els[0].dataset["oeModel"],
                    record_id: [Number(els[0].dataset["oeId"])],
                    field_name: els[0].dataset["oeField"],
                    translations,
                }),
            );
        }
        log.pipeline("saveDelayTranslations: posting delayed translations", () => ({
            cleanDelayed: cleanDelayTranslationEls.length,
            groups: Object.keys(groupedDelayTranslationElements).length,
            rpcs: updateTranslationProms.length,
            lang: currentWebsiteLang,
        }));
        return Promise.all(updateTranslationProms);
    }
    /**
     * @param {Array<HTMLElement>} els
     */
    async saveTranslationElements(els) {
        if (els[0].dataset["oeTranslationSourceSha"]) {
            const translations = {};
            translations[this.services.website.currentWebsite.metadata.lang] =
                Object.assign(
                    {},
                    ...els.map((el) => ({
                        [el.dataset["oeTranslationSourceSha"]]:
                            this.getEscapedElement(el).innerHTML,
                    })),
                );
            log.pipeline("saveTranslationElements: posting translations", () => ({
                count: els.length,
                model: els[0].dataset["oeModel"],
                field: els[0].dataset["oeField"],
            }));
            return rpc("/website/field/translation/update", {
                model: els[0].dataset["oeModel"],
                record_id: [Number(els[0].dataset["oeId"])],
                field_name: els[0].dataset["oeField"],
                translations,
            });
        }
        log.logic("saveTranslationElements: no source sha, save view", () => ({
            count: els.length,
        }));
        const endSaveView = log.perf("saveTranslationElements saveView");
        await this.dependencies.savePlugin.saveView(els[0], false);
        endSaveView();
        return true;
    }

    getEscapedElement(el) {
        const escapedEl = el.cloneNode(true);
        const allElements = [escapedEl, ...escapedEl.querySelectorAll("*")];
        const exclusion = [];
        for (const element of allElements) {
            if (
                element.matches(
                    "object,iframe,script,style,[data-oe-model]:not([data-oe-model='ir.ui.view'])",
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
        log.pipeline("getEscapedElement", () => ({
            elements: allElements.length,
            excluded: exclusionSet.size,
        }));
        return escapedEl;
    }
}
