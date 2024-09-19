import { Component, useEffect, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";
import { useService } from "@web/core/utils/hooks";

export class ProductInfoBanner extends Component {
    static template = "point_of_sale.ProductInfoBanner";
    static components = {};
    static props = {
        product: Object,
        info: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.fetchStock = useTrackedAsync((p) => this.pos.getProductInfo(p, 1));
        this.ui = useState(useService("ui"));
        this.state = useState({
            available_quantity: 0,
            price_with_tax: 0,
            price_without_tax: 0,
            tax_name: "",
            tax_amount: 0,
        });

        useEffect(
            () => {
                const fetchStocks = async () => {
                    let result = {};
                    if (!this.props.info) {
                        await this.fetchStock.call(this.props.product);
                        if (this.fetchStock.status === "error") {
                            throw this.fetchStock.result;
                        }
                        result = this.fetchStock.result;
                    } else {
                        result = this.props.info;
                    }

                    if (result) {
                        const productInfo = result.productInfo;
                        this.state.available_quantity = productInfo.total_qty_available;
                        this.state.price_with_tax = productInfo.all_prices.price_with_tax;
                        this.state.price_without_tax = productInfo.all_prices.price_without_tax;
                        this.state.tax_name = productInfo.all_prices.tax_details[0]?.name || "";
                        this.state.tax_amount = productInfo.all_prices.tax_details[0]?.amount || 0;
                    }
                };

                fetchStocks();
            },
            () => [this.props.product]
        );
    }

    get bannerBackground() {
        if (!this.props.product.is_storable || this.state.available_quantity > 10) {
            return "bg-info";
        }

        return this.state.available_quantity < 5 ? "bg-danger" : "bg-warning";
    }

    get bannerClass() {
        return `${this.ui.isSmall ? "flex-column" : "justify-content-between"} ${
            this.bannerBackground
        }`;
    }
}
