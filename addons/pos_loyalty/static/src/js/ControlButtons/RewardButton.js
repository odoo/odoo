/** @odoo-module **/

import { Gui } from "@point_of_sale/js/Gui";
import PosComponent from "@point_of_sale/js/PosComponent";
import ProductScreen from "@point_of_sale/js/Screens/ProductScreen/ProductScreen";
import Registries from "@point_of_sale/js/Registries";
import { useListener } from "@web/core/utils/hooks";

export class RewardButton extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this.onClick);
    }

    /**
     * If rewards are the same, prioritize the one from freeProductRewards.
     * Make sure that the reward is claimable first.
     */
    _mergeFreeProductRewards(freeProductRewards, potentialFreeProductRewards) {
        const result = [];
        for (const reward of potentialFreeProductRewards) {
            if (!freeProductRewards.find((item) => item.reward.id === reward.reward.id)) {
                result.push(reward);
            }
        }
        return freeProductRewards.concat(result);
    }

    _getPotentialRewards() {
        const order = this.env.pos.get_order();
        // Claimable rewards excluding those from eWallet programs.
        // eWallet rewards are handled in the eWalletButton.
        let rewards = [];
        if (order) {
            const claimableRewards = order.getClaimableRewards();
            rewards = claimableRewards.filter(
                ({ reward }) => reward.program_id.program_type !== "ewallet"
            );
        }
        const discountRewards = rewards.filter(({ reward }) => reward.reward_type == "discount");
        const freeProductRewards = rewards.filter(({ reward }) => reward.reward_type == "product");
        const potentialFreeProductRewards = order.getPotentialFreeProductRewards();
        return discountRewards.concat(
            this._mergeFreeProductRewards(freeProductRewards, potentialFreeProductRewards)
        );
    }

    _isDisabled() {}

    hasClaimableRewards() {
        return this._getPotentialRewards().length > 0;
    }

    /**
     * Applies the reward on the current order, if multiple products can be claimed opens a popup asking for which one.
     *
     * @param {Object} reward
     * @param {Integer} coupon_id
     */
    async _applyReward(reward, coupon_id, potentialQty) {
        const order = this.env.pos.get_order();
        order.disabledRewards.delete(reward.id);

        const args = {};
        if (reward.reward_type === "product" && reward.multi_product) {
            const productsList = reward.reward_product_ids.map((product_id) => ({
                id: product_id,
                label: this.env.pos.db.get_product_by_id(product_id).display_name,
                item: product_id,
            }));
            const { confirmed, payload: selectedProduct } = await this.showPopup("SelectionPopup", {
                title: this.env._t("Please select a product for this reward"),
                list: productsList,
            });
            if (!confirmed) {
                return false;
            }
            args["product"] = selectedProduct;
        }
        if (
            (reward.reward_type == "product" && reward.program_id.applies_on !== "both") ||
            (reward.program_id.applies_on == "both" && potentialQty)
        ) {
            // Delegate the addition of product and reward update to the `click-product` event.
            this.trigger(
                "click-product",
                this.env.pos.db.get_product_by_id(args["product"] || reward.reward_product_ids[0])
            );
            return true;
        } else {
            const result = order._applyReward(reward, coupon_id, args);
            if (result !== true) {
                // Returned an error
                Gui.showNotification(result);
            }
            order._updateRewards();
            return result;
        }
    }

    async onClick() {
        const rewards = this._getPotentialRewards();
        if (rewards.length === 1) {
            return this._applyReward(
                rewards[0].reward,
                rewards[0].coupon_id,
                rewards[0].potentialQty
            );
        } else {
            const rewardsList = rewards.map((reward) => ({
                id: reward.reward.id,
                label: reward.reward.description,
                item: reward,
            }));
            const { confirmed, payload: selectedReward } = await this.showPopup("SelectionPopup", {
                title: this.env._t("Please select a reward"),
                list: rewardsList,
            });
            if (confirmed) {
                return this._applyReward(
                    selectedReward.reward,
                    selectedReward.coupon_id,
                    selectedReward.potentialQty
                );
            }
        }
        return false;
    }
}

RewardButton.template = "RewardButton";

ProductScreen.addControlButton({
    component: RewardButton,
    condition: function () {
        return this.env.pos.programs.length > 0;
    },
});

Registries.Component.add(RewardButton);
