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

const modelNameFilter = 'product.public.category';

export class DynamicSnippetCategoryOption2 extends DynamicSnippetCategoryOption {
    static selector = 'section.s_dynamic_snippet_category';
    static defaultProps = {
        modelNameFilter,
    };
    static groups = ['website.group_website_designer'];
}

export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryOptionPlugin';
    static dependencies = ['dynamicSnippetOption'];
    selector = DynamicSnippetCategoryOption2.selector;
    modelNameFilter = modelNameFilter;
    resources = {
        builder_options: [
            withSequence(DEVICE_VISIBILITY, DynamicSnippetCategoryOption2),
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
