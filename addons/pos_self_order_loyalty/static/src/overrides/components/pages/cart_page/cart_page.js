import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { RewardButton } from "@pos_self_order_loyalty/app/components/reward_button/reward_button";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { signal } from "@odoo/owl";
import { roundPrecision } from "@web/core/utils/numbers";

patch(CartPage, {
    components: { ...CartPage.components, RewardButton },
});

patch(CartPage.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.discountAsked = false;
        this.code = signal("");
        this.showCode = signal(false);
        this.applyCode = useTrackedAsync(this.applyCode.bind(this));
        this.selfOrder.currentOrder.recomputeRewards();
    },

    roundPoints(points) {
        return roundPrecision(points, 0.01);
    },

    async pay() {
        if (!this.discountAsked && this.selfOrder.currentOrder.getPartner()) {
            const discountReward = this.selfOrder.getLoyaltyPrograms("discount", true);
            this.discountAsked = true;
            if (Object.keys(discountReward).length > 0) {
                this.dialog.add(SelectRewardPopup, {
                    getPayload: (reward) => {
                        this.selfOrder.applyReward(reward);
                    },
                    rewardType: "discount",
                    claimableOnly: true,
                });
                return;
            }
        }
        await super.pay();
    },
    async applyCode() {
        if (!this.code()) {
            return;
        }
        const result = await this.selfOrder.applyCode(this.code());
        if (result) {
            this.code.set("");
        }
    },
    onKeydownCodeInput(ev) {
        if (ev.key.toUpperCase() === "ENTER") {
            this.applyCode.call();
        }
    },
    onClickShowCode() {
        this.showCode.set(!this.showCode());
    },
    canChangeQuantity(line, increase) {
        const result = super.canChangeQuantity(...arguments);
        if (line.is_reward_line && increase) {
            if (
                line.reward_id.reward_type === "discount" ||
                (line.reward_id.reward_type === "product" &&
                    line.qty + 1 > line.reward_id.reward_product_qty)
            ) {
                return false;
            }
        }
        return result;
    },
    changeQuantity(line, increase) {
        super.changeQuantity(...arguments);
        this.selfOrder.currentOrder.recomputeRewards();
    },
    doRemoveLine(line) {
        super.doRemoveLine(...arguments);
        this.selfOrder.currentOrder.recomputeRewards();
    },
    get lines() {
        const lines = super.lines;
        return lines.filter(
            (line) => !line.is_reward_line || line.reward_id.reward_type != "discount"
        );
    },
    get displayBeforeDiscount() {
        return this.selfOrder.currentOrder.lines.find(
            (line) => line.is_reward_line && line.reward_id.reward_type === "discount"
        );
    },
    getTotalDiscount() {
        return this.selfOrder.currentOrder.lines.reduce((total, line) => {
            if (line.is_reward_line && line.reward_id.reward_type === "discount") {
                return total + line.priceIncl;
            }
            return total;
        }, 0);
    },
    getLoyaltyProgramClass(program) {
        return program.uiState.pointsDifference > 0 ? "text-success" : "text-danger";
    },
});
