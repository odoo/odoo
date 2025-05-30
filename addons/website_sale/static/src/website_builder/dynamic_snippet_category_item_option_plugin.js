import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";


export class CategoryMediaDialog extends MediaDialog {
    async save(){
        rpc('/snippets/category/set_image',{
            category_id: parseInt(this.props.node.parentElement.dataset.categoryId),
            media: this.selectedMedia[this.state.activeTab],
        })
        this.props.close()
        await super.save();
    }
}

export class DynamicSnippetCategoryItemOptionPlugin extends Plugin {
    static id = 'dynamicSnippetCategoryItemOptionPlugin';
    static dependencies = ["media", "dialog", "builder-options"];
    resources = {
        builder_options: {
            template: "website_sale.dynamicSnippetCategoryItemOptions",
            selector: ".category_item, .all_products",
            editableOnly: false,
            title: _t("Category"),
        },
        builder_actions: this.getActions(),
    }
    getActions() {
        return {
            setCategoryImage: {
                reload: {},
                load: async ({ editingElement: el }) => {
                    const imageEl = el.querySelector(".s_category_image")
                    if(el.classList.contains("category_item")){
                        await new Promise((resolve) => {
                            this.dependencies.dialog.addDialog(CategoryMediaDialog, {
                                node: imageEl,
                                onlyImages: true,
                                noDocuments: true,
                                save: resolve,
                            });
                        });
                    } else {
                        let icon;
                        await this.dependencies.media.openMediaDialog({
                            node: imageEl,
                            onlyImages: true,
                            noDocuments: true,
                            save: (newIcon) => { icon = newIcon },
                        });
                        return icon;
                    }
                },
                apply: ({ editingElement: el, loadResult: newImage }) => {
                    if (!(newImage instanceof HTMLImageElement)) return;
                    el.querySelector(".s_category_image").replaceWith(newImage);
                    this.dependencies["builder-options"].updateContainers(newImage);
                },
            },
        }
    }
}

registry.category('website-plugins').add(
    DynamicSnippetCategoryItemOptionPlugin.id, DynamicSnippetCategoryItemOptionPlugin,
);
