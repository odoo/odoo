import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class ProductAttributeOptionPlugin extends Plugin {
    static id = "productAtttributeOption";
    resources = {
        builder_options: {
            template: "website_sale.ProductAttributeOption",
            selector: "#product_detail .o_wsale_product_attribute",
            editableOnly: false,
        },
        builder_actions: this.getActions(),
    };
    getActions() {
        return {
            productAttributeDisplay: {
                isReload: true,
                getReloadSelector: () => "#product_detail .o_wsale_product_attribute",
                isApplied: ({ editingElement: el, value }) =>
                    value === this.getProductAttributeDisplay(el),
                getValue: ({ editingElement: el }) => this.getProductAttributeDisplay(el),
                load: async ({ editingElement: el, value }) => {
                    const attributeID = parseInt(
                        el.closest("[data-attribute_id]").dataset.attribute_id
                    );
                    await rpc("/shop/config/attribute", {
                        attribute_id: attributeID,
                        display_type: value,
                    });
                },
                apply: () => {},
            },
        };
    }
    getProductAttributeDisplay(el) {
        return el.closest("[data-attribute_display_type]").dataset.attribute_display_type;
    }
}

registry
    .category("website-plugins")
    .add(ProductAttributeOptionPlugin.id, ProductAttributeOptionPlugin);
