import { DynamicSnippetOption } from "@html_builder/website_builder/plugins/options/dynamic_snippet_option";

export class DynamicSnippetEventsOption extends DynamicSnippetOption {
    static template = "website_event.DynamicSnippetEventsOption";
    static props = {
        ...DynamicSnippetOption.props,
    };
    setup() {
        super.setup();
        this.modelNameFilter = "event.event";
    }
}
