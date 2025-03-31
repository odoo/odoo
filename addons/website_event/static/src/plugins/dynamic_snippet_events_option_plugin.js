import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DynamicSnippetEventsOption } from "./dynamic_snippet_events_option";

class DynamicSnippetEventsOptionPlugin extends Plugin {
    static id = "dynamicSnippetEventsOption";
    static dependencies = ["dynamicSnippetOption"];
    resources = {
        builder_options: {
            OptionComponent: DynamicSnippetEventsOption,
            props: {
                ...this.dependencies.dynamicSnippetOption.getComponentProps(),
            },
            selector: ".s_event_upcoming_snippet",
        },
    };
}

registry
    .category("website-plugins")
    .add(DynamicSnippetEventsOptionPlugin.id, DynamicSnippetEventsOptionPlugin);

