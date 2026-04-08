import { Base } from "../related_models";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { logPosMessage } from "../../utils/pretty_console_log";
import { formatCurrency } from "@web/core/currency";

const CONSOLE_COLOR = "#4EFF4D";

export class PosOrderAccounting extends Base {
    static accountingFields = new Set(["pricelist_id", "fiscal_position_id"]);

    setup() {
        super.setup();

        this._prices = {};
        this.triggerRecomputeAllPrices();
    }

    triggerRecomputeAllPrices() {
        if (!this._prices) {
            return;
        }
        this._prices.original = this._constructPriceData();
        this._prices.unit = this._constructPriceData({ baseLineOpts: { quantity: 1 } });
    }

    /**
     * Currency formatted prices, these getters already handle included/excluded tax configuration.
     * They must be used each time a price is displayed to the user.
     */
    get currencyDisplayPrice() {
        return formatCurrency(this.displayPrice, this.currency.id);
    }

    get currencyDisplayPriceIncl() {
        return formatCurrency(this.priceIncl, this.currency.id);
    }

    get currencyDisplayPriceExcl() {
        return formatCurrency(this.priceExcl, this.currency.id);
    }

    get currencyAmountTaxes() {
        return formatCurrency(this.amountTaxes, this.currency.id);
    }

    /**
     * Display price depending on the tax configuration (included or excluded).
     */
    get displayPrice() {
        return this.config.iface_tax_included === "total"
            ? this.currency.round(this.priceIncl)
            : this.currency.round(this.priceExcl);
    }

    /**
     * Remaining due take into account the rounding of the order, the rounding can be configured
     * in two different ways:
     *
     * 1) Rounding applied only on cash payments
     *    In this case the remaining due is rounded only if there is at least one cash payment line.
     *    and the remaining due is less than the rounding tolerance.
     *
     * 2) Rounding applied on all payment methods
     *    In this case the remaining due is always rounded even if a card payment method is used.
     *    The remaining due is rounded if it is less than the rounding tolerance. No payment method
     *    is rounded in this case, the whole order is rounded instead.
     *
     * !!! Keep in mind that from 19.0 only one cash payment line can be used in an order !!!
     */
    get remainingDue() {
        const isNegative = this.totalDue < 0;
        const total = this.totalDue;
        const remaining = total - this.amountPaid;

        // Amount paid covers the total due
        if ((isNegative && remaining >= 0) || (!isNegative && remaining <= 0)) {
            return 0;
        }

        const amount =
            this.orderIsRounded &&
            this.config.rounding_method.asymmetricRound(isNegative ? -remaining : remaining) == 0
                ? 0
                : Math.abs(remaining);
        return isNegative ? this.currency.round(-amount) : this.currency.round(amount);
    }
    get change() {
        const isNegative = this.totalDue < 0;
        const roundingSanatizer = this.orderIsRounded ? this.appliedRounding : 0;
        const remaining = this.totalDue - this.amountPaid;

        // Amount paid covers the total due
        if ((isNegative && remaining <= 0) || (!isNegative && remaining >= 0)) {
            return 0;
        }

        const total =
            Math.abs(this.priceIncl) -
            Math.abs(this.amountPaid) +
            (isNegative ? -roundingSanatizer : roundingSanatizer);

        const amount = isNegative ? -this.currency.round(total) : this.currency.round(total);
        return this.shouldRoundChange
            ? this.config.rounding_method.asymmetricRound(amount)
            : amount;
    }
    get shouldRoundChange() {
        return this.config.cash_rounding;
    }
    get orderIsRounded() {
        const cashPm = this.payment_ids.some((p) => p.payment_method_id.is_cash_count);
        return this.config.hasGlobalRounding || (cashPm && this.config.hasCashRounding);
    }
    get appliedRounding() {
        const total = this.prices.taxDetails.total_amount_no_rounding;
        const isNegative = this.amountPaid > total;
        const remaining = total - this.amountPaid;
        const amount =
            this.orderIsRounded &&
            this.config.rounding_method.asymmetricRound(total < 0 ? -remaining : remaining) == 0
                ? Math.abs(remaining)
                : 0;
        return isNegative ? this.currency.round(amount) : this.currency.round(-amount);
    }

    /**
     * Getters are preferred to methods because they are cached.
     * These getters must be used each time the order prices are needed.
     *
     * Do not try to make your own price computation outside these getters.
     */
    get prices() {
        return this._prices.original;
    }
    get unitPrices() {
        return this._prices.unit;
    }
    get priceIncl() {
        return this.prices.taxDetails.total_amount_no_rounding;
    }
    get priceExcl() {
        return this.prices.taxDetails.base_amount;
    }
    get totalDue() {
        return this.config.hasCashRounding
            ? this.currency.round(this.prices.taxDetails.total_amount_no_rounding)
            : this.currency.round(this.prices.taxDetails.total_amount);
    }
    get amountTaxes() {
        return this.prices.taxDetails.tax_amount_currency;
    }
    get orderHasZeroRemaining() {
        return this.currency.isZero(this.remainingDue);
    }
    get amountPaid() {
        return this.currency.round(
            this.payment_ids.reduce(function (sum, paymentLine) {
                // Return lines are created after the sync, should not be taken into account in
                // the paid amount otherwise, the change would be wrong.
                if (paymentLine.isDone() && !paymentLine.is_change) {
                    sum += paymentLine.getAmount();
                }
                return sum;
            }, 0)
        );
    }
    get orderSign() {
        return this.prices.taxDetails.order_sign;
    }

