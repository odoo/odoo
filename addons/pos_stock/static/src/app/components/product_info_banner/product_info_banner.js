import { useEffect, onWillUnmount } from "@odoo/owl";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";
import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";

patch(ProductInfoBanner.prototype, {
    setup() {
        super.setup();
        this.fetchStock = useTrackedAsync((pt, p) => this.pos.getProductInfo(pt, 1, 0, p), {
            keepLast: true,
        });

        const debouncedFetchStocks = debounce(async (product, productTemplate) => {
            let result = {};
            if (!this.props.info) {
                await this.fetchStock.call(productTemplate, product);
                if (this.fetchStock.status === "error") {
                    throw this.fetchStock.result;
                }
                result = this.fetchStock.result;
            } else {
                result = this.props.info;
            }

            if (result) {
                const productInfo = result.productInfo;
                this.state.other_warehouses = productInfo.warehouses.slice(1);
                this.state.available_quantity = productInfo.warehouses[0]?.available_quantity;
                this.state.free_qty = productInfo.warehouses[0]?.free_qty;
                this.state.uom = productInfo.warehouses[0]?.uom;
            }
        }, 500);

        useEffect(
            () => {
                if (this.props.productTemplate) {
                    debouncedFetchStocks(this.props.product, this.props.productTemplate);
                }
            },
            () => [this.props.product]
        );
        onWillUnmount(() => debouncedFetchStocks.cancel());
    },
});
