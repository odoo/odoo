/** @odoo-module **/

import AbstractAwaitablePopup from 'point_of_sale.AbstractAwaitablePopup';
import Registries from 'point_of_sale.Registries';
import { useBarcodeReader } from 'point_of_sale.custom_hooks';
import Core from 'web.core';

const _t = Core._t;
const { useState, onPatched, useComponent} = owl;

export class GiftCardPopup extends AbstractAwaitablePopup {
    setup() {
        super.setup();

        this.confirmFunctions = {
            'create_set': this.generateBarcode.bind(this),
            'scan_set': this.scanAndUseGiftCard.bind(this),
            'scan_use': this.scanAndUseGiftCard.bind(this),
            'pay': this.payWithGiftCard.bind(this),
            'balance': this.showRemainingAmount.bind(this),
        };

        this.state = useState({
            giftCardConfig: this.env.pos.config.gift_card_settings,
            showMenu: true,
            error: '',
            context: '',
            amountToSet: 0,
            code: '',
        });

        useBarcodeReader({
            gift_card: this._onScan,
        }, true);

        this.useAutoFocus(this.state);
    }

    //@override
    async confirm() {
        if (!this.state.showMenu) {
            this.clickConfirm();
        }
    }

    clickConfirm() {
        this.confirmFunctions[this.state.context]();
    }

    get code() {
        return this.state.code.trim();
    }

    useAutoFocus(state) {
        const component = useComponent();
        let hasFocused = false;
        function autofocus() {
            if (!state.showMenu) {
                // Should autofocus here but only if it hasn't autofocus yet.
                if (!hasFocused) {
                    const elem = component.el.querySelector(`.gift-card-input-code`);
                    if (elem)
                        elem.focus();
                        hasFocused = true;
                }
            } else {
                // When changing showBarcodeGeneration to false, we reset hasFocused.
                hasFocused = false;
            }
        }
        onPatched(autofocus);
    }

    switchToMenu() {
        this.state.showMenu = true;
        this.state.context = '';
        this.state.amountToSet = 0;
        this.state.code = '';
        this.state.error = '';
    }

    switchToBarcode() {
        this.state.context = this.state.giftCardConfig;
        this.state.showMenu = false;
    }

    switchToPay() {
        this.state.showMenu = false;
        this.state.context = 'pay';
    }

    switchToBalance() {
        this.state.showMenu = false;
        this.state.context = 'balance';
    }

    _onScan(code) {
        this.state.code = code.base_code;
    }

    _getGiftCardProduct() {
        const pos = this.env.pos;
        const program = pos.program_by_id[pos.config.gift_card_program_id[0]];
        return pos.db.product_by_id[[...program.rules[0].valid_product_ids][0]];
    }
    
    addGiftCardProduct() {
        const pos = this.env.pos;
        const order = pos.get_order();
        const product = this._getGiftCardProduct();
        order.add_product(product, {
            price: this.state.amountToSet,
            quantity: 1,
            merge: false,
            giftBarcode: this.code || false,
        });
    }

    async generateBarcode() {
        this.addGiftCardProduct(false);
        this.confirm();
    }

    scanAndUseGiftCard() {
        if (this.state.giftCardConfig === "scan_use") {
            // Use the default price of the first product to match
            this.state.amountToSet = this._getGiftCardProduct().price;
        }
        this.addGiftCardProduct();
        this.confirm();
    }

    async payWithGiftCard()  {
        if (!this.code) {
            this.state.error = _t('No gift card code set');
            return;
        }
        // This should load and enable the coupon and automatic rewards since the gift_card program is supposed to only have one
        //  (as long as there are enough points).
        const res = await this.env.pos.get_order().activateCode(this.code);
        if (res !== true) {
            this.state.error = res;
        }
        this.confirm();
    }

    async showRemainingAmount() {
        this.state.amountToSet = 0;
        if (!this.code) {
            this.state.error = _t('No gift card code set');
            return;
        }
        const coupon = await this.rpc({
            model: 'loyalty.card',
            method: 'search_read',
            args: [
                [['code', '=', this.code], ['program_id', '=', this.env.pos.config.gift_card_program_id[0]]],
                ['points'],
            ],
        });
        if (!coupon || !coupon.length) {
            this.state.error = _t('No gift card found');
        } else {
            this.state.amountToSet = coupon[0].points;
        }
    }
}

GiftCardPopup.template = 'GiftCardPopup';

Registries.Component.add(GiftCardPopup);
