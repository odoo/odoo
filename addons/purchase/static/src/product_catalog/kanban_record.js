import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogPurchaseOrderLine } from "./purchase_order_line/purchase_order_line";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
    },

    get orderLineComponent() {
        if (this.env.orderResModel === "purchase.order") {
            return ProductCatalogPurchaseOrderLine;
        }
        return super.orderLineComponent;
    },

    addProduct() {
        if (this.productCatalogData.quantity === 0 && this.productCatalogData.min_qty) {
            super.addProduct(this.productCatalogData.min_qty);
        } else {
            super.addProduct(...arguments);
        }
    },
});
