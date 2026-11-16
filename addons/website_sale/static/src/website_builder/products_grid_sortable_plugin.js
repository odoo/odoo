import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class ProductsGridSortablePlugin extends Plugin {
    static id = "productsGridSortable";

    resources = {
        on_ready_to_save_document_handlers: this.onSave.bind(this),
    };

    setup() {
        this.initialProductIds = this.getProductIds();
    }

    getProductIds() {
        const gridEl = this.editable.querySelector("#o_wsale_products_grid[data-wsale-sortable]");
        if (!gridEl) {
            return [];
        }
        return [...gridEl.querySelectorAll(":scope > .oe_product[data-product-template-id]")].map(
            (el) => parseInt(el.dataset.productTemplateId)
        );
    }

    async onSave() {
        const productIds = this.getProductIds();
        if (productIds.join() === this.initialProductIds.join()) {
            return;
        }
        await rpc("/shop/config/products/resequence", { product_ids: productIds });
        this.initialProductIds = productIds;
    }
}

registry.category("website-plugins").add(ProductsGridSortablePlugin.id, ProductsGridSortablePlugin);
