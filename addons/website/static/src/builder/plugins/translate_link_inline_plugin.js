import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class TranslateLinkInlinePlugin extends Plugin {
    static id = "translateLinkInline";
    resources = {
        create_link_handlers: (linkEl) => linkEl.classList.add("o_translate_inline"),
    };
}

registry.category("website-plugins").add(TranslateLinkInlinePlugin.id, TranslateLinkInlinePlugin);
