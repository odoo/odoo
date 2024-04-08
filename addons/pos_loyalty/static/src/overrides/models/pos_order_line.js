import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline, {
    extraFields: {
        ...(PosOrderline.extraFields || {}),
        _e_wallet_program_id: {
            model: "pos.order.line",
            name: "_e_wallet_program_id",
            relation: "loyalty.program",
            type: "many2one",
            local: true,
        },
        gift_code: {
            model: "pos.order.line",
            name: "gift_code",
            type: "char",
            local: true,
        },
        _gift_barcode: {
            model: "pos.order.line",
            name: "_gift_barcode",
            type: "char",
            local: true,
        },
        _gift_card_id: {
            model: "pos.order.line",
            name: "_gift_card_id",
            relation: "loyalty.card",
            type: "many2one",
            local: true,
        },
        _reward_product_id: {
            model: "pos.order.line",
            name: "_reward_product_id",
            relation: "product.product",
            type: "many2one",
            local: true,
        },
    },
});

patch(PosOrderline.prototype, {
    serialize(options = {}) {
        const json = super.serialize(...arguments);
        if (options.orm && json.coupon_id < 0) {
            json.coupon_id = undefined;
        }
        return json;
    },
    setOptions(options) {
        if (options.eWalletGiftCardProgram) {
            this.update({ _e_wallet_program_id: options.eWalletGiftCardProgram });
        }
        if (options.giftBarcode) {
            this.update({ _gift_barcode: options.giftBarcode });
        }
        if (options.giftCardId) {
            this.update({ _gift_card_id: this.models["loyalty.card"].get(options.giftCardId) });
        }
        return super.setOptions(...arguments);
    },
    getEWalletGiftCardProgramType() {
        return this._e_wallet_program_id && this._e_wallet_program_id.program_type;
    },
    ignoreLoyaltyPoints({ program }) {
        return (
            ["gift_card", "ewallet"].includes(program.program_type) &&
            this._e_wallet_program_id?.id !== program.id
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
        return formatCurrency(coupon?.points || 0, this.currency);
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "fst-italic": this.is_reward_line,
        };
    },
});
