import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class ProductTagImageOption extends BaseOptionComponent {
    static template = "website_sale.ProductTagImageOption";
    static selector =  "#product_detail .o_wsale_product_tag_image img";
}

export class ProductTagImageOptionPlugin extends Plugin {
    static id = "productTagImageOption";
    resources = {
        builder_options: ProductTagImageOption,
        builder_actions: {
            /*
             * Removes the image in the back-end
             */
            RemoveTagMediaAction,
        },
        patch_builder_options: [
            {
                target_name: "replaceMediaOption",
                target_element: "exclude",
                method: "add",
                value: ProductTagImageOption.selector,
            },
        ],
    };
}

/*
 * Removes the image in the back-end
 */
export class RemoveTagMediaAction extends BuilderAction {
    static id = "removeTagMedia";

    setup() {
        this.reload = true;
    }

    async apply({ editingElement: el }) {
        if (el.parentElement.dataset.oeModel === "product.tag") {
            const tag_id = parseInt(el.parentElement.dataset.oeId);
            await rpc("/shop/config/tag", {
                tag_id: tag_id,
                image: false,
            });
        }
        el.remove()
    }
}

registry.category("website-plugins")
        .add(ProductTagImageOptionPlugin.id, ProductTagImageOptionPlugin);
