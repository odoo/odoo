import { BuilderAction } from "@html_builder/core/builder_action";
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
    static dependencies = ['media', 'dialog', 'builderOptions'];

    async apply({ editingElement: el }) {
        const imageEl = el.querySelector('.s_category_image');
        await this.dependencies.media.openMediaDialog({
            node: imageEl,
            onlyImages: true,
            noDocuments: true,
            save: async (imgEls, selectedMedia, activeTab) => {
                // the category/set_image route is used to set images for category
                // record which are represented in snippet using s_dynamic_category_item class.
                rpc('/snippets/category/set_image', {
                    category_id: parseInt(imageEl.parentElement.dataset.categoryId),
                    attachment_id: selectedMedia[0]['id'],
                });
                if (!(imgEls instanceof HTMLImageElement)) return;
                el.querySelector('.s_category_image').replaceWith(imgEls);
                this.dependencies['builderOptions'].updateContainers(imgEls);
            },
        });
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryItemOptionPlugin.id, DynamicSnippetCategoryItemOptionPlugin,
);
