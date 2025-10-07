import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteSavePlugin extends Plugin {
    static id = "websiteSavePlugin";
    static shared = ["saveView"];

    resources = {
        save_element_handlers: this.saveView.bind(this),
    };

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
}

registry.category("website-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
