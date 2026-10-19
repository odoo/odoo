import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

export class ProductImageOptionPlugin extends Plugin {
    static id = "productImageOption";
    resources = {
        builder_actions: {
            /*
             * Change sequence of product page images
             */
            SetPositionAction,
            /*
             * Removes the image in the back-end
             */
            RemoveMediaAction,
        },
    };
}

/*
* Change sequence of product page images
*/
export class SetPositionAction extends BuilderAction {
    static id = "setPosition";
    setup() {
        this.reload = {};
    }
    async apply({ editingElement: el, value }) {
        const params = {
            image_res_id: el.parentElement.dataset.oeId,
            move: value,
            product_variant_id: this.document.querySelector('[data-product-variant-id]').dataset.productVariantId,
        };

        await rpc("/shop/product/resequence-image", params);
    }
}
/*
 * Removes the image in the back-end
 */
export class RemoveMediaAction extends BuilderAction {
    static id = "removeMedia";
    setup() {
        this.reload = {};
    }
    async apply({ editingElement: el }) {
        const wrapper = el.closest("[data-oe-model='product.image']");
        if (wrapper) {
            await this.services.orm.unlink("product.image", [parseInt(wrapper.dataset.oeId)]);
            wrapper.remove();
        } else {
            el.remove();
        }
    }
}

registry.category("website-plugins").add(ProductImageOptionPlugin.id, ProductImageOptionPlugin);
