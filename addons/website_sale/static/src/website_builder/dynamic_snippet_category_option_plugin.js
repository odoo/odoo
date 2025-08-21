import { Plugin } from '@html_editor/plugin';
import { withSequence } from '@html_editor/utils/resource';
import { BuilderAction } from '@html_builder/core/builder_action';
import { registry } from '@web/core/registry';
import { DEVICE_VISIBILITY } from '@website/builder/option_sequence';
import {
    setDatasetIfUndefined
} from '@website/builder/plugins/options/dynamic_snippet_option_plugin';
import { DynamicSnippetCategoryOption } from './dynamic_snippet_category_options';

const TEMPLATE_OPTIONS = {
    'clickable': 'website_sale.dynamic_filter_template_product_public_category_clickable_items',
    'default': 'website_sale.dynamic_filter_template_product_public_category_default',
}

export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryOptionPlugin';
    static dependencies = ['dynamicSnippetOption'];
    selector = 'section.s_dynamic_snippet_category';
    modelNameFilter = 'product.public.category';
    resources = {
        builder_options: [
            withSequence(DEVICE_VISIBILITY, {
                OptionComponent: DynamicSnippetCategoryOption,
                props: {
                    modelNameFilter: this.modelNameFilter,
                },
                selector: this.selector,
                groups: ['website.group_website_designer'],
            }),
        ],
        builder_actions: { ToggleClickableAction },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            for (const [optionName, value] of [
                ['showParent', true],
                ['columns', 4],
                ['rounded', 2],
                ['gap', 2],
                ['size', 'medium'],
                ['button', 'Explore Now'],
                ['alignment', 'center'],
            ]) {
                setDatasetIfUndefined(snippetEl, optionName, value);
            }
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter,
                [],
            );
        }
    }
}

export class ToggleClickableAction extends BuilderAction {
    static id = 'toggleClickable';
    apply({ editingElement }) {
        const nodeData = editingElement.dataset;
        nodeData.templateKey = nodeData.templateKey === TEMPLATE_OPTIONS['default']
            ? TEMPLATE_OPTIONS['clickable']
            : TEMPLATE_OPTIONS['default'];
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryOptionPlugin.id, DynamicSnippetCategoryOptionPlugin,
);
