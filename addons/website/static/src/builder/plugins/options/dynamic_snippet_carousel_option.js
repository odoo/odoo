import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";
import { registry } from "@web/core/registry";

export class DynamicSnippetCarouselOption extends BaseOptionComponent {
    static id = "dynamic_snippet_carousel_option";
    static template = "website.DynamicSnippetCarouselOption";

    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOption();
    }
}

registry
    .category("website-options")
    .add(DynamicSnippetCarouselOption.id, DynamicSnippetCarouselOption);
