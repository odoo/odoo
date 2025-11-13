import { REPLACE_MEDIA } from "@html_builder/utils/option_sequence";
import {
    ReplaceMediaOption,
} from "@html_builder/plugins/image/replace_media_option";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";


export class ProductImageOption extends BaseOptionComponent {
    static template = "website_sale.ProductImageOption";
    static selector =  `.o_wsale_product_images :is(${ReplaceMediaOption.selector})`;
    static exclude = ReplaceMediaOption.exclude;
}

export class ProductImageOptionPlugin extends Plugin {
    static id = "productImageOption";
    resources = {
        builder_options: [
            withSequence(REPLACE_MEDIA, ProductImageOption),
        ],
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
        patch_builder_options: [
            {
                target_name: "replaceMediaOption",
                target_element: "exclude",
                method: "add",
                value: ProductImageOption.selector,
            },
        ],
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
            image_res_model: el.parentElement.dataset.oeModel,
            image_res_id: el.parentElement.dataset.oeId,
            move: value,
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
        if (el.parentElement.dataset.oeModel === "product.image") {
            // Unlink the "product.image" record as it is not the main product image.
            await this.services.orm.unlink("product.image", [
                parseInt(el.parentElement.dataset.oeId),
            ]);
        }
        el.remove();
    }
}

registry.category("website-plugins").add(ProductImageOptionPlugin.id, ProductImageOptionPlugin);
