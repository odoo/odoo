odoo.define('pos_coupon.OrderWidget', function (require) {
    'use strict';

    const OrderWidget = require('point_of_sale.OrderWidget');
    const Registries = require('point_of_sale.Registries');

    const PosCouponOrderWidget = (OrderWidget) =>
        class PosCouponOrderWidget extends OrderWidget {
            getActiveProgramsProps() {
                const order = this.env.pos.get_order();
                const unRewardedArray = order.rewardsContainer ? order.rewardsContainer.getUnawarded() : [];
                const nonGeneratingProgramIds = new Set(unRewardedArray.map(({ program }) => program.id));
                const nonGeneratingCouponIds = new Set(
                    unRewardedArray.map(({ coupon_id }) => coupon_id).filter((coupon_id) => coupon_id)
                );
                const onNextOrderPromoPrograms = order.activePromoProgramIds
                    .filter((program_id) => {
                        const program = order.pos.coupon_programs_by_id[program_id];
                        return program.promo_applicability === 'on_next_order' && (order.programIdsToGenerateCoupons || []).includes(program_id);
                    })
                    .map((program_id) => order.pos.coupon_programs_by_id[program_id]);
                const onCurrentOrderPromoProgramIds = order.activePromoProgramIds.filter((program_id) => {
                    const program = order.pos.coupon_programs_by_id[program_id];
                    return program.promo_applicability === 'on_current_order';
                });
                const withRewardsPromoPrograms = onCurrentOrderPromoProgramIds
                    .filter((program_id) => !nonGeneratingProgramIds.has(program_id))
                    .map((program_id) => {
                        const program = order.pos.coupon_programs_by_id[program_id];
                        return {
                            name: program.name,
                            promo_code: program.promo_code,
                        };
                    });
                const withRewardsBookedCoupons = Object.values(order.bookedCouponCodes)
                    .filter((couponCode) => !nonGeneratingCouponIds.has(couponCode.coupon_id))
                    .map((couponCode) => {
                        let program = order.pos.coupon_programs_by_id[couponCode.program_id];
                        return {
                            program_name: program.name,
                            coupon_code: couponCode.code,
                        };
                    });
                return {
                    withRewardsPromoPrograms,
                    withRewardsBookedCoupons,
                    onNextOrderPromoPrograms,
                    show:
                        withRewardsPromoPrograms.length !== 0 ||
                        withRewardsBookedCoupons.length !== 0 ||
                        onNextOrderPromoPrograms.length !== 0,
                };
            }
        };

    Registries.Component.extend(OrderWidget, PosCouponOrderWidget);

    return OrderWidget;
});
