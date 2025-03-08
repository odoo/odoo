import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { DynamicSnippetOption } from "@html_builder/plugins/dynamic_snippet_option";

export class DynamicSnippetEventsOption extends DynamicSnippetOption {
    static template = "website_event.DynamicSnippetEventsOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        ...DynamicSnippetOption.props,
    };
    setup() {
        super.setup();
        this.modelNameFilter = "event.event";
    }
}
