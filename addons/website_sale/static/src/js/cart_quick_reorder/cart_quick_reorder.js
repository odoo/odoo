import { Component, onPatched, onWillStart, proxy, props, t } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useRef, useSubEnv } from "@web/owl2/utils";
import { OrderHistoryLine } from "./order_history_line/order_history_line";
import { useAutofocus, useBus, useService } from "@web/core/utils/hooks";

export class CartQuickReorder extends Component {
    static template = "website_sale.CartQuickReorder";
    static components = { OrderHistoryLine };
    props = props({ templateData: t.object() });

    setup() {
        this.state = proxy({
            is_public_user: true,
            order_history: [],
            currency_id: null,
        });
        this.cartService = useService("cart");
        this.offCanvasRef = useRef("quickReorderSidebar");

        useAutofocus();

        useSubEnv({
            formatPrice: this.formatPrice.bind(this),
            handleReorder: this.handleReorder.bind(this),
        });

        useBus(this.cartService.bus, "cart_update", () => {
            this.loadOrderHistory();
        });

        onWillStart(async () => {
            await this.loadOrderHistory();
        });

        onPatched(() => {
            if (!this.state.order_history.length) {
                const offCanvas = Offcanvas.getInstance(this.offCanvasRef.el);
                if (offCanvas) {
                    offCanvas.hide();
                }
            }
        });
    }

    async handleReorder(lineData) {
        await this.cartService.add(
            {
                productTemplateId: lineData.product_tmpl_id,
                productId: lineData.product_id,
                isCombo: lineData.is_combo,
                quantity: lineData.quantity,
                ...(lineData.is_combo && { selected_combo_items: lineData.selected_combo_items }),
            },
            {
                isBuyNow: true,
                source: "quick_reorder",
            }
        );
    }

    async loadOrderHistory() {
        const data = await rpc("/shop/cart/history");
        Object.assign(this.state, data);
    }

    get quickReorderTooltip() {
        if (this.state.is_public_user) {
            return _t("Login to reorder");
        } else if (!this.state.order_history.length) {
            return _t("No previous products available for reorder.");
        }
        return "";
    }

    formatPrice(price) {
        return formatCurrency(price, this.state.currency_id);
    }
}
