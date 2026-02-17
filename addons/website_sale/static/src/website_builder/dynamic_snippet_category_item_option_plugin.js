import { BuilderAction } from '@html_builder/core/builder_action';
import { Plugin } from '@html_editor/plugin';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';

export class DynamicSnippetCategoryItemOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryItemOptionPlugin';
    resources = {
        builder_actions: { SetCategoryImageAction },
    }
}

export class SetCategoryImageAction extends BuilderAction {
    static id = 'setCategoryImage';
    static dependencies = ['media', 'builderOptions'];

    setup() {
        this.canTimeout = false;
    }

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
