import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";
import { computeComboItems } from "./utils/compute_combo_items";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { localization } from "@web/core/l10n/localization";
import { formatDate } from "@web/core/l10n/dates";
import { getStrNotes } from "./utils/order_change";

const { DateTime } = luxon;

export class PosOrder extends Base {
    static pythonModel = "pos.order";

    setup(vals) {
        super.setup(vals);

        if (!this.session_id?.id && (!this.finalized || typeof this.id !== "number")) {
            this.session_id = this.session;

            if (this.state === "draft" && this.lines.length == 0 && this.payment_ids.length == 0) {
                this._isResidual = true;
            }
        }

        // Data present in python model
        this.name = vals.name || "/";
        this.nb_print = vals.nb_print || 0;
        this.to_invoice = vals.to_invoice || false;
        this.setShippingDate(vals.shipping_date);
        this.state = vals.state || "draft";

        this.general_customer_note = vals.general_customer_note || "";
        this.internal_note = vals.internal_note || "";

        if (!this.date_order) {
            this.date_order = DateTime.now();
        }
        if (!this.user_id && this.models["res.users"]) {
            this.user_id = this.user;
        }
    }

    initState() {
        super.initState();
        // !!Keep all uiState in one object!!
        this.uiState = {
            unmerge: {},
            lineToRefund: {},
            displayed: this.state !== "cancel",
            booked: false,
            screen_data: {},
            selected_orderline_uuid: undefined,
            selected_paymentline_uuid: undefined,
            // Pos restaurant specific to most proper way is to override this
            TipScreen: {
                inputTipAmount: "",
            },
            requiredPartnerDetails: {},
            last_general_customer_note: this.general_customer_note || "",
            last_internal_note: this.internal_note || "",
            printStack: {},
        };
    }

    get user() {
        return this.models["res.users"].getFirst();
    }

    get company() {
        return this.config.company_id;
    }

    get config() {
        return this.models["pos.config"].getFirst();
    }

    get currency() {
        return this.config.currency_id;
    }

    get pickingType() {
        return this.models["stock.picking.type"].getFirst();
    }

    get session() {
        return this.models["pos.session"].getFirst();
    }

    get finalized() {
        return this.state !== "draft";
    }

    get totalQuantity() {
        return this.lines.reduce((sum, line) => sum + line.getQuantity(), 0);
    }

    get isUnsyncedPaid() {
        return this.finalized && typeof this.id === "string";
    }

    get originalSplittedOrder() {
        return this.models["pos.order"].getBy("uuid", this.uiState.splittedOrderUuid);
    }

    get presetDate() {
        return this.preset_time?.toFormat(localization.dateFormat) || "";
    }

    get isFutureDate() {
        return this.preset_time?.startOf("day") > DateTime.now().startOf("day");
    }

    get presetTime() {
        return this.preset_time && this.preset_time.isValid
            ? this.preset_time.toFormat("HH:mm")
            : false;
    }

    get invoiceName() {
        return this.account_move?.name || "";
    }

    get presetDateTime() {
        return this.preset_time?.isValid
            ? this.preset_time.hasSame(this.date_order, "day")
                ? this.preset_time.toFormat(localization.timeFormat)
                : this.preset_time.toFormat(`${localization.dateFormat} ${localization.timeFormat}`)
            : false;
    }

    get isCustomerRequired() {
        if (this.partner_id) {
            return false;
        }
        const splitPayment = this.payment_ids.some(
            (payment) => payment.payment_method_id.split_transactions
        );
        const invalidPartnerPreset =
            (this.preset_id?.needsName && !this.floating_order_name) ||
            this.preset_id?.needsPartner;
        return invalidPartnerPreset || this.isToInvoice() || Boolean(splitPayment);
    }

    get presetRequirementsFilled() {
        const invalidCustomer =
            (this.preset_id?.needsName && !(this.floating_order_name || this.partner_id)) ||
            (this.preset_id?.needsPartner && !this.partner_id);
        const isAddressMissing =
            this.preset_id?.needsPartner && !(this.partner_id?.street || this.partner_id?.street2);
        const invalidSlot = this.preset_id?.needsSlot && !this.preset_time;

        if (invalidCustomer || isAddressMissing || invalidSlot) {
            this.uiState.requiredPartnerDetails = {
                field: _t(
                    invalidCustomer ? _t("Customer") : isAddressMissing ? _t("Address") : _t("Slot")
                ),
                message: invalidCustomer
                    ? _t("Please add a valid customer to the order.")
                    : isAddressMissing
                    ? _t("The selected customer needs an address.")
                    : _t("Please select a time slot before proceeding."),
            };
            return false;
        }
        return true;
    }

    get isRefund() {
        return this.is_refund === true;
    }

