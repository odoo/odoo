import { Component, onWillUpdateProps, t, useProps, proxy } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class CartRewards extends Component {
    static template = "website_sale_loyalty.CartRewards";
    props = useProps({ rewards: t.array() });

    setup() {
        this.cartService = useService("cart");
        this.selectedProductIds = proxy(this.getDefaultProductIds(this.props.rewards));
        this.pendingRewardIds = proxy({});
        this.notification = proxy({ message: "", success: false });
        onWillUpdateProps((nextProps) => {
            Object.assign(this.selectedProductIds, this.getDefaultProductIds(nextProps.rewards));
        });
    }

    getDefaultProductIds(rewards) {
        return Object.fromEntries(
            rewards.flatMap((coupon) =>
                coupon.rewards
                    .filter((reward) => reward.multi_product)
                    .map((reward) => [reward.id, reward.products[0]?.id])
            )
        );
    }

    async claimReward(reward, coupon) {
        this.pendingRewardIds[reward.id] = true;
        const data = await rpc("/shop/claimreward", {
            reward_id: reward.id,
            code: coupon.coupon_code,
            product_id: reward.multi_product ? this.selectedProductIds[reward.id] : false,
        });
        this.notification.message = data.message || "";
        this.notification.success = data.success;
        if (data.success) {
            await this.cartService.refreshCartData(true);
        }
        this.pendingRewardIds[reward.id] = false;
    }
}
