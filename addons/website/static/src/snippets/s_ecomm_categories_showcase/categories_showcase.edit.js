import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class EcommCategoriesShowcaseEdit extends Interaction {
    static selector = ".s_ecomm_categories_showcase";
    dynamicContent = {
        ".s_ecomm_categories_showcase_empty_alert": {
            "t-on-click": this.onAddBlock.bind(this),
        },
    };
    start() {
        // The "Add Blocks" message must be injected *before* the removal of the
        // last block, otherwise the wrapper is automatically removed by the
        // editor (see remove_plugin.isEmptyAndRemovable()), breaking
        // AddEcommCategoriesShowcaseBlockAction.apply().
        this.renderAt(
            "website.s_ecomm_categories_showcase.empty_alert",
            {},
            this.el.querySelector(".s_ecomm_categories_showcase_wrapper")
        );
    }
    onAddBlock() {
        const applySpec = { editingElement: this.el };
        this.services["website_edit"].applyAction("addEcommCategoriesShowcaseBlock", applySpec);
    }
}

registry.category("public.interactions.edit").add("website.ecomm_categories_showcase_edit", {
    Interaction: EcommCategoriesShowcaseEdit,
});
