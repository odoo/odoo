import { Component, onWillStart, providePlugins, useProps, usePlugin, t, signal } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { useDebounced } from "@web/core/utils/timing";
import { CartPlugin } from "@website_sale/js/cart_plugin";

export class CartSummary extends Component {
    static template = "website_sale.CartSummary";
    props = useProps({
        isOffcanvas: t.boolean().optional(false),
        fromConfirmationPage: t.boolean(),
    });
    scrollBadge = signal.ref();

    setup() {
        providePlugins([CartPlugin]);
        this.cart = usePlugin(CartPlugin);
        this.cartService = useService("cart");
        this.debouncedOnScroll = useDebounced(this.onScroll.bind(this), 100);
        onWillStart(
            async () =>
                await this.cartService.loadCart({
                    fromConfirmationPage: this.props.fromConfirmationPage,
                })
        );
    }

    get data() {
        return this.cartService.state.lines;
    }

    get isScrollable() {
        return this.data.cart_lines?.length > 4;
    }

    get cartQuantity() {
        return this.data.cart_quantity;
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
