import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { DynamicSnippetOption } from "./dynamic_snippet_option";

class DynamicSnippetCarouselOptionPlugin extends Plugin {
    static id = "DynamicSnippetCarouselOption";
    static dependencies = ["DynamicSnippetOption"];
    resources = {
        builder_options: {
            OptionComponent: DynamicSnippetCarouselOption,
            props: {
                ...this.dependencies.DynamicSnippetOption.getComponentProps(),
            },
            selector: ".s_dynamic_snippet_carousel",
        },
    };
}

registry
    .category("website-plugins")
    .add(DynamicSnippetCarouselOptionPlugin.id, DynamicSnippetCarouselOptionPlugin);

export class DynamicSnippetCarouselOption extends DynamicSnippetOption {
    static template = "html_builder.DynamicSnippetCarouselOption";
    static components = { ...defaultBuilderComponents };
}
