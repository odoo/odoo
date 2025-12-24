import { useLayoutEffect, useState } from "@web/owl2/utils";
import { Component, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";
import { AccordionItem } from "@point_of_sale/app/components/accordion_item/accordion_item";
import { debounce } from "@web/core/utils/timing";

export class ProductInfoBanner extends Component {
    static template = "point_of_sale.ProductInfoBanner";
    static components = {
        AccordionItem,
    };
    static props = {
        productTemplate: Object,
        product: { type: [Object, { value: null }], optional: true },
        info: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.fetchStock = useTrackedAsync((pt, p) => this.pos.getProductInfo(pt, 1, 0, p), {
            keepLast: true,
        });
        this.ui = useService("ui");
        this.state = useState({
            other_warehouses: [],
            available_quantity: 0,
            free_qty: 0,
            uom: "",
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
                this.updateState(result.productInfo);
            }
        }, 500);

        useLayoutEffect(
            () => {
                if (this.props.productTemplate) {
                    debouncedFetchStocks(this.props.product, this.props.productTemplate);
                }
            },
            () => [this.props.product]
        );
        onWillUnmount(() => debouncedFetchStocks.cancel());
    }

    updateState(productInfo) {
        this.state.free_qty = productInfo.free_qty;
        this.state.uom = productInfo.uom;
    }
}
