import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";
import { useService } from "@web/core/utils/hooks";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";

patch(CartPage.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.discountAsked = false;
        this.state.couponCode = "";
        this.state.showCode = false;
        this.applyCouponCode = useTrackedAsync(this.applyCouponCode.bind(this));
        this.selfOrder.updateProgramsAndRewards();
    },
    async pay() {
        if (!this.discountAsked && this.selfOrder.currentOrder.getPartner()) {
            const discountReward = this.selfOrder.getLoyaltyPrograms("discount", true)
            this.discountAsked = true;
            if (Object.keys(discountReward).length > 0) {
                this.dialog.add(SelectRewardPopup, {
                    getPayload: (reward) => {
                        this.selfOrder.applyRewardFromReward(reward);
                    },
                    rewardType: "discount",
                    claimableOnly: true,
                });
                return;
            }
        }
        await super.pay();
    },
    async applyCouponCode() {
        if (!this.state.couponCode) {
            return;
        }
        this.selfOrder.currentOrder.updateAppliedCouponCodes();
        if (this.selfOrder.currentOrder.uiState.appliedCode.includes(this.state.couponCode)) {
            this.state.couponCode = "";
            this.notification.add(_t("Coupon code has already been applied"), {
                type: "warning",
            });
            return;
        }
        await this.selfOrder.applyCouponCode(this.state.couponCode);
        this.selfOrder.currentOrder.uiState.appliedCode.push(this.state.couponCode);
        this.state.couponCode = "";
    },
    onKeydownCouponInput(ev) {
        if (ev.key.toUpperCase() === "ENTER") {
            this.applyCouponCode.call();
        }
    },
    onClickShowCode() {
        this.state.showCode = !this.state.showCode;
    },
    canChangeQuantity(line, increase) {
        const result = super.canChangeQuantity(...arguments);
        if (line.is_reward_line && increase) {
            if (line.reward_id.reward_type === "discount" || (line.reward_id.reward_type === "product" && line.qty + 1 > line.reward_id.reward_product_qty)) {
                return false;
            }
        }
        return result;
    },
    changeQuantity(line, increase) {
        super.changeQuantity(...arguments);
        this.selfOrder.updateProgramsAndRewards();
    },
    doRemoveLine(line) {
        super.doRemoveLine(...arguments);
        this.selfOrder.updateProgramsAndRewards();
    },
    get lines() {
        const lines = super.lines;
        return lines.filter((line) => !line.is_reward_line || line.reward_id.reward_type != "discount");
    },
    get displayBeforeDiscount() {
        return this.selfOrder.currentOrder.lines.find((line) => line.is_reward_line && line.reward_id.reward_type === "discount");
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
        return program.uiState.pointsDifference > 0 ? 'text-success' : 'text-danger';
    },
});
