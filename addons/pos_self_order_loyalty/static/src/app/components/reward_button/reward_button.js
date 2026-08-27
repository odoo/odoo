import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SelectRewardPopup } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/select_reward_popup";

export class RewardButton extends Component {
    static template = "pos_self_order_loyalty.RewardButton";

    setup() {
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.selfOrder = useSelfOrder();
    }

    async clickRewardButton() {
        if (!this.selfOrder.currentOrder.getPartner()) {
            // Open non-identification linked rewards
            if (this.availableRewardsLength > 0) {
                this.dialog.add(SelectRewardPopup, {
                    getPayload: (reward) => {
                        this.selfOrder.applyReward(reward);
                    },
                    rewardType: "product",
                    showIdentificationButton: !this.selfOrder.currentOrder.getPartner(),
                    claimableOnly: true,
                });
                return;
            }
        }
        // Open reward popup
        this.dialog.add(SelectRewardPopup, {
            getPayload: (reward) => {
                this.selfOrder.applyReward(reward);
            },
            rewardType: "product",
        });
    }

    get showAvatarOnly() {
        // In mobile mode, the button is always compact whatever the screen size
        return this.ui.isSmall || !this.selfOrder.kioskMode;
    }

    get partnerInitial() {
        const name = this.selfOrder.currentOrder.getPartner()?.name?.trim();
        return name ? name[0].toUpperCase() : "?";
    }

    get loggedInLabel() {
        return _t("Logged in as %s", this.selfOrder.currentOrder.getPartner()?.name || "");
    }

    getPartnerLoyaltyPoints() {
        const cards = this.selfOrder.getLoyaltyCards();
        if (cards.length > 0) {
            return cards[0].program_id.getDisplayPoints(this.selfOrder.currentOrder);
        }
        return false;
    }

    get availableRewardsLength() {
        return this.getRewardsLength(false);
    }

    get claimableRewardsLength() {
        return this.getRewardsLength(true);
    }

    getRewardsLength(claimable = false) {
        const programRewards = this.selfOrder.getLoyaltyPrograms("product", claimable);
        const promotions = this.selfOrder.getPromotionPrograms(claimable);
        return Object.keys(programRewards).length + Object.keys(promotions).length;
    }

    get isDisabled() {
        return this.selfOrder.currentOrder.getPartner() && this.availableRewardsLength === 0;
    }

    get hasRewards() {
        return this.selfOrder.currentOrder.getPartner() && this.claimableRewardsLength > 0;
    }
}
