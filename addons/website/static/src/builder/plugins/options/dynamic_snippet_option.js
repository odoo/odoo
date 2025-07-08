import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";

export class DynamicSnippetOption extends BaseOptionComponent {
    static template = "website.DynamicSnippetOption";
    static props = {
        slots: { type: Object, optional: true },
        modelNameFilter: { type: String },
    };

    setup() {
        super.setup();
        // Specify model name in subclasses to filter the list of available
        // model record filters. Indicates that some current options are a
        // default selection.
        this.dynamicOptionParams = useDynamicSnippetOption(this.props.modelNameFilter);
    }
}
