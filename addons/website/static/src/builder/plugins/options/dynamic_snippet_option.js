import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";
import { useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class DynamicSnippetOption extends BaseOptionComponent {
    static id = "dynamic_snippet_option";
    static template = "website.DynamicSnippetOption";
    static dependencies = ["dynamicSnippetOption"];
    props = useProps({
        slots: t.object().optional(),
    });

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
