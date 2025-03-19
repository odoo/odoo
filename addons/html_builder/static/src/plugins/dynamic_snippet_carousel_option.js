import { DynamicSnippetOption } from "./dynamic_snippet_option";
import { useBuilderComponents } from "@html_builder/core/utils";

export class DynamicSnippetCarouselOption extends DynamicSnippetOption {
    static template = "html_builder.DynamicSnippetCarouselOption";
    setup() {
        useBuilderComponents();
    }
}
