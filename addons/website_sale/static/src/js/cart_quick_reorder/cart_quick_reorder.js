import { Component, onPatched, onWillStart, signal, t, useProps } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { useSubEnv } from "@web/owl2/utils";
import { OrderHistoryLine } from "./order_history_line/order_history_line";
import { useService } from "@web/core/utils/hooks";

export class CartQuickReorder extends Component {
    static template = "website_sale.CartQuickReorder";
    static components = { OrderHistoryLine };
    props = useProps({ templateData: t.object() });
    offCanvasRef = signal.ref();

    setup() {
        this.cartService = useService("cart");
        onWillStart(async () => await this.cartService.loadCart({ withHistory: true }));

        useSubEnv({
            formatPrice: this.formatPrice.bind(this),
            handleReorder: this.handleReorder.bind(this),
        });

        onPatched(() => {
            if (!this.orderHistory.length) {
                const offCanvas = Offcanvas.getInstance(this.offCanvasRef());
                if (offCanvas) {
                    offCanvas.hide();
                }
            }
        });
    }

    async handleReorder(lineData) {
        const quantity = await this.cartService.add(
            {
                productTemplateId: lineData.product_tmpl_id,
                productId: lineData.product_id,
                isCombo: lineData.is_combo,
                quantity: lineData.quantity,
                ...(lineData.is_combo && { selected_combo_items: lineData.selected_combo_items }),
            },
            {
                isBuyNow: true,
                redirectToCart: false,
                showNotification: false,
                skipOrderAlert: true,
                // The cart summary isn't on the page if the cart was empty.
                renderShorterCartSummary: !this.cartService.state.lines.cart_lines?.length,
            }
        );
        if (quantity) {
            await this.cartService.loadCart({ force: true, withHistory: true });
        }
    }

    get quickReorderTooltip() {
        if (this.data.is_public_user) {
            return _t("Login to reorder");
        } else if (!this.orderHistory.length) {
            return _t("No previous products available for reorder.");
        }
        return "";
    }

    get data() {
        return this.cartService.state.history;
    }

    get orderHistory() {
        return this.data.order_history ?? [];
    }

    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }
}
