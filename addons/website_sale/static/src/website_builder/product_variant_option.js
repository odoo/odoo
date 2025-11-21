import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ProductVariantOption extends BaseOptionComponent {
    static template = "website_sale.ProductVariantOption";
    static selector = "#product_detail";
    static editableOnly = false;
    static title = " ";

    setup() {
        this.domState = useDomState(async (el) => {
            const productProduct = el.querySelector('[data-oe-model="product.product"]');
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const variantId = productProduct ? parseInt(productProduct.dataset.oeId) : null;
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;

            const hasVariants = el.querySelector(".variant_attribute") || !templateId;

            const model = hasVariants ? "product.product" : "product.template";
            const field = hasVariants ? "additional_product_tag_ids": "product_tag_ids";
            const productId = hasVariants ? variantId : templateId;

            return {
                model,
                field,
                productId,
            }
        })
    }
}
