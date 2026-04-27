/** @odoo-module */
import { ProductCatalogSaleOrderLine } from "@sale_stock/product_catalog/sale_order_line/sale_order_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogSaleOrderLine, {
    props: {
        ...ProductCatalogSaleOrderLine.props,
        tracking: Boolean,
        minimumQuantityOnProduct: Number,
    },
});

patch(ProductCatalogSaleOrderLine.prototype, {
    get disableRemove() {
        if (this.env.fsm_task_id) {
            return this.props.quantity === this.props.minimumQuantityOnProduct;
        }
        return this.props.quantity === this.props.deliveredQty;
    },
});
