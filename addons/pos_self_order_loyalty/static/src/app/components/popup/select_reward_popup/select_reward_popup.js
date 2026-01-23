import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { _t } from "@web/core/l10n/translation";

export class SelectRewardPopup extends Component {
    static template = "pos_self_order_loyalty.SelectRewardPopup";
    static props = {
        rewardType: { type: String, optional: true },
        rewards: { type: Array, optional: true },
        claimableOnly: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        showDivisions: { type: Boolean, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        rewardType: "product",
        rewards: [],
        claimableOnly: false,
        title: _t("Choose your reward"),
        showDivisions: true,
    };

    setup() {
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
            }
        } else {
            this.programRewards = this.selfOrder.getLoyaltyPrograms(this.props.rewardType, this.props.claimableOnly);
            const promotions = this.selfOrder.getPromotionPrograms(true);
            this.promotionRewards = Object.values(promotions).flat();
            this.promotionRewards = this.promotionRewards.filter((reward) => reward.reward_type === this.props.rewardType);
        }   
    }

    get programs() {
        const programIds = Object.keys(this.programRewards);
        return programIds.map(id => this.selfOrder.models["loyalty.program"].get(id));
    }

    getRewards(program) {
        return this.programRewards[program.id];
    }

    getProgramPoints(program) {
        return 
    }

    confirm(reward) {
        this.props.getPayload(reward);
        this.props.close();
    }
}
