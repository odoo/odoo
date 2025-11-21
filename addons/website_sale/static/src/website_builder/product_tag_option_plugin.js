import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";

export class ProductTagOptionPlugin extends Plugin {
    static id = "productTagOption";
    resources = {
        builder_actions: {
            ProductTagColorAction,
            ProductTagImageAction,
        },
        builder_options_render_context: {
            tagSelector: "a:has([data-oe-model='product.tag'][data-oe-field='name'])",
        },
    };
}

export class ProductTagColorAction extends BuilderAction {
    static id = "productTagColorAction";
    static dependencies = ["savePlugin"];

    setup() {
        this.preview = false;
    }

    getValue({ editingElement: el }) {
        const tag_element = el.querySelector("[data-oe-model='product.tag']");
        return tag_element?.style.color;
    }

    async apply({ editingElement: el, value }) {
        const tag_element = el.querySelector("[data-oe-model='product.tag']");
        const tag_id = parseInt(tag_element.dataset.oeId);
        await rpc("/shop/config/tag", { tag_id: tag_id, color: value });
        await this.dependencies.savePlugin.save();
        await this.config.reloadEditor();
    }
}

export class ProductTagImageAction extends BuilderAction {
    static id = "productTagImageAction";
    static dependencies = ["media"];

    async load({ editingElement: el }) {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                addFieldImage: true,
                multiImages: false,
                visibleTabs: ["IMAGES"],
                node: el,
                save: async (imgEl, selectedMedia) => {
                    if (selectedMedia.length) {
                        resolve({ imgEl, selectedMedia });
                    }
                },
            });
            onClose.then(resolve);
        });
    }

    async apply({ editingElement: el, loadResult }) {
        const tag_element = el.querySelector("[data-oe-model='product.tag']");
        const tag_id = parseInt(tag_element.dataset.oeId);
        if (!loadResult) {
            return BuilderAction.cancelReload;
        }
        const { imgEl, selectedMedia } = loadResult;

        this.setTagImage(el, tag_id, imgEl.src);

        await rpc("/shop/config/tag", { tag_id: tag_id, image: selectedMedia[0]["id"] });
    }

    setTagImage(editingElement, tag_id, imageUrl) {
        const tagElement = editingElement.querySelector("[data-oe-model='product.tag']");
        tagElement.innerHTML = "";
        tagElement.className = "order-0 o_savable";
        tagElement.dataset.oeType = "image";
        tagElement.dataset.oeExpression = "tag.image";
        tagElement.dataset.oeField = "image";
        tagElement.dataset.oeId = tag_id;
        tagElement.style = "";

        const img = document.createElement("img");
        img.src = imageUrl;
        img.className = "img img-fluid o_product_tag_img rounded";

        tagElement.appendChild(img);
    }
}

registry.category("website-plugins").add(ProductTagOptionPlugin.id, ProductTagOptionPlugin);
