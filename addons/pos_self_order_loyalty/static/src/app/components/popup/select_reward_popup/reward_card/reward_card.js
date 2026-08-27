import { Component, useProps, t } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { _t } from "@web/core/l10n/translation";

export class RewardCard extends Component {
    static template = "pos_self_order_loyalty.RewardCard";
    props = useProps({
        reward: t.object(),
        onClick: t.function(),
        showPoints: t.boolean().optional(true),
    });

    setup() {
        this.selfOrder = useSelfOrder();
    }

    get currentProgramPoints() {
        const order = this.selfOrder.currentOrder;
        return this.props.reward.program_id.getPoints(order) || 0;
    }

    pointToString(points) {
        return `${points} ${this.props.reward.program_id.portal_point_name}`;
    }

    get pointText() {
        const currentPoints = this.currentProgramPoints;
        const pointsToUnlock = this.props.reward.required_points - currentPoints || "";
        return _t(
            "%s • %s more to unlock",
            this.pointToString(currentPoints),
            this.pointToString(pointsToUnlock)
        );
    }

    get isLocked() {
        // Locked if the reward is not accessible by the user
        return !this.selfOrder.currentOrder.availableRewards.some(
            (r) => r.reward.id === this.props.reward.id
        );
    }
}
