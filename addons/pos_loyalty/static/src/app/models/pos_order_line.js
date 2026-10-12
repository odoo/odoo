import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosOrderline.prototype, {
    // gift_card/eWallet program this trigger-product line funds, derived from the
    // `gift_card_vals` blob ({ program_id, code?, expiration_date? }) which syncs to the
    // server. The loyalty.card itself is created server-side when the order is saved.
    // mirror of *models/pos_order_line.py* PosOrderLine._get_loyalty_program
    get payment_program_id() {
        const programId = this.gift_card_vals?.program_id;
        return programId ? this.models["loyalty.program"].get(programId) : undefined;
    },
    /**
     * Get the total price on the order line, taking qty, combos and taxes into account
     * @returns {number}
     */
    get linePriceTaxIncluded() {
        return this.combo_line_ids.length
            ? this.getAllLinesInCombo()
                  .filter((line) => !line.combo_line_ids.length)
                  .reduce((total, lines) => total + lines.priceIncl, 0)
            : this.priceIncl;
    },
    /**
     * Get the total price on the order line, taking into account combos and qty, excluding taxes
     * @returns {number}
     */
    get linePriceTaxExcluded() {
        return this.combo_line_ids.length
            ? this.getAllLinesInCombo()
                  .filter((line) => !line.combo_line_ids.length)
                  .reduce((total, lines) => total + lines.priceExcl, 0)
            : this.priceExcl;
    },
    /**
     * Get the current balance on the payment program balance
     * @returns {number|undefined} returns the balance on the payment program,
     *  or undefined if it's not a payment program line
     */
    getPaymentProgramBalance() {
        const card = this.card_id;
        if (!this.is_reward_line || !card?.program_id?.is_payment_program) {
            return undefined;
        }
        return card.points;
    },
    /**
     * Override the setQuantity method to recompute auto rewards whenever the order changes
     * Additionally, we directly call removeOrderline when the qty on a reward is <= 0, otherwise
     * the reward would be automatically added back on recompute
     */
    setQuantity(quantity, keep_price) {
        if (quantity <= 0 && this.is_reward_line) {
            return this.order_id?.removeOrderline(this);
        }
        if (this.payment_program_id && quantity < 0) {
            return {
                title: _t("Negative quantity not allowed"),
                body: _t("A gift card or eWallet top-up can't have a negative quantity."),
            };
        }
        const order = this.order_id;
        if (order && this.is_reward_line && this.reward_id?.reward_type === "product") {
            const entry = order.active_rewards.find(
                (entry) => entry.reward_id === this.reward_id.id
            );
            if (entry) {
                entry.qty = quantity;
            } else {
                order.active_rewards.push({ reward_id: this.reward_id.id, qty: quantity });
            }
        }
        const result = super.setQuantity(quantity, keep_price);
        order?.recomputeRewards();
        return result;
    },
    /**
     * Override the setUnitPrice method to recompute auto rewards whenever the order changes
     */
    setUnitPrice(price) {
        if (this.payment_program_id && price < 0) {
            price = -price;
        }
        super.setUnitPrice(price);
        this.order_id?.recomputeRewards();
    },
    /**
     * Override setDiscount to recompute rewards: a manual line discount changes the
     * line's discountable price, so order/discount rewards must be recomputed on the
     * new base (otherwise a "% off order" reward keeps discounting the pre-discount price).
     */
    setDiscount(discount) {
        super.setDiscount(discount);
        this.order_id?.recomputeRewards();
    },
    /**
     * A trigger-product line funds its own loyalty card (one card per sold gift card /
     * top-up), so it must never merge with another line.
     */
    canBeMergedWith(orderline) {
        if (this.payment_program_id || orderline.payment_program_id) {
            return false;
        }
        return super.canBeMergedWith(orderline);
    },
    getDisplayClasses() {
        return {
            ...super.getDisplayClasses(),
            "fst-italic": this.is_reward_line,
        };
    },
    /**
     * A gift-card / eWallet reward line is a payment, not goods, so a global discount (from
     * pos_discount / pos_restaurant) must never apply to it. Other reward lines stay
     * discountable, deferring to the base behaviour.
     * @returns {boolean}
     */
    isGlobalDiscountApplicable() {
        const programType = this.card_id?.program_id?.program_type;
        if (this.is_reward_line && ["gift_card", "ewallet"].includes(programType)) {
            return false;
        }
        return super.isGlobalDiscountApplicable?.() ?? true;
    },
    /**
     * A trigger-product line sells a payment instrument (gift card / eWallet top-up), not
     * goods or a service, so a preset's service fee must never be charged on it. Other
     * lines defer to the base behaviour.
     * @returns {boolean}
     */
    isServiceFeeApplicable() {
        if (this.payment_program_id) {
            return false;
        }
        // A discount reward joins the base the fee is carved from only for a
        // percentage of the total after discount, as the global discount line does
        // in pos_discount.
        if (this.is_reward_line && this.reward_id?.reward_type === "discount") {
            const preset = this.order_id?.preset_id;
            return (
                preset?.service_fee_type === "percent" &&
                preset?.service_fee_based_on === "post_discount"
            );
        }
        return super.isServiceFeeApplicable?.() ?? true;
    },
    /**
     * Reward lines display the reward's description as their name (e.g. "Free Product - X").
     */
    get orderDisplayProductName() {
        const result = super.orderDisplayProductName;
        if (this.is_reward_line && this.reward_id) {
            let name;
            if (this.reward_id.reward_type === "product" && this.reward_id.multi_product) {
                name = _t("Free Product - %s", this.product_id.display_name);
            } else if (this.reward_id.reward_type === "discount") {
                name = this.product_id.display_name;
            } else {
                name = this.reward_id.description;
            }
            return { ...result, name };
        }
        return result;
    },
    isRefund() {
        return super.isRefund(...arguments) && !this.is_reward_line;
    },
});
