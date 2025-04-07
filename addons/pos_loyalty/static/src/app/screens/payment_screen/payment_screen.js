import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { omit } from "@web/core/utils/objects";
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
        this.currentOrder.uiState.couponPointChanges = Object.entries(
            this.currentOrder.uiState.couponPointChanges
        ).reduce((acc, [k, p]) => {
            const newId = this.pos.data.mapUuidToId(p.coupon_id);
            p.coupon_id = newId;
            acc[newId] = p;
            return acc;
        }, {});
        for (const pe of Object.values(this.currentOrder.uiState.couponPointChanges)) {
            if (pe.coupon_id > 0) {
                pointChanges[pe.coupon_id] = pe.points;
            } else if (pe.barcode && !pe.giftCardId) {
                // New coupon with a specific code, validate that it does not exist
                newCodes.push(pe.barcode);
            }
        }
        for (const line of this.currentOrder._get_reward_lines()) {
            let couponId = line.coupon_id.id;
            if (isNaN(Number(line.coupon_id.id))) {
                couponId = this.pos.data.mapUuidToId(line.coupon_id.id);
            }
            if (line.coupon_id.id < 1) {
                continue;
            }
            if (!pointChanges[couponId]) {
                pointChanges[couponId] = -line.points_cost;
            } else {
                pointChanges[couponId] -= line.points_cost;
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
    /**
     * @override
     */
    async _postPushOrderResolve(order, server_ids) {
        if (!["draft", "cancel"].includes(order.state)) {
            await this._postProcessLoyalty(order);
        }
        return super._postPushOrderResolve(order, server_ids);
    },
    async _postProcessLoyalty(order) {
        // Compile data for our function
        const ProgramModel = this.pos.models["loyalty.program"];
        const rewardLines = order._get_reward_lines();
        const partner = order.getPartner();

        let couponData = Object.values(order.uiState.couponPointChanges).reduce((agg, pe) => {
            agg[pe.coupon_id] = Object.assign({}, pe, {
                points: pe.points - order._getPointsCorrection(ProgramModel.get(pe.program_id)),
            });
            const program = ProgramModel.get(pe.program_id);
            if (
                (program.is_nominative || program.program_type == "next_order_coupons") &&
                partner
            ) {
                agg[pe.coupon_id].partner_id = partner.id;
            }
            if (program.program_type != "loyalty") {
                agg[pe.coupon_id].expiration_date = program.date_to || pe.expiration_date;
            }
            return agg;
        }, {});
        for (const line of rewardLines) {
            const reward = line.reward_id;
            let couponId = line.coupon_id.id;
            if (isNaN(Number(line.coupon_id.id))) {
                couponId = this.pos.data.mapUuidToId(line.coupon_id.id);
            }
            if (!couponData[couponId]) {
                couponData[couponId] = {
                    points: 0,
                    program_id: reward.program_id.id,
                    coupon_id: couponId,
                    barcode: false,
                };
                if (reward.program_type != "loyalty") {
                    couponData[couponId].expiration_date = reward.program_id.date_to;
                }
            }
            if (!couponData[couponId].line_codes) {
                couponData[couponId].line_codes = [];
            }
            if (!couponData[couponId].line_codes.includes(line.reward_identifier_code)) {
                !couponData[couponId].line_codes.push(line.reward_identifier_code);
            }
            couponData[couponId].points -= line.points_cost;
        }
        // We actually do not care about coupons for 'current' programs that did not claim any reward, they will be lost if not validated
        couponData = Object.fromEntries(
            Object.entries(couponData)
                .filter(([key, value]) => {
                    const program = ProgramModel.get(value.program_id);
                    if (program.applies_on === "current") {
                        return value.line_codes && value.line_codes.length;
                    }
                    return true;
                })
                .map(([key, value]) => [key, omit(value, "appliedRules")])
        );
        if (Object.keys(couponData || {}).length > 0) {
            const payload = await this.pos.data.call("pos.order", "confirm_coupon_programs", [
                order.id,
                couponData,
            ]);
            // Update the coupons in the pos
            for (const couponId of Object.keys(couponData)) {
                await this.pos.fetchCoupons([["id", "=", Number(couponId)]]);
            }

            const loyaltyPoints = Object.keys(couponData).map((coupon_id) => ({
                order_id: order.id,
                card_id: coupon_id,
                spent: couponData[coupon_id].points < 0 ? -couponData[coupon_id].points : 0,
                won: couponData[coupon_id].points > 0 ? couponData[coupon_id].points : 0,
            }));

            const couponUpdates = payload.coupon_updates.map((item) => ({
                id: item.id,
                old_id: item.old_id,
            }));
            this.pos.data.call("pos.order", "add_loyalty_history_lines", [
                [order.id],
                loyaltyPoints,
                couponUpdates,
            ]);
            // Update the usage count since it is checked based on local data
            if (payload.program_updates) {
                for (const programUpdate of payload.program_updates) {
                    const program = ProgramModel.get(programUpdate.program_id);
                    if (program) {
                        program.total_order_count = programUpdate.usages;
                    }
                }
            }
            if (payload.coupon_report) {
                for (const [actionId, active_ids] of Object.entries(payload.coupon_report)) {
                    await this.report.doAction(actionId, active_ids);
                }
                order.has_pdf_gift_card = Object.keys(payload.coupon_report).length > 0;
            }
            order.new_coupon_info = payload.new_coupon_info;
        }
    },
});
