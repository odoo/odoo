import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";

class ProductAttributeOptionPlugin extends Plugin {
    static id = "productAttributeOption";
    resources = {
        builder_options: {
            template: "website_sale.ProductAttributeOption",
            selector: "#product_detail .o_wsale_product_attribute",
            editableOnly: false,
            reloadTarget: true,
        },
        builder_actions: {
            ProductAttributeDisplayAction,
        },
    };

}

export class ProductAttributeDisplayAction extends BuilderAction {
    static id = "productAttributeDisplay";

    setup() {
        this.reload = {};
    }
    isApplied({ editingElement: el, value }) {
        return value === this.getProductAttributeDisplay(el);
    }
    getValue({ editingElement: el }) {
        return this.getProductAttributeDisplay(el);
    }
    async apply({ editingElement: el, value }) {
        const attributeID = parseInt(
            el.closest("[data-attribute_id]").dataset.attribute_id
        );
        await rpc("/shop/config/attribute", {
            attribute_id: attributeID,
            display_type: value,
        });
    }
    getProductAttributeDisplay(el) {
        return el.closest("[data-attribute_display_type]").dataset.attribute_display_type;
    }
}

registry
    .category("website-plugins")
    .add(ProductAttributeOptionPlugin.id, ProductAttributeOptionPlugin);
