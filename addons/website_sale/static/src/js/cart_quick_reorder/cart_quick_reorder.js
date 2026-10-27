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
        onWillStart(async () => {
            await this.cartService.mutex.exec(async () => await this.cartService.loadCartData());
        });

        useSubEnv({
            formatPrice: this.formatPrice.bind(this),
            handleReorder: this.handleReorder.bind(this),
        });

        onPatched(() => {
            if (!this.data.order_history.length) {
                const offCanvas = Offcanvas.getInstance(this.offCanvasRef());
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

    get quickReorderTooltip() {
        if (this.data.is_public_user) {
            return _t("Login to reorder");
        } else if (!this.data.order_history.length) {
            return _t("No previous products available for reorder.");
        }
        return "";
    }

    get data() {
        return this.cartService.state.history;
    }

    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }
}
