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
                await this.cartService.loadCart({
                    fromConfirmationPage: this.props.fromConfirmationPage,
                    withHistory: !this.props.fromConfirmationPage,
                })
        );
    }

    get data() {
        return this.cartService.state.totals;
    }

    /**
     * Whether the untaxed amount of the order should be shown.
     *
     * @returns {Boolean}
     */
    get showUntaxedAmount() {
        return this.data.show_untaxed_amount;
    }

    /**
     * Whether the tax amounts of the order should be shown.
     *
     * @returns {Boolean}
     */
    get showTaxLines() {
        return this.data.show_tax_lines;
    }

    /**
     * Whether the total amount of the order should be shown.
     *
     * @returns {Boolean}
     */
    get showTotal() {
        return this.data.show_total;
    }

    updatePromoCode(value) {
        this.state.promoCode = value;
    }

    async applyPromoCode() {
        const data = await rpc("/shop/code/apply", {
            code: this.state.promoCode,
        });
        if (data.message) {
            this.notifications.add(data.message, {
                type: data.success ? "success" : "danger",
            });
        }
        if (data.success) {
            await this.cartService.loadCart({ force: true, withHistory: true });
            this.cartService.bus.trigger("cart_amount_changed", [data.amount, data.minor_amount]);
        }
        this.state.promoCode = "";
    }

    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }
}
