import { Component, onWillStart, useState } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';
import { rpc } from '@web/core/network/rpc';
import { useService, useBus } from "@web/core/utils/hooks";

export class CartTotal extends Component {
    static template = 'website_sale.CartTotal';
    static props = {};

    setup() {
        this.state = useState({
            amount_delivery: 0,
            amount_untaxed: 0,
            tax_subtotals: {},
            amount_total: 0,
            currency_id: null,
            has_carrier: false,
            has_deliverable_products: false,
        });
        this.cartService = useService('cart');

        onWillStart(async () => {
            await this.updateTotals();
        });

        useBus(this.cartService.bus, 'cart_update', () => {
            this.updateTotals();
        });
    }

    async updateTotals() {
        const data = await rpc('/shop/cart/totals');
        // !This can be improved a bit but I don't wanna define some nasty hooks for now just for adding
        // !a new assignment in extenstions
        Object.assign(this.state, data);
    }

    formatPrice(price) {
        return formatCurrency(price, this.state.currency_id);
    }
}
