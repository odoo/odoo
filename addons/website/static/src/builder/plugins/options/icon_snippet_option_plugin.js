import { Plugin } from "@html_editor/plugin";
import { allowsParagraphRelatedElements } from "@html_editor/utils/dom_info";
import { registry } from "@web/core/registry";

export class IconSnippetOptionPlugin extends Plugin {
    static id = "iconSnippetOption";
    static dependencies = ["media"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        so_content_addition_selector: [".s_icon"],
    };

    async onSnippetDropped({ snippetEl, dragState }) {
        if (!snippetEl.matches(".s_icon")) {
            return;
        }
        let iconInserted = false;
        await this.dependencies.media.openMediaDialog({
            activeTab: "ICONS",
            save: async (selectedIconEl) => {
                iconInserted = true;
                snippetEl.insertAdjacentElement("afterend", selectedIconEl);
                snippetEl.remove();
                dragState.replacedSnippetEl = selectedIconEl;
                // ensure the icon is wrapped in a block("P") element to allow
                // line breaks
                if (allowsParagraphRelatedElements(selectedIconEl.parentElement)) {
                    const blockEl = this.document.createElement("p");
                    selectedIconEl.before(blockEl);
                    blockEl.append(selectedIconEl);
                }
            },
        });
        return !iconInserted;
    }
}

registry.category("website-plugins").add(IconSnippetOptionPlugin.id, IconSnippetOptionPlugin);
