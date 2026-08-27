import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { isDarkColorPalette } from "@website/components/dialog/dark_palette_utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetOption"];
    static shared = ["getModelNameFilter"];
    modelNameFilter = "event.event";
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_dynamic_snippet_template_updated_handlers: this.onTemplateUpdated.bind(this),
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_event_upcoming_snippet")) {
            setDatasetIfUndefined(snippetEl, "numberOfRecords", 3);
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }
    // Some single-event templates use `o_cc5` for their content background.
    // The snippet dialog replaces it with `o_cc1` for dark palettes. Since the
    // generic template update still relies on the original `o_cc5` metadata,
    // normalize the actual preset after each template change.
    onTemplateUpdated({ el: snippetEl, template }) {
        if (!snippetEl.matches(".s_event_upcoming_snippet")) {
            return;
        }
        const contentEl = snippetEl.querySelector(".s_dynamic_snippet_content");
        const hasColorPreset = template.contentClasses?.split(" ").includes("o_cc5");
        if (!hasColorPreset) {
            // Avoid carrying a preset from a previously selected single layout.
            contentEl.classList.remove("o_cc1", "o_cc5");
        } else if (isDarkColorPalette(snippetEl.ownerDocument)) {
            contentEl.classList.replace("o_cc5", "o_cc1");
        } else {
            contentEl.classList.replace("o_cc1", "o_cc5");
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);
