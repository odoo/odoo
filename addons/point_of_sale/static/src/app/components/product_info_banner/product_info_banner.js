import { Component, useEffect, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";
import { AccordionItem } from "@point_of_sale/app/components/accordion_item/accordion_item";

export class ProductInfoBanner extends Component {
    static template = "point_of_sale.ProductInfoBanner";
    static components = {
        AccordionItem,
    };
    static props = {
        productTemplate: Object,
        product: { type: Object | null, optional: true },
        info: { type: Object, optional: true },
        showProductName: { type: Boolean, optional: true },
        showSelfOrder: { type: Boolean, optional: true },
    };
    static defaultProps = {
        showProductName: true,
        showSelfOrder: false,
    };

    setup() {
        this.pos = usePos();
        this.fetchStock = useTrackedAsync((pt, p) => this.pos.getProductInfo(pt, 1, 0, p));
        this.ui = useState(useService("ui"));
        this.state = useState({
            other_warehouses: [],
            available_quantity: 0,
            price_with_tax: 0,
            price_without_tax: 0,
            tax_name: "",
            tax_amount: 0,
        });

        useEffect(
            () => {
                if (!this.props.productTemplate) {
                    return;
                }

                const fetchStocks = async () => {
                    let result = {};
                    if (!this.props.info) {
                        await this.fetchStock.call(this.props.productTemplate, this.props.product);
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
                        this.state.available_quantity =
                            productInfo.warehouses[0]?.available_quantity;
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
        if (!this.props.productTemplate.is_storable || this.state.available_quantity > 10) {
            return "bg-info";
        }

        return this.state.available_quantity < 5 ? "bg-danger" : "bg-warning";
    }

    get bannerClass() {
        return this.bannerBackground;
    }
}
