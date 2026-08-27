import { Component, useProps, t } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { _t } from "@web/core/l10n/translation";

export class SelectRewardPopup extends Component {
    static template = "pos_self_order_loyalty.SelectRewardPopup";

    setup() {
        this.props = useProps({
            rewardType: t.string().optional("product"),
            rewards: t.array().optional([]),
            claimableOnly: t.boolean().optional(false),
            title: t.string().optional(_t("Choose your reward")),
            showDivisions: t.boolean().optional(true),
            getPayload: t.function(),
            close: t.function(),
        });
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
            this.programRewards = {
                [this.props.rewards[0].program_id.id]: this.props.rewards,
            };
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
