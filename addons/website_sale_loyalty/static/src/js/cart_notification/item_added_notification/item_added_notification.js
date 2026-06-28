import { patch } from "@web/core/utils/patch";
import { ItemAddedNotification } from
    "@website_sale/js/cart_notification/item_added_notification/item_added_notification";
import { PromotionProgressBar } from
    "@website_sale_loyalty/js/promotion_progress_bar/promotion_progress_bar";

patch(ItemAddedNotification, {
    components: { ...ItemAddedNotification.components, PromotionProgressBar },
    props: {
        ...ItemAddedNotification.props,
        promotion_progress_bars: { type: Array, optional: true },
    },
});
