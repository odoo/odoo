odoo.define('pos_coupon.ActivePrograms', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');

    class ActivePrograms extends PosComponent {
        getRenderParams() {
            const order = this.props.activeOrder;
            const rewardsContainer = this.env.model.getRewardsContainer(order.id);
            const unRewardedArray = rewardsContainer ? rewardsContainer.getUnawarded() : [];
            const nonGeneratingProgramIds = new Set(unRewardedArray.map(({ program }) => program.id));
            const nonGeneratingCouponIds = new Set(
                unRewardedArray.map(({ coupon_id }) => coupon_id).filter((coupon_id) => coupon_id)
            );
            const onNextOrderPromoPrograms = order._extras.activePromoProgramIds
                .filter((program_id) => {
                    const program = this.env.model.getRecord('coupon.program', program_id);
                    return (
                        program.promo_applicability === 'on_next_order' &&
                        order._extras.programIdsToGenerateCoupons.includes(program_id)
                    );
                })
                .map((program_id) => this.env.model.getRecord('coupon.program', program_id));
            const onCurrentOrderPromoProgramIds = order._extras.activePromoProgramIds.filter((program_id) => {
                const program = this.env.model.getRecord('coupon.program', program_id);
                return program.promo_applicability === 'on_current_order';
            });
            const withRewardsPromoPrograms = onCurrentOrderPromoProgramIds
                .filter((program_id) => !nonGeneratingProgramIds.has(program_id))
                .map((program_id) => {
                    const program = this.env.model.getRecord('coupon.program', program_id);
                    return {
                        name: program.name,
                        promo_code: program.promo_code,
                    };
                });
            const withRewardsBookedCoupons = Object.values(order._extras.bookedCouponCodes)
                .filter((couponCode) => !nonGeneratingCouponIds.has(couponCode.coupon_id))
                .map((couponCode) => {
                    const program = this.env.model.getRecord('coupon.program', couponCode.program_id);
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
    }
    ActivePrograms.template = 'pos_coupon.ActivePrograms';

    return ActivePrograms;
});
