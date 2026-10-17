import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ProductsItemOption extends BaseOptionComponent {
    static id = "products_item_option";
    static template = "website_sale.ProductsItemOptionPlugin";
    static dependencies = ["productsItemOptionPlugin"];

    setup() {
        super.setup();

        const { loadInfo } = this.dependencies.productsItemOptionPlugin;

        onWillStart(async () => {
            const defaultSort = await loadInfo();
            // Only display the "Re-order" option if shop_default_sort is 'website_sequence asc'
            this.displayReOrder = defaultSort[0].shop_default_sort === "website_sequence asc";
        });
    }
}

registry.category("website-options").add(ProductsItemOption.id, ProductsItemOption);
