import { Component, onWillStart, proxy, t, useProps } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";

export class CartTotal extends Component {
    static template = "website_sale.CartTotal";
    props = useProps({
        templateData: t.object(),
        fromConfirmationPage: t.boolean(),
        hidePromotions: t.boolean(),
    });

    setup() {
        this.state = proxy({
            notification: {
                success: false,
                message: "",
            },
            promoCode: "",
        });
        this.promoInputPlaceholder = _t("Discount code...");
        this.cartService = useService("cart");
        onWillStart(async () => {
            await this.cartService.mutex.exec(
                async () =>
                    await this.cartService.loadCartData(
                        false,
                        this.props.fromConfirmationPage,
                        !this.props.fromConfirmationPage
                    )
            );
        });

        useBus(this.cartService.bus, "cart_update", (ev) => {
            if (ev.detail.clearAlerts) {
                this.state.notification = {};
            }
        });
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
        this.state.notification = data;
        if (data.success) {
            await this.cartService.refreshCartData(false);
        }
    }

    formatPrice(price) {
        return formatCurrency(price, this.cartService.state.currency_id);
    }
}
