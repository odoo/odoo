import { Plugin } from '@html_editor/plugin';
import { withSequence } from '@html_editor/utils/resource';
import { registry } from '@web/core/registry';
import { DEVICE_VISIBILITY } from '@website/builder/option_sequence';
import { DynamicSnippetCategoryOption } from './dynamic_snippet_category_options';


export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryOptionPlugin';
    selector = 'section.s_dynamic_category'
    resources = {
        builder_options: [
            withSequence(DEVICE_VISIBILITY, {
                OptionComponent: DynamicSnippetCategoryOption,
                selector: this.selector,
                groups: ['website.group_website_designer'],
            }),
        ],
    };
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryOptionPlugin.id, DynamicSnippetCategoryOptionPlugin,
);
