import { Plugin } from '@html_editor/plugin';
import { BuilderAction } from '@html_builder/core/builder_action';
import { registry } from '@web/core/registry';

const TEMPLATE_OPTIONS = {
    'clickable': 'website_sale.dynamic_filter_template_product_public_category_clickable_items',
    'default': 'website_sale.dynamic_filter_template_product_public_category_default',
}

const modelNameFilter = 'product.public.category';

export class DynamicSnippetCategoryOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryOptionPlugin';
    static dependencies = ['dynamicSnippetOption'];

    modelNameFilter = modelNameFilter;
    resources = {
        builder_actions: { ToggleButtonAction: ToggleButtonAction },
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches("section.s_dynamic_snippet_category")) {
            await this.dependencies.dynamicSnippetOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter,
                [],
            );
        }
    }
}

export class ToggleButtonAction extends BuilderAction {
    static id = 'toggleButton';
    static dependencies = ['dynamicSnippetOption'];
    isApplied({ editingElement }) {
        return editingElement.dataset.templateKey === TEMPLATE_OPTIONS.default;
    }
    apply({ editingElement }) {
        const { getTemplateByKey, updateTemplate } = this.dependencies.dynamicSnippetOption;
        updateTemplate(editingElement, getTemplateByKey(TEMPLATE_OPTIONS.default));
        editingElement.classList.remove('s_dynamic_category_clickable_items');
    }
    clean({ editingElement }) {
        const { getTemplateByKey, updateTemplate } = this.dependencies.dynamicSnippetOption;
        updateTemplate(editingElement, getTemplateByKey(TEMPLATE_OPTIONS.clickable));
        editingElement.classList.add('s_dynamic_category_clickable_items');
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryOptionPlugin.id, DynamicSnippetCategoryOptionPlugin,
);
