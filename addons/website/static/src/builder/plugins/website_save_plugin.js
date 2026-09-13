import { prepareElementForSave } from "@html_builder/core/save_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const ATTRS_TO_TRANSLATE = {
    img: ["src", "srcset"],
};

/**
 * @typedef {((context: Object) => context)[]} save_element_context_processors
 */

export class WebsiteSavePlugin extends Plugin {
    static id = "websiteSavePlugin";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_ready_to_save_document_handlers: this.saveElements.bind(this),
        clean_for_save_processors: (rootEl) => {
            if (
                (rootEl.dataset.oeModel === "ir.ui.view" && rootEl.dataset.oeField === "arch") ||
                rootEl.dataset.oeType === "html"
            ) {
                this.setTranslateAttributes(rootEl);
            }
            return rootEl;
        },
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

    async saveElements() {
        let context = {};
        if (this.services.website) {
            context = this.processThrough("save_element_context_processors", {
                website_id: this.services.website.currentWebsite.id,
                lang: this.services.website.currentWebsite.metadata.lang,
                delay_translations: true,
            });
        }
        const dirtys = this.editable.querySelectorAll(
            "[data-oe-model].o_dirty:not([data-oe-translation-source-sha])"
        );
        const getGroupKey = (el) =>
            `${el.dataset.oeModel}::${el.dataset.oeId}::${el.dataset.oeField}`;
        await Promise.all(
            Object.values(Object.groupBy(dirtys, getGroupKey)).map(async (els) => {
                // parts of the same group are uploaded sequentially to avoid
                // dataraces on backend that could lead to duplication or loss
                for (const el of els) {
                    await this.services.orm.call(
                        "ir.ui.view",
                        "save",
                        [
                            Number(el.dataset.oeId),
                            prepareElementForSave(this, el).outerHTML,
                            (!el.dataset.oeExpression && el.dataset.oeXpath) || null,
                        ],
                        { context }
                    );
                }
            })
        );
    }
}

registry.category("website-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
registry.category("translation-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
