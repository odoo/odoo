import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetCarouselOption", "dynamicSnippetOption"];
    static shared = ["getModelNameFilter"];
    modelNameFilter = "event.event";
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    getModelNameFilter() {
        return this.modelNameFilter;
    }
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_event_upcoming_snippet, .s_events_carousel")) {
            setDatasetIfUndefined(snippetEl, "numberOfRecords", 3);
            const optionKey = snippetEl.matches(".s_event_upcoming_snippet")
                ? "dynamicSnippetOption"
                : "dynamicSnippetCarouselOption";
            await this.dependencies[optionKey].setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);
