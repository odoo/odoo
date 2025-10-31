import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.report = useService("report");
    },
    //@override
    async validateOrder(isForceValidate) {
        const pointChanges = {};
        const newCodes = [];
        for (const pe of Object.values(this.currentOrder.uiState.couponPointChanges)) {
            if (pe.coupon_id > 0) {
                pointChanges[pe.coupon_id] = pe.points;
            } else if (pe.barcode && !pe.giftCardId) {
                // New coupon with a specific code, validate that it does not exist
                newCodes.push(pe.barcode);
            }
        }
        for (const line of this.currentOrder._get_reward_lines()) {
            if (line.coupon_id.id < 1) {
                continue;
            }
            if (!pointChanges[line.coupon_id.id]) {
                pointChanges[line.coupon_id.id] = -line.points_cost;
            } else {
                pointChanges[line.coupon_id.id] -= line.points_cost;
            }
        }
        if (!(await this._isOrderValid(isForceValidate))) {
            return;
        }
        // No need to do an rpc if no existing coupon is being used.
        if (Object.keys(pointChanges || {}).length > 0 || newCodes.length) {
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
                    for (const couponId of payload.removed_coupons) {
                        const coupon = this.pos.models["loyalty.card"].get(couponId);
                        coupon && coupon.delete();
                    }
                }
                if (!successful) {
                    this.dialog.add(AlertDialog, {
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
