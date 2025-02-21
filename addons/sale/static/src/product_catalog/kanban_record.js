import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogSaleOrder } from "./sale_order_line/sale_order_line";

export class SaleProductCatalogKanbanRecord extends ProductCatalogKanbanRecord {
    static components = {
        ...ProductCatalogKanbanRecord.components,
        ProductCatalogSaleOrder,
    };

    setup() {
        super.setup();
    }

    get orderLineComponent() {
        if (this.env.orderResModel === "sale.order") {
            return ProductCatalogSaleOrder;
        }
        return super.orderLineComponent;
    }
};
