import { Component, onWillStart, useState } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";

export class CartTotal extends Component {
    static template = "website_sale.CartTotal";
    static props = {
        templateData: Object,
        orderId: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({
            amount_delivery: 0,
            amount_untaxed: 0,
            tax_subtotals: {},
            amount_total: 0,
            currency_id: null,
            has_carrier: false,
            has_deliverable_products: false,
            tax_included: false,
        });
        this.cartService = useService("cart");

        onWillStart(async () => {
            await this.updateTotals();
        });

        useBus(this.cartService.bus, "cart_update", () => {
            this.updateTotals();
        });
    }

    async updateTotals() {
        const data = await rpc("/shop/cart/totals", {
            order_id: this.props.orderId ? this.props.orderId : false,
        });
        Object.assign(this.state, data);
    }

    formatPrice(price) {
        return formatCurrency(price, this.state.currency_id);
    }
}
