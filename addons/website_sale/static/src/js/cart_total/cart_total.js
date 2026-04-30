import { Component, onWillStart, useState } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService, useBus } from "@web/core/utils/hooks";
import { useRef } from "@web/owl2/utils";

export class CartTotal extends Component {
    static template = "website_sale.CartTotal";
    static props = {
        templateData: Object,
        orderId: { type: Number, optional: true },
        hidePromotions: { type: Boolean },
    };

    setup() {
        this.state = useState({
            totals: {},
            errorMessage: "",
        });
        this.promoInput = useRef("promoInput");
        this.promoInputPlaceholder = _t("Discount code...");
        this.cartService = useService("cart");

        onWillStart(async () => {
            await this.updateTotals();
        });

        useBus(this.cartService.bus, "cart_update", () => {
            this.updateTotals();
            this.state.errorMessage = "";
        });
    }

    async updateTotals() {
        this.state.totals = await rpc("/shop/cart/totals", {
            order_id: this.props.orderId ? this.props.orderId : false,
        });
    }

    async applyPromoCode() {
        const data = await rpc("/shop/pricelist/apply", {
            promo: this.promoInput.el.value,
        });

        if (!data.success) {
            this.state.errorMessage = data.message;
        } else {
            this.cartService.bus.trigger("cart_update");
        }
    }

    formatPrice(price) {
        return formatCurrency(price, this.state.totals.currency_id);
    }
}
