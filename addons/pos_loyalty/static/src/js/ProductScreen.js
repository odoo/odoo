/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useBarcodeReader } from 'point_of_sale.custom_hooks';

export const PosLoyaltyProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        setup() {
            super.setup();
            useBarcodeReader({
                coupon: this._onCouponScan,
            });
        }

        /**
         * If the product is a potential reward, also apply the reward.
         * @override
         */
        async _addProduct(product, options) {
            const order = this.env.pos.get_order();
            const potentialRewards = order.getPotentialFreeProductRewards();
            let rewardsToApply = [];
            for (const reward of potentialRewards) {
                for (const reward_product_id of reward.reward.reward_product_ids) {
                    if (reward_product_id == product.id) {
                        rewardsToApply.push(reward);
                    }
                }
            }
            await super._addProduct(product, options);
            await order._updatePrograms();
            if (rewardsToApply.length == 1) {
                const reward = rewardsToApply[0];
                order._applyReward(reward.reward, reward.coupon_id, { product: product.id });
            }
        }

        _onCouponScan(code) {
            this.currentOrder.activateCode(code.base_code);
        }

        async _updateSelectedOrderline(event) {
            const selectedLine = this.currentOrder.get_selected_orderline();
            if (selectedLine && selectedLine.is_reward_line && !selectedLine.manual_reward &&
                    (event.detail.key === 'Backspace' || event.detail.key === 'Delete')) {
                const reward = this.env.pos.reward_by_id[selectedLine.reward_id];
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Deactivating reward'),
                    body: _.str.sprintf(
                        this.env._t('Are you sure you want to remove %s from this order?\n You will still be able to claim it through the reward button.'),
                        reward.description
                    ),
                    cancelText: this.env._t('No'),
                    confirmText: this.env._t('Yes'),
                });
                if (confirmed) {
                    event.detail.buffer = null;
                } else {
                    // Cancel backspace
                    return;
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
                !selectedLine.is_reward_line ||
                (selectedLine.is_reward_line && ['', 'remove'].includes(val))
            ) {
                super._setValue(val);
            }
            if (!selectedLine) return;
            if (selectedLine.is_reward_line && val === 'remove') {
                this.currentOrder.disabledRewards.add(selectedLine.reward_id);
                const coupon = this.env.pos.couponCache[selectedLine.coupon_id];
                if (coupon && coupon.id > 0 && this.currentOrder.codeActivatedCoupons.find((c) => c.code === coupon.code)) {
                    delete this.env.pos.couponCache[selectedLine.coupon_id];
                    this.currentOrder.codeActivatedCoupons.splice(this.currentOrder.codeActivatedCoupons.findIndex((coupon) => {
                        return coupon.id === selectedLine.coupon_id;
                    }), 1);
                }
            }
            if (!selectedLine.is_reward_line || (selectedLine.is_reward_line && val === 'remove')) {
                selectedLine.order._updateRewards();
            }
        }
    };

Registries.Component.extend(ProductScreen, PosLoyaltyProductScreen);
