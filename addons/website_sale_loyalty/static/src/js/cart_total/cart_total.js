import { CartTotal } from "@website_sale/js/cart_total/cart_total";
import { patch } from "@web/core/utils/patch";
import { PromotionProgressBar } from "../promotion_progress_bar/promotion_progress_bar";
import { _t } from "@web/core/l10n/translation";

patch(CartTotal, {
    components: {
        ...CartTotal.components,
        PromotionProgressBar,
    },
});

patch(CartTotal.prototype, {
    setup() {
        super.setup();
        this.promoInputPlaceholder = _t("Gift card or discount code...");
    },
});
