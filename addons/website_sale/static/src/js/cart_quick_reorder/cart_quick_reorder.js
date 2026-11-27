import { Component, onPatched, onWillStart, providePlugins, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { OrderHistoryLine } from "./order_history_line/order_history_line";
import { useService } from "@web/core/utils/hooks";
import { CartPlugin } from "@website_sale/js/cart_plugin";

export class CartQuickReorder extends Component {
    static template = "website_sale.CartQuickReorder";
    static components = { OrderHistoryLine };
    props = useProps({ templateData: t.object() });
    offCanvasRef = signal.ref();

    setup() {
        providePlugins([CartPlugin]);
        this.cartService = useService("cart");
        onWillStart(async () => await this.cartService.loadCart({ withHistory: true }));

        onPatched(() => {
            if (!this.orderHistory.length) {
                const offCanvas = Offcanvas.getInstance(this.offCanvasRef());
                if (offCanvas) {
                    offCanvas.hide();
                }
            }
        });
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
}
