import { useDomState } from "@html_builder/core/utils";
import { ProductTemplateOption } from "./product_template_option";
import { registry } from "@web/core/registry";

export class ProductVariantOption extends ProductTemplateOption {
    static id = "product_variant_option";
    static template = "website_sale.ProductVariantOption";

    setup() {
        super.setup();
        this.domState = useDomState(async (el) => {
            const productProduct = el.querySelector("[data-product-variant-id]");
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const variantId = productProduct
                ? parseInt(productProduct.dataset.productVariantId)
                : null;
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;
            const hasVariants = el.querySelector(".variant_attribute") || !templateId;

            const model = hasVariants ? "product.product" : "product.template";
            const field = hasVariants ? "additional_product_tag_ids" : "product_tag_ids";
            const productId = hasVariants ? variantId : templateId;

            return {
                model,
                field,
                productId,
            };
        });
    }
}

registry.category("website-options").add(ProductVariantOption.id, ProductVariantOption);
