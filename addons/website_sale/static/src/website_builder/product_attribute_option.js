import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class ProductAttributeOption extends BaseOptionComponent {
    static id = "product_attribute_option";
    static template = "website_sale.ProductAttributeOption";

    setup() {
        super.setup();
        this.domState = useDomState((el) => {
            const attributeEl = el.closest(".variant_attribute");
            const { attributeCreateVariant, attributeIsThumbnailVisible } = attributeEl.dataset;
            const isThumbnailVisible = !!attributeIsThumbnailVisible;
            return {
                // Variant images require 'instantly' created variants, unless already enabled
                canShowThumbnails: isThumbnailVisible || attributeCreateVariant === "always",
                isThumbnailVisible,
            };
        });
    }
}

registry.category("website-options").add(ProductAttributeOption.id, ProductAttributeOption);
