import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";

export class SaveTranslationPlugin extends Plugin {
    static id = "saveTranslation";
    static dependencies = ["savePlugin"];

    resources = {
        save_elements_overrides: withSequence(20, this.saveTranslationElements.bind(this)),
    };

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
                ...els.map((el) => ({
                    [el.dataset["oeTranslationSourceSha"]]: this.getEscapedElement(el).innerHTML,
                }))
            );
            return rpc("/website/field/translation/update", {
                model: els[0].dataset["oeModel"],
                record_id: [Number(els[0].dataset["oeId"])],
                field_name: els[0].dataset["oeField"],
                translations,
            });
        }
        await this.dependencies.savePlugin.saveView(els[0], false);
        return true;
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
}
