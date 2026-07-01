import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

export class ProductTagImageOptionPlugin extends Plugin {
    static id = "productTagImageOption";
    resources = {
        builder_actions: {
            /*
             * Removes the image in the back-end
             */
            RemoveTagMediaAction,
        },
        builder_options_render_context: {
            tagImageSelector: "a:has([data-oe-model='product.tag'][data-oe-field='image']) img",
        },
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
            await rpc("/shop/config/tag", { tag_id: tag_id, image: false });
        }
        el.remove();
    }
}

registry
    .category("website-plugins")
    .add(ProductTagImageOptionPlugin.id, ProductTagImageOptionPlugin);
