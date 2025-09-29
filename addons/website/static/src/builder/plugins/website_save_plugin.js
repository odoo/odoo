import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {((context: Object) => void)[]} save_view_context_processors
 */

const ATTRS_TO_TRANSLATE = {
    img: ["src", "srcset"],
};

export class WebsiteSavePlugin extends Plugin {
    static id = "websiteSavePlugin";
    static dependencies = ["savePlugin"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dirt_marks: {
            id: "element",
            setDirtyOnMutation: (mutation, targetNode) =>
                closestElement(targetNode, ".o_savable:not([data-oe-translation-source-sha])"),
            saveAll: this.saveElements.bind(this),
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

    /**
     * Saves all dirty elements to "ir.ui.view"
     */
    async saveElements(dirtys) {
        let context = {};
        if (this.services.website) {
            context = this.processThrough("save_view_context_processors", {
                website_id: this.services.website.currentWebsite.id,
                lang: this.services.website.currentWebsite.metadata.lang,
                delay_translations: true,
            });
        }

        await Promise.all(
            Object.values(
                Object.groupBy(
                    dirtys,
                    ({ el }) => `${el.dataset.oeModel}::${el.dataset.oeId}::${el.dataset.oeField}`
                )
            ).map(async (els) => {
                // parts of the same group are uploaded sequentially to avoid
                // dataraces on backend that could lead to duplication or loss
                for (const { el, setClean } of els) {
                    // Only translate attributes within arch views (website pages) or html
                    // fields. Any other type should not be translated.
                    if (
                        (el.dataset.oeModel === "ir.ui.view" && el.dataset.oeField === "arch") ||
                        el.dataset.oeType === "html"
                    ) {
                        this.setTranslateAttributes(el);
                    }
                    await this.services.orm.call(
                        "ir.ui.view",
                        "save",
                        [
                            Number(el.dataset.oeId),
                            this.dependencies.savePlugin.prepareElementForSave(el).outerHTML,
                            (!el.dataset["oeExpression"] && el.dataset["oeXpath"]) || null,
                        ],
                        { context }
                    );
                    setClean();
                }
            })
        );
    }
}

registry.category("website-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
registry.category("translation-plugins").add(WebsiteSavePlugin.id, WebsiteSavePlugin);
