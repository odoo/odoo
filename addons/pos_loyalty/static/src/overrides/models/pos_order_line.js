/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline, {
    extraFields: {
        ...(PosOrderline.extraFields || {}),
        e_wallet_program_id: {
            model: "pos.order.line",
            name: "e_wallet_program_id",
            relation: "loyalty.program",
            type: "many2one",
            local: true,
        },
        gift_barcode: {
            model: "pos.order.line",
            name: "gift_barcode",
            type: "char",
            local: true,
        },
        gift_card_id: {
            model: "pos.order.line",
            name: "gift_card_id",
            relation: "loyalty.card",
            type: "many2one",
            local: true,
        },
        reward_product_id: {
            model: "pos.order.line",
            name: "reward_product_id",
            relation: "product.product",
            type: "many2one",
            local: true,
        },
    },
});

patch(PosOrderline.prototype, {
    serialize() {
        const isNegativeCoupon = this.coupon_id?.id < 0;
        const json = super.serialize(...arguments);
        if (isNegativeCoupon) {
            json.coupon_id = undefined;
        }
        return json;
    },
    setOptions(options) {
        if (options.eWalletGiftCardProgram) {
            this.update({ e_wallet_program_id: options.eWalletGiftCardProgram });
        }
        if (options.giftBarcode) {
            this.update({ gift_barcode: options.giftBarcode });
        }
        if (options.giftCardId) {
            this.update({ gift_card_id: this.models["loyalty.card"].get(options.giftCardId) });
        }
        return super.setOptions(...arguments);
    },
    getEWalletGiftCardProgramType() {
        return this.e_wallet_program_id && this.e_wallet_program_id.program_type;
    },
    ignoreLoyaltyPoints({ program }) {
        return (
            ["gift_card", "ewallet"].includes(program.program_type) &&
            this.e_wallet_program_id?.id !== program.id
        );
    },
    isGiftCardOrEWalletReward() {
        const coupon = this.coupon_id;
        if (!coupon || !this.is_reward_line) {
            return false;
        }
        return ["ewallet", "gift_card"].includes(coupon.program_id?.program_type);
    },
    getGiftCardOrEWalletBalance() {
        const coupon = this.coupon_id;
        return formatCurrency(coupon?.point || 0, this.currency);
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "fst-italic": this.is_reward_line,
        };
    },
});
