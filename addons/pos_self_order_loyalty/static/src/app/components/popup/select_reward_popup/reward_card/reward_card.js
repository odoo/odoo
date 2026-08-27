import { Component, useProps, t } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { _t } from "@web/core/l10n/translation";
import { roundPrecision } from "@web/core/utils/numbers";

export class RewardCard extends Component {
    static template = "pos_self_order_loyalty.RewardCard";
    props = useProps({
        reward: t.object(),
        onClick: t.function().optional(() => () => {}),
        showPoints: t.boolean().optional(true),
        claimed: t.boolean().optional(false),
        claimedLabel: t.string().optional(""),
    });

    setup() {
        this.selfOrder = useSelfOrder();
    }

    get currentProgramPoints() {
        const order = this.selfOrder.currentOrder;
        return this.props.reward.program_id.getPoints(order) || 0;
    }

    pointToString(points) {
        points = roundPrecision(points, 0.01);
        return `${points} ${this.props.reward.program_id.portal_point_name}`;
    }

    get pointText() {
        const currentPoints = this.currentProgramPoints;
        const pointsToUnlock = this.props.reward.required_points - currentPoints || 0;
        if (pointsToUnlock <= 0) {
            return this.pointToString(this.props.reward.required_points);
        }
        return _t(
            "%s • %s left to unlock",
            this.pointToString(this.props.reward.required_points),
            this.pointToString(pointsToUnlock)
        );
    }

    get isLocked() {
        // Locked if the reward is not accessible by the user
        if (this.props.claimed) {
            return false;
        }
        return !this.selfOrder.currentOrder.availableRewards.some(
            (r) => r.reward.id === this.props.reward.id
        );
    }
}
