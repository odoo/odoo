import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";

export class ProductsRibbonOption extends BaseOptionComponent {
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
