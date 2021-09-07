odoo.define('pos_coupon.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    const PosCouponProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
                useBarcodeReader({
                    coupon: this._onCouponScan,
                });
            }
            _onCouponScan(code) {
                this.currentOrder.activateCode(code.base_code);
            }
            async _updateSelectedOrderline(event) {
                const selectedLine = this.currentOrder.get_selected_orderline();
                if (selectedLine && selectedLine.is_program_reward && event.detail.key === 'Backspace') {
                    const program = this.env.pos.coupon_programs_by_id[selectedLine.program_id]
                    const { confirmed } = await this.showPopup('ConfirmPopup', {
                        title: this.env._t('Deactivating program'),
                        body: _.str.sprintf(
                            this.env._t('Are you sure you want to deactivate %s in this order?'),
                            program.name
                        ),
                        cancelText: this.env._t('No'),
                        confirmText: this.env._t('Yes'),
                    });
                    if (confirmed) {
                        event.detail.buffer = null;
                    } else {
                        return; // do nothing on the line
                    }
                }
                return super._updateSelectedOrderline(...arguments);
            }
            /**
             * 1/ Perform the usual set value operation (super._setValue) if the line being modified
             * is not a reward line or if it is a reward line, the `val` being set is '' or 'remove' only.
             *
             * 2/ Update activated programs and coupons when removing a reward line.
             *
             * 3/ Trigger 'update-rewards' if the line being modified is a regular line or
             * if removing a reward line.
             *
             * @override
             */
            _setValue(val) {
                const selectedLine = this.currentOrder.get_selected_orderline();
                if (
                    !selectedLine ||
                    !selectedLine.is_program_reward ||
                    (selectedLine.is_program_reward && ['', 'remove'].includes(val))
                ) {
                    super._setValue(val);
                }
                if (!selectedLine) return;
                if (selectedLine.is_program_reward && val === 'remove') {
                    if (selectedLine.coupon_id) {
                        const coupon_code = Object.values(selectedLine.order.bookedCouponCodes).find(
                            (couponCode) => couponCode.coupon_id === selectedLine.coupon_id
                        ).code;
                        delete selectedLine.order.bookedCouponCodes[coupon_code];
                        selectedLine.order.trigger('reset-coupons', [selectedLine.coupon_id]);
                        this.showNotification(`Coupon (${coupon_code}) has been deactivated.`);
                    } else if (selectedLine.program_id) {
                        // remove program from active programs
                        const index = selectedLine.order.activePromoProgramIds.indexOf(selectedLine.program_id);
                        selectedLine.order.activePromoProgramIds.splice(index, 1);
                        this.showNotification(
                            `'${
                                this.env.pos.coupon_programs_by_id[selectedLine.program_id].name
                            }' program has been deactivated.`
                        );
                    }
                }
                if (!selectedLine.is_program_reward || (selectedLine.is_program_reward && val === 'remove')) {
                    selectedLine.order.trigger('update-rewards');
                }
            }
        };

    Registries.Component.extend(ProductScreen, PosCouponProductScreen);

    return ProductScreen;
});
