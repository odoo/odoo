import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(OrderPaymentValidation.prototype, {
    async validateOrder(isForceValidate) {
        const pointChanges = {};
        const newCodes = [];
        for (const pe of Object.values(this.order.uiState.couponPointChanges)) {
            if (!(pe.barcode && pe.code) && typeof pe.coupon_id === "number") {
                pointChanges[pe.coupon_id] = pe.points;
            } else if ((pe.barcode || pe.code) && typeof pe.coupon_id === "number") {
                // New coupon with a specific code, validate that it does not exist
                newCodes.push(pe.barcode || pe.code);
            }
        }
        for (const line of this.order._get_reward_lines()) {
            if (typeof line.coupon_id.id === "string") {
                continue;
            }
            if (!pointChanges[line.coupon_id.id]) {
                pointChanges[line.coupon_id.id] = -line.points_cost;
            } else {
                pointChanges[line.coupon_id.id] -= line.points_cost;
            }
        }
        if (!(await this.isOrderValid(isForceValidate))) {
            return;
        }
        // No need to do an rpc if no existing coupon is being used.
        if (this.order.state != "paid" && Object.keys(pointChanges || {}).length > 0) {
            try {
                const { successful, payload } = await this.pos.data.call(
                    "pos.order",
                    "validate_coupon_programs",
                    [[], pointChanges, newCodes]
                );
                // Payload may contain the points of the concerned coupons to be updated in case of error. (So that rewards can be corrected)
                if (payload && payload.updated_points) {
                    for (const pointChange of Object.entries(payload.updated_points)) {
                        const coupon = this.pos.models["loyalty.card"].get(pointChange[0]);
                        if (coupon) {
                            coupon.points = pointChange[1];
                        }
                    }
                }
                if (payload && payload.removed_coupons) {
                    const orderLinesToRemove = [];
                    for (const couponId of payload.removed_coupons) {
                        const coupon = this.pos.models["loyalty.card"].get(couponId);
                        coupon && coupon.delete();
                        const relatedRewardLine = this.order.lines.find(
                            (line) => line.coupon_id.id === couponId
                        );
                        if (relatedRewardLine) {
                            orderLinesToRemove.push(relatedRewardLine);
                        }
                    }
                    if (orderLinesToRemove.length > 0) {
                        for (const line of orderLinesToRemove) {
                            this.order.removeOrderline(line);
                        }
                    }
                }
                if (!successful) {
                    this.pos.dialog.add(AlertDialog, {
                        title: _t("Error validating rewards"),
                        body: payload.message,
                    });
                    return;
                }
            } catch {
                // Do nothing with error, while this validation step is nice for error messages
                // it should not be blocking.
            }
        }
        await super.validateOrder(...arguments);
    },
});
