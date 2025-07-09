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
    initState() {
        super.initState();
        this.uiState = {
            ...this.uiState,
            program_type: null,
            gift_code: null,
            e_wallet_id: null,
            gift_card_expiration_date: null,
        };
    },
    setOptions(options) {
        if (options.eWalletGiftCardProgram) {
            this._e_wallet_program_id = options.eWalletGiftCardProgram;
            this.uiState.program_type = options.eWalletGiftCardProgram.program_type;
            this.uiState.e_wallet_id = options.eWalletGiftCardProgram.id;
        }
        if (options.giftBarcode) {
            this._gift_barcode = options.giftBarcode;
        }
        if (options.giftCardId) {
            this._gift_card_id = options.giftCardId;
        }
        return super.setOptions(...arguments);
    },
    getEWalletGiftCardProgramType() {
        return (
            (this._e_wallet_program_id && this._e_wallet_program_id.program_type) ||
            this.uiState.program_type
        );
    },
    ignoreLoyaltyPoints({ program }) {
        return (
            (["gift_card", "ewallet"].includes(program.program_type) &&
                (this._e_wallet_program_id?.id !== program.id ||
                    this.uiState.e_wallet_id !== program.id)) ||
            this.settled_invoice_id ||
            this.settled_order_id
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
    canBeMergedWith(orderline) {
        const res = super.canBeMergedWith(...arguments);
        if (!this._e_wallet_program_id || this.uiState.gift_code === orderline.uiState.gift_code) {
            return res;
        }
        return false;
    },
});
