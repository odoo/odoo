import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ProductsRibbonOption extends BaseOptionComponent {
    static id = "products_ribbon_option";
    static template = 'website_sale.ProductsRibbonOptionPlugin';
    static dependencies = ['productsRibbonOptionPlugin'];

    setup() {
        super.setup();

        const {loadInfo, getCount} = this.dependencies.productsRibbonOptionPlugin;
        this.count = proxy(getCount());

        this.state = proxy({
            ribbons: [],
            ribbonEditMode: false,
        });

        onWillStart(async () => {
            this.state.ribbons = await loadInfo();
        });
    }
}

registry.category("website-options").add(ProductsRibbonOption.id, ProductsRibbonOption);
