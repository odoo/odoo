import { Plugin } from '@html_editor/plugin';
import { withSequence } from '@html_editor/utils/resource';
import { registry } from '@web/core/registry';
import { WEBSITE_BACKGROUND_OPTIONS } from '@website/builder/option_sequence';
import { before } from "@html_builder/utils/option_sequence";
import { CategoriesInlineOption } from './categories_inline_options';


export class CategoriesInlineOptionPlugin extends Plugin {
    static id = 'categoriesInlineOptionPlugin';
    selector = '.s_categories_inline';
    resources = {
        builder_options: [
            withSequence(before(WEBSITE_BACKGROUND_OPTIONS), {
                OptionComponent: CategoriesInlineOption,
                selector: this.selector,
            }),
            withSequence(WEBSITE_BACKGROUND_OPTIONS, {
                template: "website_sale.CategoriesInlineStyleOption",
                selector: this.selector,
            }),
        ],
        so_content_addition_selector: [".s_categories_inline"],
    };
}


registry.category('website-plugins').add(
    CategoriesInlineOptionPlugin.id, CategoriesInlineOptionPlugin,
);
