import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";
import { registry } from "@web/core/registry";

export class DynamicSnippetCarouselOption extends BaseOptionComponent {
    static id = "dynamic_snippet_carousel_option";
    static template = "website.DynamicSnippetCarouselOption";
    static dependencies = ["dynamicSnippetCarouselOption"];

    setup() {
        super.setup();
        const { getModelNameFilter } = this.dependencies.dynamicSnippetCarouselOption;
        this.modelNameFilter = getModelNameFilter();
        this.dynamicOptionParams = useDynamicSnippetOption(this.modelNameFilter);
    }
}

registry
    .category("builder-options")
    .add(DynamicSnippetCarouselOption.id, DynamicSnippetCarouselOption);
