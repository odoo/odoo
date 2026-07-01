import { Component, onWillStart, proxy, props, t } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";

export class CartTotal extends Component {
    static template = "website_sale.CartTotal";
    props = props({
        templateData: t.object(),
        orderId: t.number().optional(),
        hidePromotions: t.boolean(),
    });

    setup() {
        this.state = proxy({
            totals: {},
            notification: {
                success: false,
                message: "",
            },
            promoCode: "",
        });
        this.promoInputPlaceholder = _t("Discount code...");
        this.cartService = useService("cart");

        onWillStart(async () => {
            await this.updateTotals();
        });

        useBus(this.cartService.bus, "cart_update", (ev) => {
            this.updateTotals();
            if (!ev.detail?.keepAlerts) {
                this.state.notification = {};
            }
        });
    }

    async updateTotals() {
        this.state.totals = await rpc("/shop/cart/totals", {
            order_id: this.props.orderId ? this.props.orderId : false,
        });
    }

    updatePromoCode(value) {
        this.state.promoCode = value;
    }

    async applyPromoCode() {
        const data = await rpc("/shop/pricelist/apply", {
            promo: this.state.promoCode,
        });

        this.state.notification = data;

        if (data.success) {
            this.cartService.bus.trigger("cart_update", { keepAlerts: true });
        }
    }

    formatPrice(price) {
        return formatCurrency(price, this.state.totals.currency_id);
    }
}
