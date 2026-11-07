import { Component, onWillStart, useProps, t, signal } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { formatDate } from "@web/core/l10n/dates";
import { useDebounced } from "@web/core/utils/timing";

export class CartSummary extends Component {
    static template = "website_sale.CartSummary";
    props = useProps({
        isOffcanvas: t.boolean().optional(false),
        fromConfirmationPage: t.boolean(),
    });
    scrollBadge = signal.ref();

    setup() {
        this.cartService = useService("cart");
        this.debouncedOnScroll = useDebounced(this.onScroll.bind(this), 100);
        onWillStart(
            async () =>
                await this.cartService.loadCart(false, this.props.fromConfirmationPage, false)
        );
    }

    get data() {
        return this.cartService.state.lines;
    }

    get isScrollable() {
        return this.data.cart_lines?.length > 4;
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

    onScroll(event) {
        if (this.scrollBadge()) {
            this.scrollBadge().classList.toggle(
                "o_scrollable_table_badge_hidden",
                event.target.scrollTop > 0
            );
        }
    }
}

registry.category("public_components").add("website_sale.CartSummary", CartSummary);
