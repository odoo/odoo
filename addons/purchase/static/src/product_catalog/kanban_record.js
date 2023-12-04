/** @odoo-module */
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogPurchaseOrderLine } from "./purchase_order_line/purchase_order_line";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useSubEnv } from "@odoo/owl";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        useSubEnv({
            updatePackagingQuantity: this.updatePackagingQuantity.bind(this),
        });
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

    async updatePackagingQuantity(packaging) {
        const productPackagingQty =
            Math.floor(this.productCatalogData.quantity / packaging.qty) + 1;
        this.productCatalogData.quantity = productPackagingQty * packaging.qty;
        const price = await rpc("/product/catalog/update_order_line_info", {
            order_id: this.env.orderId,
            product_id: this.env.productId,
            product_packaging_id: packaging.id,
            product_packaging_qty: productPackagingQty,
            res_model: this.env.orderResModel,
        });
        this.productCatalogData.price = parseFloat(price);
    },
});
