import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { RewardButton } from "@pos_self_order_loyalty/app/components/reward_button/reward_button";

patch(OrderWidget, {
    components: { ...OrderWidget.components, RewardButton },
});