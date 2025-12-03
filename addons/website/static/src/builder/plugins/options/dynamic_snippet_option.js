import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";
import { registry } from "@web/core/registry";

export class DynamicSnippetOption extends BaseOptionComponent {
    static id = "dynamic_snippet_option";
    static template = "website.DynamicSnippetOption";
    static dependencies = ["dynamicSnippetOption"];
    static props = {
        slots: { type: Object, optional: true },
    };
    // TODO DUAU: where the fuck is that props coming from??

    setup() {
        super.setup();
        const { getModelNameFilter } = this.dependencies.dynamicSnippetOption;
        // Specify model name in subclasses to filter the list of available
        // model record filters. Indicates that some current options are a
        // default selection.
        this.modelNameFilter = getModelNameFilter();
        this.dynamicOptionParams = useDynamicSnippetOption(this.modelNameFilter);
    }
}

registry.category("website-options").add(DynamicSnippetOption.id, DynamicSnippetOption);
