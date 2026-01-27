import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class TranslateLinkInlinePlugin extends Plugin {
    static id = "translateLinkInline";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        create_link_handlers: (linkEl) => linkEl.classList.add("o_translate_inline"),
        before_insert_processors: (container) => {
            this.markTranslateInline(container);
            return container;
        },
        on_replaced_media_handlers: ({ newMediaEl }) => {
            this.markTranslateInline(newMediaEl);
        },
    };

    markTranslateInline(containerEl) {
        for (const linkEl of containerEl.querySelectorAll("a")) {
            linkEl.classList.add("o_translate_inline");
        }
    }
}

registry.category("website-plugins").add(TranslateLinkInlinePlugin.id, TranslateLinkInlinePlugin);
