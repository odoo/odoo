import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { registry } from "@web/core/registry";
import { groupBy } from "@web/core/utils/arrays";

/** @typedef {import("plugins").CSSSelector} CSSSelector */
/**
 * @typedef {((context: Object) => void)[]} save_view_context_processors
 */

export class WebsiteSavePlugin extends Plugin {
    static id = "websiteSavePlugin";
    static dependencies = ["savePlugin"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dirt_marks: {
            id: "element",
            setDirtyOnMutation: (record) => closestElement(record.target, ".o_savable:not([data-oe-translation-source-sha])"),
            saveAll: this.saveElements.bind(this),
        },
    };

    /**
     * Saves all dirty elements to "ir.ui.view"
     */
    async saveElements(dirtys) {
        let context = {};
        if (this.services.website) {
            context = {
                website_id: this.services.website.currentWebsite.id,
                lang: this.services.website.currentWebsite.metadata.lang,
                delay_translations: true,
            };
            this.dispatchTo("save_view_context_processors", context);
        }

        await Promise.all(
            Object.values(
                groupBy(
                    dirtys,
                    ({ el }) => `${el.dataset.oeModel}::${el.dataset.oeId}::${el.dataset.oeField}`
                )
            ).map(async (els) => {
                // parts of the same group are uploaded sequentially to avoid
                // dataraces on backend that could lead to duplication or loss
                for (const { el, setClean } of els) {
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
