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
        async _onClickPay() {
            const order = this.env.pos.get_order();
            const eWalletLine = order.get_orderlines().find(line => line.getEWalletGiftCardProgramType() === 'ewallet');
            if (eWalletLine && !order.get_partner()) {
                const {confirmed} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Customer needed'),
                    body: this.env._t('eWallet requires a customer to be selected'),
                });
                if (confirmed) {
                    const { confirmed, payload: newPartner } = await this.showTempScreen(
                        'PartnerListScreen',
                        { partner: null }
                    );
                    if (confirmed) {
                        order.set_partner(newPartner);
                        order.updatePricelist(newPartner);
                    }
                }
            } else {
                return super._onClickPay(...arguments);
            }
        }
        /**
         * Sets up the options for the gift card product.
         * @param {object} program
         * @param {object} options
         * @returns {Promise<boolean>} whether to proceed with adding the product or not
         */
        async _setupGiftCardOptions(program, options) {
            options.quantity = 1;
            options.merge = false;
            options.eWalletGiftCardProgram = program;

            // If gift card program setting is 'scan_use', ask for the code.
            if (this.env.pos.config.gift_card_settings == 'scan_use') {
                const { confirmed, payload: code } = await this.showPopup('TextInputPopup', {
                    title: this.env._t('Generate a Gift Card'),
                    startingValue: '',
                    placeholder: this.env._t('Enter the gift card code'),
                });
                if (!confirmed) {
                    return false;
                }
                const trimmedCode = code.trim();
                if (trimmedCode && trimmedCode.startsWith('044')) {
                    // check if the code exist in the database
                    // if so, use its balance, otherwise, use the unit price of the gift card product
                    const fetchedGiftCard = await this.rpc({
                        model: 'loyalty.card',
                        method: 'search_read',
                        args: [
                            [['code', '=', trimmedCode], ['program_id', '=', program.id]],
                            ['points', 'source_pos_order_id'],
                        ],
                    });
                    // There should be maximum one gift card for a given code.
                    const giftCard = fetchedGiftCard[0];
                    if (giftCard && giftCard.source_pos_order_id) {
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('This gift card has already been sold'),
                            body: this.env._t('You cannot sell a gift card that has already been sold.'),
                        });
                        return false;
                    }
                    options.giftBarcode = trimmedCode;
                    if (giftCard) {
                        // Use the balance of the gift card as the price of the orderline.
                        // NOTE: No need to convert the points to price because when opening a session,
                        // the gift card programs are made sure to have 1 point = 1 currency unit.
                        options.price = giftCard.points;
                        options.giftCardId = giftCard.id;
                    }
                } else {
                    this.showNotification('Please enter a valid gift card code.');
                    return false;
                }
            }
            return true;
        }
        async setupEWalletOptions(program, options) {
            options.quantity = 1;
            options.merge = false;
            options.eWalletGiftCardProgram = program;
            return true;
        }
        /**
         * If the product is a potential reward, also apply the reward.
         * @override
         */
        async _addProduct(product, options) {
            const linkedProgramIds = this.env.pos.productId2ProgramIds[product.id] || [];
            const linkedPrograms = linkedProgramIds.map(id => this.env.pos.program_by_id[id]);
            let selectedProgram = null;
            if (linkedPrograms.length > 1) {
                const { confirmed, payload: program } = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Select program'),
                    list: linkedPrograms.map((program) => ({
                        id: program.id,
                        item: program,
                        label: program.name,
                    })),
                });
                if (confirmed) {
                    selectedProgram = program;
                } else {
                    // Do nothing here if the selection is cancelled.
                    return;
                }
            } else if (linkedPrograms.length === 1) {
                selectedProgram = linkedPrograms[0];
            }
            if (selectedProgram && selectedProgram.program_type == 'gift_card') {
                const shouldProceed = await this._setupGiftCardOptions(selectedProgram, options);
                if (!shouldProceed) {
                    return;
                }
            } else if (selectedProgram && selectedProgram.program_type == 'ewallet') {
                const shouldProceed = await this.setupEWalletOptions(selectedProgram, options);
                if (!shouldProceed) {
                    return;
                }
            }
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
            // IMPROVEMENT: Ability to understand if the scanned code is to be paid or to be redeemed.
            this.currentOrder.activateCode(code.base_code);
        }

        async _updateSelectedOrderline(event) {
            const selectedLine = this.currentOrder.get_selected_orderline();
            if (event.detail.key === '-') {
                if (selectedLine && selectedLine.eWalletGiftCardProgram) {
                    // Do not allow negative quantity or price in a gift card or ewallet orderline.
                    // Refunding gift card or ewallet is not supported.
                    this.showNotification(this.env._t('You cannot set negative quantity or price to gift card or ewallet.'), 4000);
                    return;
                }
            }
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
