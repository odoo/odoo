import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";

export class DynamicSnippetCarouselOption extends BaseOptionComponent {
    static template = "website.DynamicSnippetCarouselOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    static selector = ".s_dynamic_snippet_carousel";

    setup() {
        super.setup();
        const { getModelNameFilter } = this.dependencies.dynamicSnippetCarouselOption;
        this.dynamicOptionParams = useDynamicSnippetOption(getModelNameFilter());
    }
}
