import { Plugin } from '@html_editor/plugin';
import { BuilderAction } from '@html_builder/core/builder_action';
import { registry } from '@web/core/registry';
import {
    dynamicContentOfDynamicSnippet,
    setSharedSnippetArg,
} from '@website/builder/plugins/options/dynamic_snippet_option_plugin';

const modelNameFilter = 'product.public.category';

export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryOptionPlugin';

    resources = {
        builder_actions: {
            ToggleClickableAction,
        },
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches("section.s_dynamic_snippet_category")) {
                return modelNameFilter;
            }
        },
    };
}

export class ToggleClickableAction extends BuilderAction {
    static id = 'toggleClickable';
    apply({ editingElement }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        const key = "website_sale.dynamic_filter_template_product_public_category_clickable_items";
        setSharedSnippetArg(dynamicEl, "content_template", key);
    }
    clean({ editingElement }) {
        const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
        const key = "website_sale.dynamic_filter_template_product_public_category_default";
        setSharedSnippetArg(dynamicEl, "content_template", key);
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryOptionPlugin.id, DynamicSnippetCategoryOptionPlugin,
);
