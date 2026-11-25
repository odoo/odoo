import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ProductCategoriesOption extends BaseOptionComponent {
    static id = "product_categories_option";
    static template = "website_sale.ProductCategoriesOption";
    static dependencies = ["productCategoriesOption"];

    setup() {
        super.setup();
        this.domState = useDomState((editingElement) => ({
            parentCategoryId: editingElement.dataset.parentCategoryId,
            showParent: !!editingElement.dataset.showParent,
        }));
        this.categories = [];

        onWillStart(async () => {
            this.categories = await this.dependencies.productCategoriesOption.getCategories();
        });
    }
}

registry.category("website-options").add(ProductCategoriesOption.id, ProductCategoriesOption);
