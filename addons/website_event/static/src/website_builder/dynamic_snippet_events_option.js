import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_hook";
import { DynamicSnippetOption } from "@website/builder/plugins/options/dynamic_snippet_option";

export class DynamicSnippetEventsOption extends BaseOptionComponent {
    static template = "website_event.DynamicSnippetEventsOption";
    static props = {
        ...DynamicSnippetOption.props,
    };
    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOption(this.props.modelNameFilter);
    }
}
