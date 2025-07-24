import { DYNAMIC_SNIPPET } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { setDatasetIfUndefined, setOptionsDefaultValues } from '@website/js/dynamic_snippet_utils';
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DynamicSnippetEventsOption } from "./dynamic_snippet_events_option";

class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetOption"];
    modelNameFilter = "event.event";
    selector = ".s_event_upcoming_snippet";
    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET, {
            OptionComponent: DynamicSnippetEventsOption,
            props: {
                modelNameFilter: this.modelNameFilter,
            },
            selector: this.selector,
        }),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };
    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            setDatasetIfUndefined(snippetEl, "numberOfRecords", 3);
            await setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter
            );
        }
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);
