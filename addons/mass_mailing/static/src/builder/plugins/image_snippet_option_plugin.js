import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class MassMailingImageSnippetOptionPlugin extends Plugin {
    static id = "mass_mailing.imageSnippetOption";
    static dependencies = ["imageSnippetOption"];
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl, dragState }) {
        if (!snippetEl.matches("p:has(> .s_image)")) {
            return;
        }
        const imageEl = snippetEl.querySelector(".s_image");
        return this.dependencies.imageSnippetOption.onSnippetDropped({
            snippetEl: imageEl,
            dragState,
        });
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingImageSnippetOptionPlugin.id, MassMailingImageSnippetOptionPlugin);
