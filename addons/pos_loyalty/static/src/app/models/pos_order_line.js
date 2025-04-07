import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline, {
    extraFields: {
        ...(PosOrderline.extraFields || {}),
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
            programType: null,
            giftCode: null,
            eWalletId: null,
            giftCardExpirationDate: null,
        };
    },
    setOptions(options) {
        if (options.eWalletGiftCardProgram) {
            this.uiState.eWalletId = options.eWalletGiftCardProgram.id;
            this.uiState.programType = options.eWalletGiftCardProgram.program_type;
        }
        return super.setOptions(...arguments);
    },
    getEWalletGiftCardProgramType() {
        return this.uiState.programType;
    },
    ignoreLoyaltyPoints({ program }) {
        return (
            ["gift_card", "ewallet"].includes(program.program_type) &&
            this.uiState.eWalletId !== program.id
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
