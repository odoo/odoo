import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ProductTemplateOption extends BaseOptionComponent {
    static template = "website_sale.ProductTemplateOption";
    static selector = ".o_wsale_product_page:has(.variant_attribute)";
    static editableOnly = false;
    static title = " ";

    setup() {
        this.domState = useDomState(async (el) => {
            const productProduct = el.querySelector('[data-oe-model="product.product"]');
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const variantID = productProduct ? parseInt(productProduct.dataset.oeId) : null;
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;

            return {
                variantID,
                templateId,
            }
        })
    }
}
