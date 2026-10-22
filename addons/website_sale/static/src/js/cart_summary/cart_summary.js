import { Component, onWillStart, proxy, useProps, t } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { rpc } from "@web/core/network/rpc";
import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { formatDate } from "@web/core/l10n/dates";

export class CartSummary extends Component {
    static template = "website_sale.CartSummary";
    props = useProps({
        isOffcanvas: t.boolean().optional(false),
    });

    setup() {
        this.cartService = useService("cart");
        this.state = proxy({
            cart_lines: [],
            currency_id: null,
            cart_quantity: 0,
        });

        onWillStart(async () => {
            await this.updateSummary();
        });

        useBus(this.cartService.bus, "cart_update", async () => {
            await this.updateSummary();
        });
    }

    async updateSummary() {
        const data = await rpc("/shop/cart/summary");
        Object.assign(this.state, data);
    }

    get isScrollable() {
        return this.state.cart_lines.length > 4;
    }

    formatPrice(price) {
        return formatCurrency(price, this.state.currency_id);
    }

    // used in website_sale_loyalty and website_sale_renting
    formatDate(date) {
        const formattedDate = luxon.DateTime.fromISO(date);
        return formatDate(formattedDate);
    }
}

registry.category("public_components").add("website_sale.CartSummary", CartSummary);
