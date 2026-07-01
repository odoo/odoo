import { useDomState } from "@html_builder/core/utils";
import { ProductTemplateOption } from "./product_template_option";
import { registry } from "@web/core/registry";

export class ProductVariantOption extends ProductTemplateOption {
    static id = "product_variant_option";
    static template = "website_sale.ProductVariantOption";

    setup() {
        super.setup();
        this.domState = useDomState(async (el) => {
            const productProduct = el.querySelector('[data-oe-model="product.product"]');
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const variantId = productProduct ? parseInt(productProduct.dataset.oeId) : null;
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;
            const hasVariants = el.querySelector(".variant_attribute") || !templateId;

            const model = hasVariants ? "product.product" : "product.template";
            const field = hasVariants ? "additional_product_tag_ids" : "product_tag_ids";
            const productId = hasVariants ? variantId : templateId;
            const selection = this.modelEdit && this.modelEdit.has(field) ? this.modelEdit.get(field) : [];

            return {
                model,
                field,
                productId,
                selection,
            };
        });
    }
}

registry.category("website-options").add(ProductVariantOption.id, ProductVariantOption);
