/** @odoo-module **/

import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from 'point_of_sale.Registries';
import session from 'web.session';
import { PosLoyaltyCard } from '@pos_loyalty/js/Loyalty';

export const PosLoyaltyPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        //@override
        async validateOrder(isForceValidate) {
            const pointChanges = {};
            const newCodes = [];
            for (const pe of Object.values(this.currentOrder.couponPointChanges)) {
                if (pe.coupon_id > 0) {
                    pointChanges[pe.coupon_id] = pe.points;
                } else if (pe.barcode && !pe.giftCardId) {
                    // New coupon with a specific code, validate that it does not exist
                    newCodes.push(pe.barcode);
                }
            }
            for (const line of this.currentOrder._get_reward_lines()) {
                if (line.coupon_id < 1) {
                    continue;
                }
                if (!pointChanges[line.coupon_id]) {
                    pointChanges[line.coupon_id] = -line.points_cost;
                } else {
                    pointChanges[line.coupon_id] -= line.points_cost;
                }
            }
            if (!await this._isOrderValid(isForceValidate)) {
                return;
            }
            // No need to do an rpc if no existing coupon is being used.
            if (!_.isEmpty(pointChanges) || newCodes.length) {
                try {
                    const {successful, payload} = await this.rpc({
                        model: 'pos.order',
                        method: 'validate_coupon_programs',
                        args: [[], pointChanges, newCodes],
                        kwargs: { context: session.user_context },
                    });
                    // Payload may contain the points of the concerned coupons to be updated in case of error. (So that rewards can be corrected)
                    if (payload && payload.updated_points) {
                        for (const pointChange of Object.entries(payload.updated_points)) {
                            if (this.env.pos.couponCache[pointChange[0]]) {
                                this.env.pos.couponCache[pointChange[0]].balance = pointChange[1];
                            }
                        }
                    }
                    if (payload && payload.removed_coupons) {
                        for (const couponId of payload.removed_coupons) {
                            if (this.env.pos.couponCache[couponId]) {
                                delete this.env.pos.couponCache[couponId];
                            }
                        }
                        this.currentOrder.codeActivatedCoupons = this.currentOrder.codeActivatedCoupons.filter((coupon) => !payload.removed_coupons.includes(coupon.id));
                    }
                    if (!successful) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Error validating rewards'),
                            body: payload.message,
                        });
                        return;
                    }
                } catch (_e) {
                    // Do nothing with error, while this validation step is nice for error messages
                    // it should not be blocking.
                }
            }
            await super.validateOrder(...arguments);
        }

        /**
         * @override
         */
        async _postPushOrderResolve(order, server_ids) {
            // Compile data for our function
            const rewardLines = order._get_reward_lines();
            const partner = order.get_partner();
            let couponData = Object.values(order.couponPointChanges).reduce((agg, pe) => {
                agg[pe.coupon_id] = Object.assign({}, pe, {
                    points: pe.points - order._getPointsCorrection(this.env.pos.program_by_id[pe.program_id]),
                });
                const program = this.env.pos.program_by_id[pe.program_id];
                if (program.is_nominative && partner) {
                    agg[pe.coupon_id].partner_id = partner.id;
                }
                return agg;
            }, {});
            for (const line of rewardLines) {
                const reward = this.env.pos.reward_by_id[line.reward_id];
                if (!couponData[line.coupon_id]) {
                    couponData[line.coupon_id] = {
                        points: 0,
                        program_id: reward.program_id.id,
                        coupon_id: line.coupon_id,
                        barcode: false,
                    }
                }
                if (!couponData[line.coupon_id].line_codes) {
                    couponData[line.coupon_id].line_codes = [];
                }
                if (!couponData[line.coupon_id].line_codes.includes(line.reward_identifier_code)) {
                    !couponData[line.coupon_id].line_codes.push(line.reward_identifier_code);
                }
                couponData[line.coupon_id].points -= line.points_cost;
            }
            // We actually do not care about coupons for 'current' programs that did not claim any reward, they will be lost if not validated
            couponData = Object.fromEntries(Object.entries(couponData).filter(([key, value]) => {
                const program = this.env.pos.program_by_id[value.program_id];
                if (program.applies_on === 'current') {
                    return value.line_codes && value.line_codes.length;
                }
                return true;
            }));
            if (!_.isEmpty(couponData)) {
                const payload = await this.rpc({
                    model: 'pos.order',
                    method: 'confirm_coupon_programs',
                    args: [server_ids, couponData],
                    kwargs: { context: session.user_context },
                });
                if (payload.coupon_updates) {
                    for (const couponUpdate of payload.coupon_updates) {
                        let dbCoupon = this.env.pos.couponCache[couponUpdate.old_id];
                        if (dbCoupon) {
                            dbCoupon.id = couponUpdate.id;
                            dbCoupon.balance = couponUpdate.points;
                            dbCoupon.code = couponUpdate.code;
                        } else {
                            dbCoupon = new PosLoyaltyCard(
                                couponUpdate.code, couponUpdate.id, couponUpdate.program_id, couponUpdate.partner_id, couponUpdate.points);
                        }
                        delete this.env.pos.couponCache[couponUpdate.old_id];
                        this.env.pos.couponCache[couponUpdate.id] = dbCoupon;
                    }
                }
                // Update the usage count since it is checked based on local data
                if (payload.program_updates) {
                    for (const programUpdate of payload.program_updates) {
                        const program = this.env.pos.program_by_id[programUpdate.program_id];
                        if (program) {
                            program.total_order_count = programUpdate.usages;
                        }
                    }
                }
                if (payload.coupon_report) {
                    for (const report_entry of Object.entries(payload.coupon_report)) {
                        this.env.legacyActionManager.do_action(report_entry[0], {
                            additional_context: {
                                active_ids: report_entry[1],
                            }
                        });
                    }
                }
                order.new_coupon_info = payload.new_coupon_info;
            }
            return super._postPushOrderResolve(order, server_ids);
        }
    };

Registries.Component.extend(PaymentScreen, PosLoyaltyPaymentScreen);
