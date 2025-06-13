import { BuilderAction } from '@html_builder/core/builder_action';
import { Plugin } from '@html_editor/plugin';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';


export class DynamicSnippetCategoryItemOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryItemOptionPlugin';
    resources = {
        builder_options: {
            template: 'website_sale.dynamicSnippetCategoryItemOptions',
            selector: '.s_dynamic_category_item, .all_products',
            editableOnly: false,
            title: _t("Category"),
        },
        builder_actions: { SetCategoryImageAction },
    }
}

class SetCategoryImageAction extends BuilderAction {
    static id = 'setCategoryImage';
    static dependencies = ['media', 'builderOptions'];

    async apply({ editingElement: el }) {
        const categoryId = el.dataset.categoryId;
        const categoryImage = el.querySelector('[name="category_image"]');
        if (!categoryImage) return;
        await this.dependencies.media.openMediaDialog({
            node: categoryImage,
            onlyImages: true,
            noDocuments: true,
            save: async (selectedImageEl, selectedMedia) => {
                rpc('/snippets/category/set_image', {
                    category_id: parseInt(categoryId),
                    attachment_id: selectedMedia[0]['id'],
                });
                if (!(selectedImageEl instanceof HTMLImageElement)) return;
                categoryImage.replaceWith(selectedImageEl);
                this.dependencies['builderOptions'].updateContainers(selectedImageEl);
            },
        });
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryItemOptionPlugin.id, DynamicSnippetCategoryItemOptionPlugin,
);
