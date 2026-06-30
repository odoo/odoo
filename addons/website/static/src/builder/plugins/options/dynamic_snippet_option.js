import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";

export class DynamicSnippetOption extends BaseOptionComponent {
    static template = "website.DynamicSnippetOption";
    static dependencies = ["dynamicSnippetOption"];
    static selector = ".s_dynamic_snippet";
    static props = {
        slots: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        const { getModelNameFilter } = this.dependencies.dynamicSnippetOption;
        // Specify model name in subclasses to filter the list of available
        // model record filters. Indicates that some current options are a
        // default selection.
        this.dynamicOptionParams = useDynamicSnippetOption(getModelNameFilter());
    }
}
