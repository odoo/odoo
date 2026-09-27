import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } WebsiteSaveShared
 * @property { WebsiteSavePlugin['saveView'] } saveView
 */

const ATTRS_TO_TRANSLATE = {
    img: ["src", "srcset"],
};

export class WebsiteSavePlugin extends Plugin {
    static id = "websiteSavePlugin";
    static shared = ["saveView"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_will_save_element_handlers: this.saveView.bind(this),
    };

    setTranslateAttributes(rootEl) {
        for (const [elType, attrs] of Object.entries(ATTRS_TO_TRANSLATE)) {
            const translateSelector = attrs.map((attr) => `${elType}[${attr}]`).join(", ");
            for (const el of rootEl.querySelectorAll(translateSelector)) {
                for (const attr of attrs) {
                    if (el.getAttribute(attr)) {
                        el.setAttribute(`${attr}.translate`, el.getAttribute(attr));
                    }
                }
            }
        }
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

        // Only translate attributes within arch views (website pages) or html
        // fields. Any other type should not be translated.
        if (
            (el.dataset.oeModel === "ir.ui.view" && el.dataset.oeField === "arch") ||
            el.dataset.oeType === "html"
        ) {
            this.setTranslateAttributes(el);
        }
        escapeTextNodes(el);
        return this.services.orm.call(
            "ir.ui.view",
            "save",
            [viewID, el.outerHTML, (!el.dataset["oeExpression"] && el.dataset["oeXpath"]) || null],
            { context }
        );
    }
}

registry.category("website-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
registry.category("translation-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
