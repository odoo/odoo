import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";
import { registry } from "@web/core/registry";

export class DynamicSnippetOption extends BaseOptionComponent {
    static id = "dynamic_snippet_option";
    static template = "website.DynamicSnippetOption";
    static props = {
        slots: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOption();
    }
}

registry.category("website-options").add(DynamicSnippetOption.id, DynamicSnippetOption);
