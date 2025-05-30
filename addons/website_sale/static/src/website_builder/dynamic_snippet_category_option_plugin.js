import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DEVICE_VISIBILITY } from "@website/builder/option_sequence";
import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { DynamicSnippetCategoryOption } from "./dynamic_snippet_category_options";


export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = "dynamicSnippetCategoryOptionPlugin";
    selector = "section.s_dynamic_category"
    resources = {
        builder_options: [
            withSequence(DEVICE_VISIBILITY, {
                OptionComponent: DynamicSnippetCategoryOption,
                selector: this.selector,
                groups: ['website.group_website_designer'],
            }),
        ],
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            for (const [optionName, value] of [
                ['columns', '2'],
                ['size', 'small'],
                ['filterId', '0'],
                ['allProducts', 'true'],
                ['button', 'Explore Now'],
                ['alignment', 'left'],
            ]) {
                setDatasetIfUndefined(snippetEl, optionName, value);
            }
        }
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryOptionPlugin.id, DynamicSnippetCategoryOptionPlugin,
);
