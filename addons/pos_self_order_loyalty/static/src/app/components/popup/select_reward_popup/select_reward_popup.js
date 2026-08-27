import { Component, useProps, t } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { RewardCard } from "@pos_self_order_loyalty/app/components/popup/select_reward_popup/reward_card/reward_card";

export class SelectRewardPopup extends Component {
    static template = "pos_self_order_loyalty.SelectRewardPopup";
    static components = { RewardCard };

    setup() {
        this.props = useProps({
            rewardType: t.string().optional("product"),
            rewards: t.array().optional([]),
            claimableOnly: t.boolean().optional(false),
            title: t.string().optional(_t("Choose your reward")),
            showDivisions: t.boolean().optional(true),
            showIdentificationButton: t.boolean().optional(false),
            getPayload: t.function(),
            close: t.function(),
        });
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.selfOrder = useSelfOrder();
        this.programRewards = {};
        this.promotionRewards = [];
        this.getPotentialRewards();
    }

    get order() {
        return this.selfOrder.currentOrder;
    }

    getPotentialRewards() {
        if (this.props.rewards.length > 0) {
            this.programRewards = this.props.rewards
                .filter((reward) => reward.program_id.program_type === "loyalty")
                .reduce((acc, reward) => {
                    if (!acc[reward.program_id.id]) {
                        acc[reward.program_id.id] = [];
                    }
                    acc[reward.program_id.id].push(reward);
                    return acc;
                }, {});
            this.promotionRewards = this.props.rewards.filter(
                (reward) => reward.program_id.program_type !== "loyalty"
            );
        } else {
            this.programRewards = this.selfOrder.getLoyaltyPrograms(
                this.props.rewardType,
                this.props.claimableOnly
            );
            const promotions = this.selfOrder.getPromotionPrograms(true);
            this.promotionRewards = Object.values(promotions).flat();
            this.promotionRewards = this.promotionRewards.filter(
                (reward) => reward.reward_type === this.props.rewardType
            );
        }

        if (
            this.props.showIdentificationButton &&
            this.selfOrder.currentOrder.getPartner() == null &&
            !this.hasRewards
        ) {
            this.selfOrder.identifyCustomer();
        }
    }

    logout() {
        this.selfOrder.currentOrder.setPartner(false);
        this.dialog.closeAll();
        this.router.navigate("default");
    }

    get hasRewards() {
        return this.promotionRewards.length + Object.keys(this.programRewards).length > 0;
    }

    get programs() {
        const programIds = Object.keys(this.programRewards);
        return programIds.map((id) => this.selfOrder.models["loyalty.program"].get(id));
    }

    getRewards(program) {
        return this.programRewards[program.id];
    }

    getProgramPoints(program) {
        return program.getPoints(this.order);
    }

    confirm(reward) {
        this.props.getPayload(reward);
        this.props.close();
    }
}
