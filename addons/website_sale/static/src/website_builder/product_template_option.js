import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class ProductTemplateOption extends BaseOptionComponent {
    static id = "product_template_option";
    static template = "website_sale.ProductTemplateOption";

    setup() {
        super.setup();
        this.domState = useDomState(async (el) => {
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const model = "product.template";
            const field = "product_tag_ids";
            const productId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;

            return {
                model,
                field,
                productId,
            };
        });
    }
}

registry.category("website-options").add(ProductTemplateOption.id, ProductTemplateOption);
