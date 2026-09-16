import { t, useProps } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ItemAddedNotification } from
    "@website_sale/js/cart_notification/item_added_notification/item_added_notification";
import { PromotionProgressBar } from
    "@website_sale_loyalty/js/promotion_progress_bar/promotion_progress_bar";

patch(ItemAddedNotification, {
    components: { ...ItemAddedNotification.components, PromotionProgressBar },
});

patch(ItemAddedNotification.prototype, {
    setup() {
        this.websiteSaleLoyaltyProps = useProps({
            promotion_progress_bars: t.array().optional(),
        });
    },
});