    setPreset(preset) {
        this.setPricelist(preset.pricelist_id || this.config.pricelist_id);
        this.fiscal_position_id =
            preset.fiscal_position_id || this.config.default_fiscal_position_id;
        this.preset_id = preset;
        if (preset.is_return) {
            this.lines.forEach((l) => l.setQuantity(-Math.abs(l.getQuantity())));
        }
    }

    /**
     * Get the details total amounts with and without taxes, the details of taxes per subtotal and per tax group.
     * @returns See '_get_tax_totals_summary' in account_tax.py for the full details.
     */
    get taxTotals() {
        return this.getTaxTotalsOfLines(this.lines);
    }

    getTaxTotalsOfLines(lines) {
        const currency = this.currency;
        const company = this.company;

        // If each line is negative, we assume it's a refund order.
        // It's a normal order if it doesn't contain a line (useful for pos_settle_due).
        // TODO: Properly differentiate refund orders from normal ones.
        const documentSign = this.isRefund ? -1 : 1;
        const baseLines = lines.map((line) =>
            accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues({
                    quantity: documentSign * line.qty,
                })
            )
        );
        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, company);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, company);

        // For the generic 'get_tax_totals_summary', we only support the cash rounding that round the whole document.
        const cashRounding =
            !this.config.only_round_cash_method && this.config.cash_rounding
                ? this.config.rounding_method
                : null;

        const taxTotals = accountTaxHelpers.get_tax_totals_summary(baseLines, currency, company, {
            cash_rounding: cashRounding,
        });

        taxTotals.order_sign = documentSign;
        taxTotals.order_total =
            taxTotals.total_amount_currency - (taxTotals.cash_rounding_base_amount_currency || 0.0);

        let order_rounding = 0;
        let remaining = taxTotals.order_total;
        const validPayments = this.payment_ids.filter((p) => p.isDone() && !p.is_change);
        for (const [payment, isLast] of validPayments.map((p, i) => [
            p,
            i === validPayments.length - 1,
        ])) {
            const paymentAmount = documentSign * payment.getAmount();
            if (isLast) {
                if (this.config.cash_rounding) {
                    const roundedRemaining = this.getRoundedRemaining(
                        this.config.rounding_method,
                        remaining
                    );
                    if (!this.currency.isZero(paymentAmount - remaining)) {
                        order_rounding = roundedRemaining - remaining;
                    }
                }
            }
            remaining -= paymentAmount;
        }

        taxTotals.order_rounding = order_rounding;
        taxTotals.order_remaining = remaining;

        return taxTotals;
    }

    shouldRound(paymentMethod) {
        return (
            this.config.cash_rounding &&
            (!this.config.only_round_cash_method || paymentMethod.is_cash_count)
        );
    }

    get orderHasZeroRemaining() {
        const { order_remaining, order_rounding } = this.taxTotals;
        const remaining_with_rounding = order_remaining + order_rounding;
        return this.currency.isZero(remaining_with_rounding);
    }

    /**
     * Get the amount to pay by default when creating a new payment.
     * @param paymentMethod: The payment method of the payment to be created.
     * @returns A monetary value.
     */
    getDefaultAmountDueToPayIn(paymentMethod) {
        const { order_remaining, order_sign } = this.taxTotals;
        const amount = this.shouldRound(paymentMethod)
            ? this.getRoundedRemaining(this.config.rounding_method, order_remaining)
            : order_remaining;
        return order_sign * amount;
    }

    getRoundedRemaining(roundingMethod, remaining) {
        remaining = roundCurrency(remaining, this.currency);
        if (this.currency.isZero(remaining)) {
            return 0;
        } else if (this.currency.isNegative(remaining)) {
            return roundingMethod.asymmetricRound(remaining);
        } else {
            return roundingMethod.round(remaining);
        }
    }

    getCashierName() {
        return this.user_id?.name?.split(" ").at(0);
    }
    canPay() {
        return this.lines.length;
    }
    recomputeOrderData() {
        this.amount_paid = this.getTotalPaid();
        this.amount_tax = this.getTotalTax();
        this.amount_total = this.getTotalWithTax();
        this.amount_return = this.getChange();
        this.lines.forEach((line) => {
            line.setLinePrice();
        });
    }

    get isBooked() {
        return Boolean(this.uiState.booked || !this.isEmpty() || typeof this.id === "number");
    }

    get hasChange() {
        return this.lines.some((l) => l.uiState.hasChange);
    }

    get preparationChanges() {
        return this.getChanges();
    }

    isEmpty() {
        return this.lines.length === 0;
    }

    updateSavedQuantity() {
        this.lines.forEach((line) => line.updateSavedQuantity());
    }

    assertEditable() {
        if (this.finalized) {
            throw new Error("Finalized Order cannot be modified");
        }
        return true;
    }

    getOrderline(id) {
        const orderlines = this.lines;
        for (let i = 0; i < orderlines.length; i++) {
            if (orderlines[i].id === id) {
                return orderlines[i];
            }
        }
        return null;
    }

    getLastOrderline() {
        const orderlines = this.lines;
        return this.lines.at(orderlines.length - 1);
    }

    getTip() {
        const tip_product = this.config.tip_product_id;
        const lines = this.lines;
        if (!tip_product) {
            return 0;
        } else {
            for (const line of lines) {
                if (line.getProduct() === tip_product) {
                    return line.getUnitPrice();
                }
            }
            return 0;
        }
    }

    setPricelist(pricelist) {
        this.pricelist_id = pricelist ? pricelist : false;

        const lines_to_recompute = this.getLinesToCompute();

        for (const line of lines_to_recompute) {
            if (line.isLotTracked()) {
                const related_lines = [];
                const price = line.product_id.product_tmpl_id.getPrice(
                    pricelist,
                    line.getQuantity(),
                    line.getPriceExtra(),
                    false,
                    line.product_id,
                    line,
                    related_lines
                );
                related_lines.forEach((line) => line.setUnitPrice(price));
            } else {
                const newPrice = line.product_id.product_tmpl_id.getPrice(
                    pricelist,
                    line.getQuantity(),
                    line.getPriceExtra(),
                    false,
                    line.product_id
                );
                line.setUnitPrice(newPrice);
            }
        }

        const attributes_prices = {};
        const combo_parent_lines = this.lines.filter(
            (line) => line.price_type === "original" && line.combo_line_ids?.length
        );
        for (const pLine of combo_parent_lines) {
            attributes_prices[pLine.id] = computeComboItems(
                pLine.product_id,
                pLine.combo_line_ids.map((cLine) => {
                    if (cLine.attribute_value_ids) {
                        return {
                            combo_item_id: cLine.combo_item_id,
                            configuration: {
                                attribute_value_ids: cLine.attribute_value_ids,
                            },
                            qty: pLine.qty,
                        };
                    } else {
                        return { combo_item_id: cLine.combo_item_id, qty: pLine.qty };
                    }
                }),
                pricelist,
                this.models["decimal.precision"].getAll(),
                this.models["product.template.attribute.value"].getAllBy("id"),
                [],
                this.config_id.currency_id
            );
        }
        const combo_children_lines = this.lines.filter(
            (line) => line.price_type === "automatic" && line.combo_parent_id
        );
        combo_children_lines.forEach((line) => {
            line.setUnitPrice(
                attributes_prices[line.combo_parent_id.id].find(
                    (item) => item.combo_item_id.id === line.combo_item_id.id
                ).price_unit
            );
        });
    }

    /**
     * A wrapper around line.delete() that may potentially remove multiple orderlines.
     * In core pos, it removes the linked combo lines. In other modules, it may remove
     * other related lines, e.g. multiple reward lines in pos_loyalty module.
     * @param {Orderline} line
     * @returns {boolean} true if the line was removed, false otherwise
     */
    removeOrderline(line) {
        const linesToRemove = line.getAllLinesInCombo();
        for (const lineToRemove of linesToRemove) {
            if (lineToRemove.refunded_orderline_id?.uuid in this.uiState.lineToRefund) {
                delete this.uiState.lineToRefund[lineToRemove.refunded_orderline_id.uuid];
            }

            if (this.assertEditable()) {
                lineToRemove.delete();
            }
        }
        if (!this.lines.length) {
            this.general_customer_note = ""; // reset general note on empty order
        }
        this.selectOrderline(this.getLastOrderline());
        return true;
    }

    isSaleDisallowed(values, options) {
        return this.isRefund && (!values.qty || values.qty > 0);
    }

    getSelectedOrderline() {
        return this.lines.find((line) => line.uuid === this.uiState.selected_orderline_uuid);
    }

    getSelectedPaymentline() {
        return this.payment_ids.find(
            (line) => line.uuid === this.uiState.selected_paymentline_uuid
        );
    }

    selectOrderline(line) {
        if (line) {
            this.uiState.selected_orderline_uuid = line.uuid;
        } else {
            this.uiState.selected_orderline_uuid = undefined;
        }
    }

    deselectOrderline() {
        if (this.uiState.selected_orderline_uuid) {
            this.uiState.selected_orderline_uuid = undefined;
        }
    }

    /* ---- Payment Lines --- */
    addPaymentline(payment_method) {
        this.assertEditable();
        if (this.electronicPaymentInProgress()) {
            return false;
        } else {
            const totalAmountDue = this.getDefaultAmountDueToPayIn(payment_method);
            const newPaymentLine = this.models["pos.payment"].create({
                pos_order_id: this,
                payment_method_id: payment_method,
            });
            this.selectPaymentline(newPaymentLine);
            newPaymentLine.setAmount(totalAmountDue);

            if (
                (payment_method.payment_terminal && !this.isRefund) ||
                payment_method.payment_method_type === "qr_code"
            ) {
                newPaymentLine.setPaymentStatus("pending");
            }
            return newPaymentLine;
        }
    }

    getPaymentlineByUuid(uuid) {
        var lines = this.payment_ids;
        return lines.find(function (line) {
            return line.uuid === uuid;
        });
    }

    removePaymentline(line) {
        this.assertEditable();

        if (this.getSelectedPaymentline() === line) {
            this.selectPaymentline(undefined);
        }

        line.delete({ backend: true });
    }

    selectPaymentline(line) {
        if (line) {
            this.uiState.selected_paymentline_uuid = line?.uuid;
        } else {
            this.uiState.selected_paymentline_uuid = undefined;
        }
    }

    electronicPaymentInProgress() {
        return this.payment_ids.some(function (pl) {
            if (pl.payment_status) {
                return !["done", "reversed"].includes(pl.payment_status);
            } else {
                return false;
            }
        });
    }

    getTotalWithTax() {
        return this.taxTotals.order_sign * this.taxTotals.order_total;
    }

    getTotalWithTaxOfLines(lines) {
        const taxTotals = this.getTaxTotalsOfLines(lines);
        return taxTotals.order_sign * taxTotals.total_amount_currency;
    }

    getTotalWithoutTax() {
        const base_amount =
            this.taxTotals.base_amount_currency +
            (this.taxTotals.cash_rounding_base_amount_currency || 0.0);
        return this.taxTotals.order_sign * base_amount;
    }

    getTotalWithoutTaxOfLines(lines) {
        const taxTotals = this.getTaxTotalsOfLines(lines);
        return taxTotals.order_sign * taxTotals.base_amount_currency;
    }

    _getIgnoredProductIdsTotalDiscount() {
        return [];
    }

    getTotalDiscount() {
        const ignored_product_ids = this._getIgnoredProductIdsTotalDiscount();
        return this.currency.round(
            this.lines.reduce((sum, orderLine) => {
                if (!ignored_product_ids.includes(orderLine.product_id.id)) {
                    sum +=
                        orderLine.getAllPrices().priceWithTaxBeforeDiscount -
                        orderLine.getAllPrices().priceWithTax;
                    if (
                        orderLine.displayDiscountPolicy() === "without_discount" &&
                        !(orderLine.price_type === "manual") &&
                        orderLine.discount == 0
                    ) {
                        sum +=
                            (orderLine.getTaxedlstUnitPrice() -
                                orderLine.getUnitDisplayPriceBeforeDiscount()) *
                            orderLine.getQuantity();
                    }
                }
                return sum;
            }, 0)
        );
    }

    getTotalTax() {
        return this.taxTotals.order_sign * this.taxTotals.tax_amount_currency;
    }

    getTotalPaid() {
        return this.currency.round(
            this.payment_ids.reduce(function (sum, paymentLine) {
                if (paymentLine.isDone()) {
                    sum += paymentLine.getAmount();
                }
                return sum;
            }, 0)
        );
    }

    getTotalDue() {
        return this.taxTotals.order_sign * this.taxTotals.order_total;
    }

    getTaxDetails() {
        return this.getTaxDetailsOfLines(this.lines);
    }

    getTaxDetailsOfLines(lines) {
        const taxDetails = {};
        for (const line of lines) {
            for (const taxData of line.allPrices.taxesData) {
                const taxId = taxData.tax.id;
                if (!taxDetails[taxId]) {
                    taxDetails[taxId] = Object.assign({}, taxData, {
                        amount: 0.0,
                        base: 0.0,
                        tax_percentage: taxData.tax.amount,
                    });
                }
                taxDetails[taxId].base += taxData.base_amount_currency;
                taxDetails[taxId].amount += taxData.tax_amount_currency;
            }
        }
        return Object.values(taxDetails);
    }

    // TODO: deprecated. Remove it and fix l10n_de_pos_cert accordingly.
    getTotalForTaxes(tax_id) {
        let total = 0;

        if (!(tax_id instanceof Array)) {
            tax_id = [tax_id];
        }

        const tax_set = {};

        for (var i = 0; i < tax_id.length; i++) {
            tax_set[tax_id[i]] = true;
        }

        this.lines.forEach((line) => {
            var taxes_ids = this.tax_ids || line.getProduct().taxes_id;
            for (var i = 0; i < taxes_ids.length; i++) {
                if (tax_set[taxes_ids[i]]) {
                    total += line.getPriceWithTax();
                    return;
                }
            }
        });

        return total;
    }

    /**
     * Checks whether to show "Remaining" or "Change" in the payment status.
     * If the remaining amount is compensated by the rounding, then we show "Remaining".
     */
    hasRemainingAmount() {
        const { order_remaining } = this.taxTotals;
        return this.orderHasZeroRemaining || !this.currency.isNegative(order_remaining);
    }

    getChange() {
        let { order_sign, order_remaining: remaining } = this.taxTotals;
        if (this.config.cash_rounding) {
            remaining = this.getRoundedRemaining(this.config.rounding_method, remaining);
        }
        return -order_sign * remaining;
    }

    getDue() {
        return this.taxTotals.order_sign * this.currency.round(this.taxTotals.order_remaining);
    }

    getRoundingApplied() {
        return this.taxTotals.order_sign * (this.taxTotals.order_rounding || 0.0);
    }

    isPaid() {
        const { order_remaining } = this.taxTotals;
        return this.orderHasZeroRemaining || this.currency.isNegative(order_remaining);
    }

    isRefundInProcess() {
        return (
            this.isRefund &&
            this.payment_ids.some(
                (pl) => pl.payment_method_id.use_payment_terminal && pl.payment_status !== "done"
            )
        );
    }

    isPaidWithCash() {
        return !!this.payment_ids.find(function (pl) {
            return pl.payment_method_id.is_cash_count;
        });
    }

    getTotalCost() {
        return this.lines.reduce(function (sum, orderLine) {
            return sum + orderLine.getTotalCost();
        }, 0);
    }

    /* ---- Invoice --- */
    setToInvoice(to_invoice) {
        this.assertEditable();
        this.to_invoice = to_invoice;
    }

    isToInvoice() {
        return this.to_invoice;
    }

    /* ---- Partner --- */
    // the partner related to the current order.
    setPartner(partner) {
        this.assertEditable();
        this.partner_id = partner;
        this.updatePricelistAndFiscalPosition(partner);
        if (partner.is_company) {
            this.setToInvoice(true);
        }
    }

    getPartner() {
        return this.partner_id;
    }

    getPartnerName() {
        return this.partner_id ? this.partner_id.name : "";
    }

    getCardHolderName() {
        const card_payment_line = this.payment_ids.find((pl) => pl.cardholder_name);
        return card_payment_line ? card_payment_line.cardholder_name : "";
    }

    /* ---- Screen Status --- */
    // the order also stores the screen status, as the PoS supports
    // different active screens per order. This method is used to
    // store the screen status.
    setScreenData(value) {
        this.uiState.screen_data["value"] = value;
    }

    getCurrentScreenData() {
        return this.uiState.screen_data["value"] ?? { name: "ProductScreen" };
    }

    //see setScreenData
    getScreenData() {
        const screen = this.uiState?.screen_data["value"];
        // If no screen data is saved
        //   no payment line -> product screen
        //   with payment line -> payment screen
        if (!screen) {
            if (!this.finalized && this.payment_ids.length > 0) {
                return { name: "PaymentScreen" };
            } else if (!this.finalized) {
                return { name: "ProductScreen" };
            }
        }
        if (!this.finalized && this.payment_ids.length > 0) {
            return { name: "PaymentScreen" };
        }

        return screen || { name: "" };
    }

    waitForPushOrder() {
        return false;
    }

    updatePricelistAndFiscalPosition(newPartner) {
        let newPartnerPricelist, newPartnerFiscalPosition;
        const defaultFiscalPosition = this.models["account.fiscal.position"].find(
            (position) => position.id === this.config.default_fiscal_position_id?.id
        );

        if (newPartner) {
            newPartnerFiscalPosition = newPartner.fiscal_position_id
                ? this.models["account.fiscal.position"].find(
                      (position) => position.id === newPartner.fiscal_position_id?.id
                  )
                : defaultFiscalPosition;
            newPartnerPricelist =
                this.models["product.pricelist"].find(
                    (pricelist) => pricelist.id === newPartner.property_product_pricelist?.id
                ) || this.config.pricelist_id;
        } else {
            newPartnerFiscalPosition = defaultFiscalPosition;
            newPartnerPricelist = this.config.pricelist_id;
        }

        if (!this.config.use_presets || !this.preset_id?.fiscal_position_id) {
            this.fiscal_position_id = newPartnerFiscalPosition;
        }

        if (!this.config.use_presets || !this.preset_id?.pricelist_id) {
            this.setPricelist(newPartnerPricelist);
        }
    }

    /* ---- Ship later --- */
    //FIXME remove this
    setShippingDate(shippingDate) {
        this.shipping_date = shippingDate;
    }
    //FIXME remove this
    getShippingDate() {
        return formatDate(this.shipping_date);
    }

    getHasRefundLines() {
        for (const line of this.lines) {
            if (line.refunded_orderline_id) {
                return true;
            }
        }
        return false;
    }

    /**
     * Returns false if the current order is empty and has no payments.
     * @returns {boolean}
     */
    _isValidEmptyOrder() {
        if (this.lines.length == 0) {
            return this.payment_ids.length != 0;
        } else {
            return true;
        }
    }

    canBeValidated() {
        return this.isPaid() && this._isValidEmptyOrder() && !this.isCustomerRequired;
    }

    // NOTE: Overrided in pos_loyalty to put loyalty rewards at this end of array.
    getOrderlines() {
        return this.lines;
    }

    get floatingOrderName() {
        return this.floating_order_name || this.tracking_number.toString() || "";
    }

    sortBySequenceAndCategory(a, b) {
        const seqA = a.product_id?.pos_categ_ids[0]?.sequence ?? 0;
        const seqB = b.product_id?.pos_categ_ids[0]?.sequence ?? 0;
        const pos_categ_id_A = a.product_id?.pos_categ_ids[0]?.id ?? 0;
        const pos_categ_id_B = b.product_id?.pos_categ_ids[0]?.id ?? 0;

        if (seqA !== seqB) {
            return seqA - seqB;
        }
        return pos_categ_id_A - pos_categ_id_B;
    }

    getName() {
        let name = this.floatingOrderName || "";
        if (this.isRefund) {
            name += _t(" (Refund)");
        }
        return name;
    }
    setGeneralCustomerNote(note) {
        this.general_customer_note = note || "";
    }
    setInternalNote(note) {
        this.internal_note = note || "";
    }

    get orderChange() {
        return this.getChange();
    }

    get showRounding() {
        return !this.currency.isZero(this.taxTotals.order_rounding);
    }

    get showChange() {
        return !this.currency.isZero(this.orderChange) && this.finalized;
    }

    getOrderData() {
        return {
            reprint: false,
            pos_reference: this.getName(),
            config_name: this.config_id?.name || this.config.name,
            time: luxon.DateTime.now().toFormat("HH:mm"),
            tracking_number: this.tracking_number,
            preset_name: this.preset_id?.name || "",
            preset_time: this.presetDateTime,
            employee_name: this.employee_id?.name || this.user_id?.name,
            internal_note: getStrNotes(this.internal_note),
            general_customer_note: this.general_customer_note,
            changes: {
                title: "",
                data: [],
            },
        };
    }

    getLinesToCompute() {
        return this.lines.filter(
            (line) =>
                line.price_type === "original" &&
                !(line.combo_line_ids?.length || line.combo_parent_id)
        );
    }

    get prepLines() {
        return this.prep_order_ids?.flatMap((po) => po.prep_line_ids);
    }
    get preparationCategories() {
        return this.config.preparationCategories;
    }

    get changes() {
        const preparationLines = this.prepLines;
        const orderlines = this.lines;
        const existingQuantityStack = {};
        const changes = {
            quantity: 0,
            categoryCount: {},
            printerData: {
                addedQuantity: {},
                removedQuantity: {},
                noteUpdate: {},
            },
        };

        for (const prepLine of preparationLines) {
            const key = keyMaker(prepLine);

            if (!existingQuantityStack[key]) {
                existingQuantityStack[key] = {
                    quantity: 0,
                    preparationLines: [],
                };
            }

            existingQuantityStack[key].preparationLines.push(prepLine);
            existingQuantityStack[key].quantity += prepLine.quantity - prepLine.cancelled;
        }

        for (const orderline of orderlines) {
            const key = keyMaker(orderline);
            const product = orderline.product_id;
            const category = product.pos_categ_ids.find((c) =>
                this.preparationCategories.has(c.id)
            );

            if (!category) {
                orderline.setHasChange(false);
                continue;
            }

            if (existingQuantityStack[key]) {
                existingQuantityStack[key].quantity -= orderline.qty;
            }

            const qty = Math.abs(existingQuantityStack[key]?.quantity || orderline.qty);
            if (!existingQuantityStack[key] || existingQuantityStack[key].quantity < 0) {
                changes.quantity += qty;
                changes.printerData.addedQuantity[key] = dataMaker(orderline, qty);

                if (!changes.categoryCount[category.id]) {
                    changes.categoryCount[category.id] = {
                        name: category.name,
                        count: 0,
                    };
                }

                changes.categoryCount[category.id].count += qty;
                orderline.setHasChange(true);
                continue;
            }

            if (orderline.changeNote) {
                changes.printerData.noteUpdate[key] = dataMaker(orderline, qty);
                orderline.setHasChange(true);
                continue;
            }

            orderline.setHasChange(false);
        }

        for (const [key, data] of Object.entries(existingQuantityStack)) {
            if (data.quantity <= 0) {
                continue;
            }
            const line = data.preparationLines[0];
            const product = line.product_id;
            const category = product.pos_categ_ids.find((c) =>
                this.preparationCategories.has(c.id)
            );

            if (category) {
                if (!changes.categoryCount[category.id]) {
                    changes.categoryCount[category.id] = {
                        name: category.name,
                        count: 0,
                    };
                }

                changes.quantity += data.quantity;
                changes.categoryCount[category.id].count -= data.quantity;
                changes.printerData.removedQuantity[key] = dataMaker(line, -data.quantity);
                line.pos_order_line_id?.setHasChange(true);
            }
        }

        changes.categoryCount = Object.values(changes.categoryCount);
        changes.printerData.addedQuantity = Object.values(changes.printerData.addedQuantity);
        changes.printerData.removedQuantity = Object.values(changes.printerData.removedQuantity);
        changes.printerData.noteUpdate = Object.values(changes.printerData.noteUpdate);

        if (changes.printerData.noteUpdate.length) {
            changes.categoryCount.push({
                count: changes.printerData.noteUpdate.length,
                name: _t("Note"),
            });
        }

        return changes;
    }

    /**
     * Update the prep order group according to the given order changes.
     * Used after printing the preparation ticket to update the prep lines.
     */
    updateLastOrderChange(opts = {}) {
        if (opts.cancelled) {
            this.prepLines?.forEach((pl) => (pl.cancelled = pl.quantity));
        } else {
            // We don't need to add note updates here since preparation display will always show
            // the latest notes from the order lines.
            const changes = this.changes;
            const allChanges = [
                ...changes.printerData.addedQuantity,
                ...changes.printerData.removedQuantity,
            ];

            let prepOrder = null;
            for (const change of allChanges) {
                const line = change.line;
                const data = change.data;

                if (data.quantity > 0) {
                    const order = (prepOrder ||= this.models["pos.prep.order"].create({
                        pos_order_id: this,
                    }));

                    this.models["pos.prep.line"].create({
                        prep_order_id: order,
                        pos_order_line_id: line,
                        product_id: line.getProduct().id,
                        quantity: data.quantity,
                        cancelled: 0,
                        attribute_value_ids: line.attribute_value_ids,
                    });
                } else {
                    let toCancel = data.quantity;
                    const mainKey = keyMaker(line);
                    for (const prepLine of [...this.prepLines].reverse()) {
                        const key = keyMaker(prepLine);
                        if (key !== mainKey) {
                            continue;
                        }

                        const lineQty = prepLine.quantity - prepLine.cancelled;
                        const cancellable = Math.min(lineQty, -toCancel);
                        prepLine.cancelled += cancellable;
                        toCancel += cancellable;
                        if (toCancel >= 0) {
                            break;
                        }
                    }
                }
            }
        }

        // Update last known state to avoid re-sending changes
        this.uiState.last_general_customer_note = this.general_customer_note;
        this.uiState.last_internal_note = this.internal_note;
        this.lines.map((line) => {
            line.setHasChange(false);
            line.uiState.last_internal_note = line.getNote() || "";
            line.uiState.last_customer_note = line.getCustomerNote() || "";
            line.uiState.savedQuantity = line.getQuantity();
        });
    }
    /**
     * PoS config can have several printers with different preparation categories.
     * This method allows to filter the changes for only the given categories.
     */
    getChanges(opts = {}) {
        const changes = this.changes;
        let addedQuantity = [];
        let removedQuantity = [];
        let noteUpdate = [];
        if (opts.cancelled) {
            removedQuantity = this.lines.map(
                (l) =>
                    dataMaker(
                        l,
                        l.prep_line_ids.reduce(
                            (sum, obj) => sum + (obj.quantity - obj.cancelled),
                            0
                        )
                    ).data
            );
        } else {
            addedQuantity = changes.printerData.addedQuantity.map((c) => c.data);
            removedQuantity = changes.printerData.removedQuantity.map((c) => c.data);
            noteUpdate = changes.printerData.noteUpdate.map((c) => c.data);
        }
        const result = {
            ...changes,
            noteChange: false,
            printerData: {
                addedQuantity: addedQuantity,
                removedQuantity: removedQuantity,
                noteUpdate: noteUpdate,
            },
        };
        if (!opts.cancelled) {
            if (this.uiState.last_general_customer_note !== this.general_customer_note) {
                result.generalCustomerNote = this.general_customer_note;
                result.noteChange = true;
            }

            if (this.uiState.last_internal_note !== this.internal_note) {
                result.internalNote = this.internal_note;
                result.noteChange = true;
            }
        }

        if (opts.categoryIdsSet) {
            const matchesCategories = (product) => {
                const categoryIds = product.parentPosCategIds;
                for (const categoryId of categoryIds) {
                    if (opts.categoryIdsSet.has(categoryId)) {
                        return true;
                    }
                }
                return false;
            };

            const filterChanges = (changes) =>
                // Combo line uuids to have at least one child line in the given categories
                changes.filter((change) =>
                    change.combo_line_ids && change.combo_line_ids.length > 0
                        ? change.combo_line_ids.some((child) => matchesCategories(child.product_id))
                        : matchesCategories(
                              this.models["product.product"].get(change["product_id"])
                          )
                );
            Object.assign(result, {
                printerData: {
                    addedQuantity: filterChanges(addedQuantity),
                    removedQuantity: filterChanges(removedQuantity),
                    noteUpdate: filterChanges(noteUpdate),
                },
            });
        }

        return result;
    }

    /**
     * Data is generated per category set since each printer can have different
     * preparation categories. Also data are split between added, removed and note updates.
     *
     * If no changes are found for the given categories, the last printed data will be returned.
     */
    async generatePrinterData(opts = { categoryIdsSet: new Set(), orderChange: false }) {
        const receiptsData = [];
        const idsString = Array.from(opts.categoryIdsSet).sort().join("-");
        const orderChange = opts.orderChange
            ? opts.orderChange
            : this.getChanges({ categoryIdsSet: opts.categoryIdsSet });
        const orderData = this.getOrderData();
        const addedQuantity = orderChange.printerData.addedQuantity;
        const removedQuantity = orderChange.printerData.removedQuantity;
        const noteUpdate = orderChange.printerData.noteUpdate;
        const generateGroupedData = (data) => {
            const dataChanges = data.changes?.data;
            if (dataChanges && dataChanges.some((c) => c.group)) {
                const groupedData = dataChanges.reduce((acc, c) => {
                    const { name = "", index = -1 } = c.group || {};
                    if (!acc[name]) {
                        acc[name] = { name, index, data: [] };
                    }
                    acc[name].data.push(c);
                    return acc;
                }, {});
                data.changes.groupedData = Object.values(groupedData).sort(
                    (a, b) => a.index - b.index
                );
            }
            return data;
        };

        if (
            addedQuantity.length === 0 &&
            removedQuantity.length === 0 &&
            noteUpdate.length === 0 &&
            !orderChange.internal_note &&
            !orderChange.general_customer_note
        ) {
            const lastPrints = this.uiState.printStack[idsString];
            const data = lastPrints ? lastPrints[lastPrints.length - 1] : [];
            for (const printable of data) {
                printable.reprint = true;
            }
            return lastPrints ? lastPrints[lastPrints.length - 1] : [];
        }

        if (addedQuantity.length) {
            const orderDataNew = { ...orderData };
            orderDataNew.changes = {
                title: _t("NEW"),
                data: addedQuantity,
            };
            receiptsData.push(generateGroupedData(orderDataNew));
        }

        if (removedQuantity.length) {
            const orderDataCancelled = { ...orderData };
            orderDataCancelled.changes = {
                title: _t("CANCELLED"),
                data: removedQuantity,
            };
            receiptsData.push(generateGroupedData(orderDataCancelled));
        }

        if (noteUpdate.length) {
            const orderDataNoteUpdate = { ...orderData };
            const { noteUpdateTitle, printNoteUpdateData = true } = orderChange;
            orderDataNoteUpdate.changes = {
                title: noteUpdateTitle || _t("NOTE UPDATE"),
                data: printNoteUpdateData ? noteUpdate : [],
            };
            receiptsData.push(generateGroupedData(orderDataNoteUpdate));
            orderData.changes.noteUpdate = [];
        }

        if (orderChange.internalNote || orderChange.generalCustomerNote) {
            const orderDataNote = { ...orderData };
            orderDataNote.changes = { title: "", data: [] };
            receiptsData.push(generateGroupedData(orderDataNote));
        }

        if (!this.uiState.printStack[idsString]) {
            this.uiState.printStack[idsString] = [];
        }
        this.uiState.printStack[idsString].push(receiptsData);
        return receiptsData;
    }
}

