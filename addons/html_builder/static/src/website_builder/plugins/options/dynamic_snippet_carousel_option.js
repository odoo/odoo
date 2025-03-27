import { BaseOptionComponent } from "@html_builder/core/utils";
import { useDynamicSnippetOption } from "./dynamic_snippet_hook";
import { DynamicSnippetOption } from "./dynamic_snippet_option";

export class DynamicSnippetCarouselOption extends BaseOptionComponent {
    static template = "html_builder.DynamicSnippetCarouselOption";
    static props = { ...DynamicSnippetOption.props };
    setup() {
        super.setup();
        this.dynamicOptionParams = useDynamicSnippetOption(this.props.modelNameFilter);
    }
}
