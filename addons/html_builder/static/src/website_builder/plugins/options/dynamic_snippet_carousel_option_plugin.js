import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DynamicSnippetCarouselOption } from "./dynamic_snippet_carousel_option";

class DynamicSnippetCarouselOptionPlugin extends Plugin {
    static id = "dynamicSnippetCarouselOption";
    static shared = ["getComponentProps"];
    static dependencies = ["dynamicSnippetOption"];
    resources = {
        builder_options: {
            OptionComponent: DynamicSnippetCarouselOption,
            props: this.getComponentProps(),
            selector: ".s_dynamic_snippet_carousel",
        },
    };
    getComponentProps() {
        return {
            ...this.dependencies.dynamicSnippetOption.getComponentProps(),
        };
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetCarouselOptionPlugin.id, DynamicSnippetCarouselOptionPlugin);
