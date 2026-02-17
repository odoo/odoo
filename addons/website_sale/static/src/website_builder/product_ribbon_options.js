import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ProductsRibbonOption extends BaseOptionComponent {
    static id = "products_ribbon_option";
    static template = 'website_sale.ProductsRibbonOptionPlugin';
    static dependencies = ['productsRibbonOptionPlugin'];

    setup() {
        super.setup();

        const {loadInfo, getCount} = this.dependencies.productsRibbonOptionPlugin;
        this.count = useState(getCount());

        this.state = useState({
            ribbons: [],
            ribbonEditMode: false,
        });

        onWillStart(async () => {
            this.state.ribbons = await loadInfo();
        });
    }
}

registry.category("website-options").add(ProductsRibbonOption.id, ProductsRibbonOption);