const keyMaker = (line) => {
    const orderline = line.pos_order_line_id || line;
    const objectKey = {
        product_id: orderline.product_id.id,
        combo_parent_id: orderline.combo_parent_id?.id,
        combo_line_ids: orderline.combo_line_ids.map((c) => c.id).sort(),
        attribute_value_ids: orderline.attribute_value_ids.map((a) => a.id).sort(),
        note: orderline?.getNote?.() || "",
        customer_note: orderline?.getCustomerNote?.() || "",
    };
    return JSON.stringify(objectKey);
};

const dataMaker = (prepOrPosLine, quantity) => {
    const line = prepOrPosLine.pos_order_line_id || prepOrPosLine;
    const product = line.product_id;
    const attributes = line.attribute_value_ids || [];
    return {
        line: line,
        data: {
            basic_name: product.name,
            product_id: product.id,
            attribute_value_names: attributes.map((a) => a.name),
            quantity: quantity,
            note: getStrNotes(line?.getNote?.() || false),
            customer_note: getStrNotes(line?.getCustomerNote?.() || false),
            pos_categ_id: product.pos_categ_ids[0]?.id || 0,
            pos_categ_sequence: product.pos_categ_ids[0]?.sequence || 0,
            group: line?.getCourse?.() || false,
            combo_line_ids: line?.combo_line_ids,
            combo_parent_uuid: line?.combo_parent_id?.uuid,
        },
    };
};

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
