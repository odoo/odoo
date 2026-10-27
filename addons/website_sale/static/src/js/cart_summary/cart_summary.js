import { Component, onWillStart, useProps, t } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { formatDate } from "@web/core/l10n/dates";

export class CartSummary extends Component {
    static template = "website_sale.CartSummary";
    props = useProps({
        isOffcanvas: t.boolean().optional(false),
    });

    setup() {
        this.cartService = useService("cart");
        onWillStart(async () => {
            await this.cartService.mutex.exec(async () => await this.cartService.loadCartData());
        });
    }

    get data() {
        return this.cartService.state.lines;
    }

    get isScrollable() {
        return this.data.cart_lines.length > 4;
    }

    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }

    get cartQuantity() {
        return this.data.cart_quantity;
    }

    // used in website_sale_loyalty and website_sale_renting
    formatDate(date) {
        const formattedDate = luxon.DateTime.fromISO(date);
        return formatDate(formattedDate);
    }
}

registry.category("public_components").add("website_sale.CartSummary", CartSummary);
