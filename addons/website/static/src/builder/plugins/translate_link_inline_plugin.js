import { LinkPlugin } from "@html_editor/main/link/link_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class TranslateLinkInlinePlugin extends Plugin {
    static id = "translateLinkInline";
    resources = {
        create_link_handlers: (linkEl) => linkEl.classList.add("o_translate_inline"),
    };
}

patch(LinkPlugin.prototype, {
    setup() {
        super.setup();
        this.ignoredClasses.add("o_translate_inline");
    },
});

registry.category("website-plugins").add(TranslateLinkInlinePlugin.id, TranslateLinkInlinePlugin);
