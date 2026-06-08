import { patch } from "@web/core/utils/patch";
import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";

patch(ProductInfoBanner.prototype, {
    updateState(productInfo) {
        super.updateState(productInfo);
        this.state.other_warehouses = productInfo.warehouses.slice(1);
        this.state.available_quantity = productInfo.warehouses[0]?.available_quantity;
        this.state.free_qty = productInfo.warehouses[0]?.free_qty;
        this.state.uom = productInfo.warehouses[0]?.uom;
    },
});
