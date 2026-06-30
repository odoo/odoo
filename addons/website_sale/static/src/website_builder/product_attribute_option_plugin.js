import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class ProductAttributeOption extends BaseOptionComponent {
    static template = "website_sale.ProductAttributeOption";
    static selector = "#product_detail .o_wsale_product_attribute";
    static editableOnly = false;
    static reloadTarget = true;
}

class ProductAttributeOptionPlugin extends Plugin {
    static id = "productAttributeOption";
    resources = {
        builder_options: ProductAttributeOption,
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
            el.closest("[data-attribute-id]").dataset.attributeId
        );
        await rpc("/shop/config/attribute", {
            attribute_id: attributeID,
            display_type: value,
        });
    }
    getProductAttributeDisplay(el) {
        return el.closest("[data-attribute-display-type]").dataset.attributeDisplayType;
    }
}

registry
    .category("website-plugins")
    .add(ProductAttributeOptionPlugin.id, ProductAttributeOptionPlugin);