    /**
     * Determine if the amount to pay should be rounded depending on the payment method
     * and the cash rounding configuration.
     *
     * Rounding on payment methods happen only when cash_rounding is enabled and
     * only_round_cash_method is enabled too. In this case only cash payment methods
     * will have a rounded amount to pay.
     *
     * If only_round_cash_method is disabled, no payment method will have a rounded amount to pay.
     * The whole order is rounded instead.
     */
    shouldRound(paymentMethod) {
        return paymentMethod.is_cash_count && this.config.hasCashRounding;
    }

    /**
     * Get the amount to pay by default when creating a new payment.
     * @param paymentMethod: The payment method of the payment to be created.
     * @returns A monetary value.
     */
    getDefaultAmountDueToPayIn(paymentMethod) {
        const amount = this.shouldRound(paymentMethod)
            ? this.config_id.rounding_method.round(this.remainingDue)
            : this.remainingDue;
        return amount || this.change;
    }

    /**
     * Since prices are computed on the fly, we need to set them before sending
     * the order to the backend.
     *
     * This method is called when the order is pushed to the backend.
     */
    setOrderPrices() {
        this.amount_paid = this.amountPaid; // Already rounded by the getter
        this.amount_tax = this.amountTaxes; // Already rounded by the getter
        this.amount_total = this.currency.round(this.priceIncl);
        this.amount_return = this.change; // Already rounded by the getter
        this.lines.forEach((line) => {
            line.price_subtotal = line.priceExcl;
            line.price_subtotal_incl = line.priceIncl;
        });
    }
    /**
     * This method is used when extra options need to be passed to the price computation.
     * All these options will finally reach these methods:
     * - prepareBaseLineForTaxesComputationExtraValues
     * - prepare_base_line_for_taxes_computation (accounting helpers)
     *
     * For example you can pass a specific set of lines to compute the price of
     * only these lines instead of the whole order.
     */
    getPriceWithOptions(opts = {}) {
        return this._constructPriceData(opts);
    }

    /**
     * @private
     *
     * Private method computing all prices and tax details.
     * DO NOT USE THIS METHOD OUTSIDE THIS FILE !!!
     */
    _constructPriceData(opts = {}) {
        const data = this._computeAllPrices(opts);
        const noDiscount = this._computeAllPrices({ baseLineOpts: { discount: 0.0 }, ...opts });
        const currency = this.currency;

        for (const key of Object.keys(data.baseLineByLineUuids)) {
            const ndData = noDiscount.baseLineByLineUuids[key].tax_details;
            const dData = data.baseLineByLineUuids[key].tax_details;

            Object.assign(data.baseLineByLineUuids[key].tax_details, {
                discount_amount: currency.round(ndData.total_included - dData.total_included),
                no_discount_total_excluded: ndData.total_excluded,
                no_discount_total_included: ndData.total_included,
                no_discount_total_included_currency: ndData.total_included_currency,
                no_discount_total_excluded_currency: ndData.total_excluded_currency,
                no_discount_taxes_data: ndData.taxes_data,
                no_discount_delta_total_excluded: ndData.delta_total_excluded,
                no_discount_delta_total_included: ndData.delta_total_included,
            });
        }

        logPosMessage("Accounting", "_constructPriceData", "Recompute allPrices", CONSOLE_COLOR, [
            data,
        ]);
        return data;
    }

    /**
     * @private
     *
     * Private method computing all prices and tax details.
     * DO NOT USE THIS METHOD OUTSIDE THIS FILE !!!
     */
    _computeAllPrices(opts = {}) {
        const currency = this.currency;
        const lines = opts.lines || this.lines;
        const documentSign = this.isRefund ? -1 : 1;
        const company = this.company;
        const baseLines = lines.map((l) =>
            l.getBaseLine({
                quantity: l.qty,
                price_unit: l.price_unit,
                ...(opts.baseLineOpts || {}),
            })
        );

        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, company);

        // Cash rounding is added only if the document needs to be globaly rounded.
        // See cash_rounding and only_round_cash_method config fields.
        const cashRounding = this.config.cash_rounding ? this.config.rounding_method : null;
        const data = accountTaxHelpers.get_tax_totals_summary(baseLines, currency, company, {
            cash_rounding: cashRounding,
        });
        const total = data.total_amount_currency - (data.cash_rounding_base_amount_currency || 0.0);

        data.order_sign = documentSign;
        data.total_amount_no_rounding = total;

        const baseLineByLineUuids = baseLines.reduce((acc, line) => {
            acc[line.record.uuid] = line;
            return acc;
        }, {});

        return { taxDetails: data, baseLines: baseLines, baseLineByLineUuids: baseLineByLineUuids };
    }
}
