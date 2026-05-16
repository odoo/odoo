import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { selectElements } from "@html_editor/utils/dom_traversal";

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
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            for (const linkEl of selectElements(snippetEl, "a")) {
                // Links inside `.o_not_editable` are not editable in
                // translation mode, so they should not be marked as inline
                // translatable.
                // This notably avoids issues with `s_table_of_content`,
                // whose navbar links are inside `.o_not_editable`.
                const closestNotEditableEl = linkEl.closest(".o_not_editable");
                if (!closestNotEditableEl) {
                    linkEl.classList.add("o_translate_inline");
                }
            }
        },
    };

    markTranslateInline(containerEl) {
        for (const linkEl of containerEl.querySelectorAll("a")) {
            linkEl.classList.add("o_translate_inline");
        }
    }
}

registry.category("website-plugins").add(TranslateLinkInlinePlugin.id, TranslateLinkInlinePlugin);
