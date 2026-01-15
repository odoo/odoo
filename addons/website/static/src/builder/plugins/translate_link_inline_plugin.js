import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class TranslateLinkInlinePlugin extends Plugin {
    static id = "translateLinkInline";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        create_link_handlers: (linkEl) => linkEl.classList.add("o_translate_inline"),
        before_insert_processors: (container) => {
            for (const linkEl of container.querySelectorAll("a")) {
                linkEl.classList.add("o_translate_inline");
            }
            return container;
        },
    };
}

registry.category("website-plugins").add(TranslateLinkInlinePlugin.id, TranslateLinkInlinePlugin);
