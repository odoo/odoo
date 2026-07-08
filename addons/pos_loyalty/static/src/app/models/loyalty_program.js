import { registry } from "@web/core/registry";
import { Base } from "@point_of_sale/app/models/related_models";

/**
 * Support different type of programs
 *
 * - Gift Card (gift_card)
 *   Created manually or automatically sent by email when the customer
 *   orders a gift card product. Then, Gift Cards can be used to pay orders.
 *
 * - eWallet (ewallet)
 *   Created manually or automatically when the customer orders a eWallet
 *   product. Then, eWallets are proposed during the checkout, to pay orders.
 *
 * - Coupons (coupons)
 *   Generate & share coupon codes manually. It can be used in eCommerce,
 *   Point of Sale or regular orders to claim the Reward. You can define
 *   constraints on its usage through conditional rule.
 *
 * - Loyalty cards (loyalty)
 *   When customers make an order, they accumulate points they can
 *   exchange for rewards on the current order or on a future one.
 *   The reward can be used on the current or future order.
 *
 * - Promotions (promotion)
 *   Set up conditional rules on the order that will give access to
 *   rewards for customers, the reward must be used on the current order
 *
 * - Discount Code (promo_code)
 *   Define Discount codes on conditional rules then share it with your
 *   customers for rewards.
 *
 * - Buy X Get Y Free (buy_x_get_y)
 *   Grant 1 credit for each item bought then reward the customer with
 *   Y items in exchange of X credits.
 *
 * - Next Order Coupons (next_order_coupons)
 *   Drive repeat purchases by sending a unique, single-use coupon code
 *   for the next purchase when a customer buys something in your store.
 */

export class LoyaltyProgram extends Base {
    static pythonModel = "loyalty.program";

    availableRewards(order) {
        const points = this.rule_ids.reduce((total, r) => total + r.getPoints(order), 0);
        return this.reward_ids.filter((r) => r.getRewards(order, points));
    }

    useProgram(order) {
        const type = this.program_type;
        if (type === "gift_card" || type === "ewallet") {
            return;
        }

        const points = this.rule_ids.map((r) => r.getPoints(order));
        const rewards = this.reward_ids.map((r) => r.getRewards(order, points));
        console.log(this.name, this.program_type, points, rewards);
    }
}

registry.category("pos_available_models").add(LoyaltyProgram.pythonModel, LoyaltyProgram);
