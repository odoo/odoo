import { Plugin } from "@html_editor/plugin";
import { wrapInlinesInBlocks } from "@html_editor/utils/dom";
import { registry } from "@web/core/registry";

export class MassMailingIconSnippetOptionPlugin extends Plugin {
    static id = "mass_mailing.iconSnippetOption";
    static dependencies = ["media"];
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches("p:has(> .s_icon)")) {
            return;
        }
        let iconInserted = false;
        await this.dependencies.media.openMediaDialog({
            activeTab: "ICONS",
            save: async (selectedIconEl) => {
                iconInserted = true;
                snippetEl.insertAdjacentElement("afterend", selectedIconEl);
                snippetEl.remove();
                wrapInlinesInBlocks(selectedIconEl.parentElement);
            },
        });
        return !iconInserted;
    }
}

registry
    .category("mass_mailing-plugins")
    .add(MassMailingIconSnippetOptionPlugin.id, MassMailingIconSnippetOptionPlugin);
