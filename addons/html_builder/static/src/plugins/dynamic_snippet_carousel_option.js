import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { DynamicSnippetOption } from "./dynamic_snippet_option";

export class DynamicSnippetCarouselOption extends DynamicSnippetOption {
    static template = "html_builder.DynamicSnippetCarouselOption";
    static components = { ...defaultBuilderComponents };
}
