import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } WebsiteSaveShared
 * @property { WebsiteSavePlugin['saveView'] } saveView
 * @property { WebsiteSavePlugin['setViewRollback'] } setViewRollback
 */

export class WebsiteSavePlugin extends Plugin {
    static id = "websiteSavePlugin";
    static dependencies = ["discard"];
    static shared = ["saveView", "setViewRollback"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        save_element_handlers: this.saveView.bind(this),
    };

    setup() {
        this.originalEditable = this.editable.cloneNode(true);
    }

    /**
     * Saves one (dirty) element of the page.
     *
     * @param {HTMLElement} el - the element to save.
     */
    saveView(el, delayTranslations = true) {
        if (!el.dataset.oeId) {
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

        this.setViewRollback(el);

        escapeTextNodes(el);
        return this.services.orm.call("ir.ui.view", "save", this.saveArgs(el), { context });
    }

    setViewRollback(el) {
        const rollbacks = this.dependencies.discard.getRollback("views", []);
        const originalEl = this.originalEditable.querySelector(
            `[data-oe-id="${el.dataset.oeId}"][data-oe-xpath="${el.dataset.oeXpath}"]`
        );
        if (!originalEl) {
            return;
        }
        escapeTextNodes(originalEl);
        // Ensure the earliest versions are rollbacked last
        rollbacks.unshift(this.saveArgs(originalEl));
        this.dependencies.discard.setRollback("views", rollbacks);
    }

    saveArgs(el) {
        return [
            Number(el.dataset.oeId),
            el.outerHTML,
            (!el.dataset.oeExpression && el.dataset.oeXpath) || null,
        ];
    }
}

registry.category("website-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
registry.category("translation-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
