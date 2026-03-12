import { Component, onWillStart, proxy, t, useProps, usePlugin } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";

export class CartTotal extends Component {
    static template = "website_sale.CartTotal";
    props = useProps({
        templateData: t.object(),
        fromConfirmationPage: t.boolean(),
        hidePromotions: t.boolean(),
    });
    notifications = usePlugin(NotificationPlugin);

    setup() {
        this.state = proxy({
            promoCode: "",
        });
        this.promoInputPlaceholder = _t("Discount code...");
        this.cartService = useService("cart");
        onWillStart(
            async () =>
                await this.cartService.loadCart(
                    false,
                    this.props.fromConfirmationPage,
                    !this.props.fromConfirmationPage
                )
        );
    }

    get data() {
        return this.cartService.state.totals;
    }

    updatePromoCode(value) {
        this.state.promoCode = value;
    }

    async applyPromoCode() {
        const data = await rpc("/shop/pricelist/apply", {
            promo: this.state.promoCode,
        });
        if (data.message) {
            this.notifications.add(data.message, {
                type: data.success ? "success" : "danger",
            });
        }
        if (data.success) {
            await this.cartService.loadCart(true, false, true);
        }
        this.state.promoCode = "";
    }

    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }
}
