import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class IconSnippetOptionPlugin extends Plugin {
    static id = "iconSnippetOption";
    static dependencies = ["media"];
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        so_content_addition_selector: [".s_icon"],
    };

    async onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(".s_icon")) {
            return;
        }

        let iconInserted = false;

        await this.dependencies.media.openMediaDialog({
            noIcons: false,
            noImages: true,
            noVideos: true,
            noDocuments: true,
            node: snippetEl,
            save: async (selectedIconEl) => {
                iconInserted = true;
                snippetEl.insertAdjacentElement("afterend", selectedIconEl);
                snippetEl.remove();
            },
        });

        return !iconInserted;
    }
}

registry.category("website-plugins").add(IconSnippetOptionPlugin.id, IconSnippetOptionPlugin);
