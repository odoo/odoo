odoo.define('pos_coupon.ActivePrograms', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { onChangeOrder } = require('point_of_sale.custom_hooks');

    class ActivePrograms extends PosComponent {
        constructor() {
            super(...arguments);
            onChangeOrder(this._onPrevOrder, this._onNewOrder);
            this.renderParams = {};
        }
        _onPrevOrder(prevOrder) {
            if (prevOrder) {
                prevOrder.off('change', null, this);
                prevOrder.off('rewards-updated', null, this);
            }
        }
        _onNewOrder(newOrder) {
            if (newOrder) {
                newOrder.on('change', this.render, this);
                newOrder.on('rewards-updated', this.render, this);
                newOrder.trigger('update-rewards');
            }
        }
        async render() {
            this._setRenderParams();
            await super.render();
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        /**
         * This is used to set the render parameters before eventually rendering this component.
         */
        _setRenderParams() {
            const order = this.currentOrder;
            const unRewardedArray = order.rewardsContainer ? order.rewardsContainer.getUnawarded() : [];
            const nonGeneratingProgramIds = new Set(unRewardedArray.map(({ program }) => program.id));
            const nonGeneratingCouponIds = new Set(
                unRewardedArray.map(({ coupon_id }) => coupon_id).filter((coupon_id) => coupon_id)
            );
            const onNextOrderPromoPrograms = order.activePromoProgramIds
                .filter((program_id) => {
                    const program = order.pos.coupon_programs_by_id[program_id];
                    return program.promo_applicability === 'on_next_order' && order.programIdsToGenerateCoupons.includes(program_id);
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
            Object.assign(this.renderParams, {
                withRewardsPromoPrograms,
                withRewardsBookedCoupons,
                onNextOrderPromoPrograms,
                show:
                    withRewardsPromoPrograms.length !== 0 ||
                    withRewardsBookedCoupons.length !== 0 ||
                    onNextOrderPromoPrograms.length !== 0,
            });
        }
    }
    ActivePrograms.template = 'ActivePrograms';

    Registries.Component.add(ActivePrograms);

    return ActivePrograms;
});
