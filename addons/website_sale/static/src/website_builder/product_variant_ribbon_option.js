import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";

export class ProductVariantRibbonOption extends BaseOptionComponent {
    static name = "ProductVariantRibbonOption";
    static template = 'website_sale.ProductVariantRibbonOptionPlugin';
    static dependencies = ['productVariantRibbonOptionPlugin'];
    static editableOnly = false;

    setup() {
        super.setup();

        const {loadInfo, getCount} = this.dependencies.productVariantRibbonOptionPlugin;
        this.count = useState(getCount());

        this.state = useState({
            ribbons: [],
            ribbonEditMode: false,
        });

        this.domState = useDomState(async (el) => {
            const productTemplate = el.querySelector('[data-oe-model="product.template"]');
            const templateId = productTemplate ? parseInt(productTemplate.dataset.oeId) : null;
            const variantMode = el.querySelector(".variant_attribute") || !templateId;

            return {
                variantMode,
            }
        })

        onWillStart(async () => {
            this.state.ribbons = await loadInfo();
        });
    }
}
