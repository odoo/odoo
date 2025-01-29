import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { random5Chars, uuidv4, gte, lt } from "@point_of_sale/utils";
import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { computeComboItems } from "./utils/compute_combo_items";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { getTaxesAfterFiscalPosition } from "./utils/tax_utils";

const formatCurrency = registry.subRegistries.formatters.content.monetary[1];
const { DateTime } = luxon;

export class PosOrder extends Base {
    static pythonModel = "pos.order";

    setup(vals) {
        super.setup(vals);

        if (!this.session_id && (!this.finalized || typeof this.id !== "number")) {
            this.session_id = this.session;
        }

        // Data present in python model
        this.nb_print = vals.nb_print || 0;
        this.to_invoice = vals.to_invoice || false;
        this.state = vals.state || "draft";
        this.uuid = vals.uuid ? vals.uuid : uuidv4();
        this.last_order_preparation_change = vals.last_order_preparation_change
            ? JSON.parse(vals.last_order_preparation_change)
            : {
                  lines: {},
                  general_customer_note: "",
                  internal_note: "",
                  sittingMode: 0,
              };
        this.general_customer_note = vals.general_customer_note || "";
        this.internal_note = vals.internal_note || "";
        if (!vals.lines) {
            this.lines = [];
        }

        if (!this.date_order) {
            this.date_order = DateTime.now();
        }

        // !!Keep all uiState in one object!!
        if (!this.uiState) {
            this.uiState = {
                unmerge: {},
                lastPrint: false,
                lineToRefund: {},
                displayed: true,
                booked: false,
                screen_data: {},
                selected_orderline_uuid: undefined,
                selected_paymentline_uuid: undefined,
                locked: this.state !== "draft",
                // Pos restaurant specific to most proper way is to override this
                TipScreen: {
                    inputTipAmount: "",
                },
            };
        }
    }

    get user() {
        return this.models["res.users"].getFirst();
    }

    get company() {
        return this.models["res.company"].getFirst();
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

    get presetTime() {
        return this.preset_time && this.preset_time.isValid
            ? this.preset_time.toFormat("HH:mm")
            : false;
    }

    get presetRequirementsFilled() {
        return (
            (!this.preset_id?.needsPartner ||
                (this.partner_id?.name && this.partner_id?.pos_contact_address)) &&
            (!this.preset_id?.needsName || this.partner_id?.name || this.floating_order_name) &&
            (!this.preset_id?.needsSlot || this.preset_time)
        );
    }

    getEmailItems() {
        return [_t("the receipt")].concat(this.isToInvoice() ? [_t("the invoice")] : []);
    }

    setPreset(preset) {
        this.setPricelist(preset.pricelist_id);
        this.fiscal_position_id = preset.fiscal_position_id;
        this.preset_id = preset;
    }

    /**
     * Get the details total amounts with and without taxes, the details of taxes per subtotal and per tax group.
     * @returns See '_get_tax_totals_summary' in account_tax.py for the full details.
     */
    get taxTotals() {
        const currency = this.currency;
        const company = this.company;
        const extraValues = { currency_id: currency };
        const orderLines = this.lines;

        // If one of the lines is negative, we assume it's a refund order.
        // This assumes that we don't mix refunds from normal orders.
        // TODO: Properly differentiate a refund orders from a normal ones.
        const documentSign = this.lines.some((l) =>
            lt(l.qty, 0, { decimals: currency.decimal_places })
        )
            ? -1
            : 1;

        const baseLines = [];
        for (const line of orderLines) {
            let taxes = line.tax_ids;
            if (this.fiscal_position_id) {
                taxes = getTaxesAfterFiscalPosition(taxes, this.fiscal_position_id, this.models);
            }
            baseLines.push(
                accountTaxHelpers.prepare_base_line_for_taxes_computation(line, {
                    ...extraValues,
                    quantity: documentSign * line.qty,
                    tax_ids: taxes,
                })
            );
        }
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
                    if (!floatIsZero(paymentAmount - remaining, this.currency.decimal_places)) {
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
        return floatIsZero(remaining_with_rounding, this.currency.decimal_places);
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
        let { rounding_method: method, rounding } = roundingMethod;
        if (
            lt(remaining, 0, {
                decimals: this.currency.decimal_places,
            })
        ) {
            // oppose the rounding method if remaining is negative
            method =
                method === "UP"
                    ? "DOWN"
                    : method === "DOWN"
                    ? "UP"
                    : method === "HALF-UP"
                    ? "HALF-DOWN"
                    : method === "HALF-DOWN"
                    ? "HALF-UP"
                    : method;
        }
        if (floatIsZero(remaining, this.currency.decimal_places)) {
            return 0;
        }
        return roundPrecision(remaining, rounding, method);
    }

    getCashierName() {
        return this.user_id?.name;
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
    /**
     * This function is called after the order has been successfully sent to the preparation tool(s).
     * In the future, this status should be separated between the different preparation tools,
     * so that if one of them returns an error, it is possible to send the information back to it
     * without impacting the other tools.
     */
    updateLastOrderChange() {
        const orderlineIdx = [];
        this.lines.forEach((line) => {
            if (!line.skip_change) {
                orderlineIdx.push(line.preparationKey);

                if (this.last_order_preparation_change.lines[line.preparationKey]) {
                    this.last_order_preparation_change.lines[line.preparationKey]["quantity"] =
                        line.getQuantity();
                } else {
                    this.last_order_preparation_change.lines[line.preparationKey] = {
                        attribute_value_names: line.attribute_value_ids.map((a) => a.name),
                        uuid: line.uuid,
                        isCombo: line.combo_item_id?.id,
                        product_id: line.getProduct().id,
                        name: line.getFullProductName(),
                        basic_name: line.getProduct().name,
                        display_name: line.getProduct().display_name,
                        note: line.getNote(),
                        quantity: line.getQuantity(),
                    };
                }
                line.setHasChange(false);
            }
        });
        // Checks whether an orderline has been deleted from the order since it
        // was last sent to the preparation tools or updated. If so we delete older changes.
        for (const [key, change] of Object.entries(this.last_order_preparation_change.lines)) {
            const orderline = this.models["pos.order.line"].getBy("uuid", change.uuid);
            if (!orderline || change.note.trim() !== orderline.note.trim()) {
                delete this.last_order_preparation_change.lines[key];
            }
        }
        this.last_order_preparation_change.general_customer_note = this.general_customer_note;
        this.last_order_preparation_change.internal_note = this.internal_note;
        this.last_order_preparation_change.sittingMode = this.preset_id?.id || 0;
    }

    hasSkippedChanges() {
        return Boolean(
            this.lines.find(
                (orderline) => orderline.skip_change && !orderline.uiState.hideSkipChangeClass
            )
        );
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

    getOrderlinesGroupedByTaxIds() {
        const orderlines_by_tax_group = {};
        const lines = this.getOrderlines();
        for (const line of lines) {
            const tax_group = this._getTaxGroupKey(line);
            if (!(tax_group in orderlines_by_tax_group)) {
                orderlines_by_tax_group[tax_group] = [];
            }
            orderlines_by_tax_group[tax_group].push(line);
        }
        return orderlines_by_tax_group;
    }

    _getTaxGroupKey(line) {
        return line
            ._getProductTaxesAfterFiscalPosition()
            .map((tax) => tax.id)
            .join(",");
    }

    /**
     * Calculate the amount that will be used as a base in order to apply a downpayment or discount product in PoS.
     * In our calculation we take into account taxes that are included in the price.
     *
     * @param  {String} tax_ids a string of the tax ids that are applied on the orderlines, in csv format
     * e.g. if taxes with ids 2, 5 and 6 are applied tax_ids will be "2,5,6"
     * @param  {Orderline[]} lines an srray of Orderlines
     * @return {Number} the base amount on which we will apply a percentile reduction
     */
    calculateBaseAmount(lines) {
        const base_amount = lines.reduce(
            (sum, line) =>
                sum +
                line.getAllPrices().priceWithTax -
                line
                    .getAllPrices()
                    .taxesData.filter((tax) => !tax.price_include)
                    .reduce((sum, tax) => (sum += tax.tax_amount), 0),
            0
        );
        return base_amount;
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

        const lines_to_recompute = this.lines.filter(
            (line) =>
                line.price_type === "original" &&
                !(line.combo_line_ids?.length || line.combo_parent_id)
        );

        for (const line of lines_to_recompute) {
            const newPrice = line.product_id.getPrice(
                pricelist,
                line.getQuantity(),
                line.getPriceExtra(),
                false,
                line.product_id
            );
            line.setUnitPrice(newPrice);
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
                        };
                    } else {
                        return { combo_item_id: cLine.combo_item_id };
                    }
                }),
                pricelist,
                this.models["decimal.precision"].getAll(),
                this.models["product.template.attribute.value"].getAllBy("id")
            );
        }
        const combo_children_lines = this.lines.filter(
            (line) => line.price_type === "original" && line.combo_parent_id
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

    _isRefundOrder() {
        if (this.lines.length > 0 && this.lines[0].refunded_orderline_id) {
            return true;
        }
        return false;
    }

    doNotAllowRefundAndSales() {
        return true;
    }

    _isRefundAndSalesNotAllowed(values, options) {
        return (
            this._isRefundOrder() &&
            this.doNotAllowRefundAndSales() &&
            (!values.qty || values.qty > 0)
        );
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
                (payment_method.payment_terminal && !this._isRefundOrder()) ||
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
    /**
     * Stops a payment on the terminal if one is running
     */
    stopElectronicPayment() {
        const lines = this.payment_ids;
        const line = lines.find(function (line) {
            var status = line.getPaymentStatus();
            return (
                status && !["done", "reversed", "reversing", "pending", "retry"].includes(status)
            );
        });

        if (line) {
            line.setPaymentStatus("waitingCancel");
            line.payment_method_id.payment_terminal
                .sendPaymentCancel(this, line.uuid)
                .finally(function () {
                    line.setPaymentStatus("retry");
                });
        }
    }

    /* ---- Payment Status --- */
    getSubtotal() {
        return roundPrecision(
            this.lines.reduce(function (sum, orderLine) {
                return sum + orderLine.getDisplayPrice();
            }, 0),
            this.currency.rounding
        );
    }

    getTotalWithTax() {
        return this.taxTotals.order_sign * this.taxTotals.order_total;
    }

    getTotalWithoutTax() {
        const base_amount =
            this.taxTotals.base_amount_currency +
            (this.taxTotals.cash_rounding_base_amount_currency || 0.0);
        return this.taxTotals.order_sign * base_amount;
    }

    _getIgnoredProductIdsTotalDiscount() {
        return [];
    }

    _reduceTotalDiscountCallback(sum, orderLine) {
        let discountUnitPrice =
            orderLine.getUnitDisplayPriceBeforeDiscount() * (orderLine.getDiscount() / 100);
        if (orderLine.displayDiscountPolicy() === "without_discount") {
            discountUnitPrice +=
                orderLine.getTaxedlstUnitPrice() - orderLine.getUnitDisplayPriceBeforeDiscount();
        }
        return sum + discountUnitPrice * orderLine.getQuantity();
    }

    getTotalDiscount() {
        const ignored_product_ids = this._getIgnoredProductIdsTotalDiscount();
        return roundPrecision(
            this.lines.reduce((sum, orderLine) => {
                if (!ignored_product_ids.includes(orderLine.product_id.id)) {
                    sum +=
                        orderLine.getUnitDisplayPriceBeforeDiscount() *
                        (orderLine.getDiscount() / 100) *
                        orderLine.getQuantity();
                    if (
                        orderLine.displayDiscountPolicy() === "without_discount" &&
                        !(orderLine.price_type === "manual")
                    ) {
                        sum +=
                            (orderLine.getTaxedlstUnitPrice() -
                                orderLine.getUnitDisplayPriceBeforeDiscount()) *
                            orderLine.getQuantity();
                    }
                }
                return sum;
            }, 0),
            this.currency.rounding
        );
    }

    getTotalTax() {
        return this.taxTotals.order_sign * this.taxTotals.tax_amount_currency;
    }

    getTotalPaid() {
        return roundPrecision(
            this.payment_ids.reduce(function (sum, paymentLine) {
                if (paymentLine.isDone()) {
                    sum += paymentLine.getAmount();
                }
                return sum;
            }, 0),
            this.currency.rounding
        );
    }

    getTotalDue() {
        return this.taxTotals.order_sign * this.taxTotals.order_total;
    }

    getTaxDetails() {
        const taxDetails = {};
        for (const line of this.lines) {
            for (const taxData of line.allPrices.taxesData) {
                const taxId = taxData.id;
                if (!taxDetails[taxId]) {
                    taxDetails[taxId] = Object.assign({}, taxData, {
                        amount: 0.0,
                        base: 0.0,
                        tax_percentage: taxData.amount,
                    });
                }
                taxDetails[taxId].base += taxData.base_amount;
                taxDetails[taxId].amount += taxData.tax_amount;
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
        return (
            this.orderHasZeroRemaining ||
            gte(order_remaining, 0, { decimals: this.currency.decimal_places })
        );
    }

    getChange() {
        let { order_sign, order_remaining: remaining } = this.taxTotals;
        if (this.config.cash_rounding) {
            remaining = this.getRoundedRemaining(this.config.rounding_method, remaining);
        }
        return -order_sign * remaining;
    }

    getDue() {
        return (
            this.taxTotals.order_sign *
            roundPrecision(this.taxTotals.order_remaining, this.currency.rounding)
        );
    }

    getRoundingApplied() {
        return this.taxTotals.order_sign * (this.taxTotals.order_rounding || 0.0);
    }

    isPaid() {
        const { order_remaining } = this.taxTotals;
        return (
            this.orderHasZeroRemaining ||
            lt(order_remaining, 0, { decimals: this.currency.decimal_places })
        );
    }

    isRefundInProcess() {
        return (
            this._isRefundOrder() &&
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

    // FIXME remove this
    isToInvoice() {
        return this.to_invoice;
    }

    /* ---- Partner --- */
    // the partner related to the current order.
    setPartner(partner) {
        this.assertEditable();
        this.partner_id = partner;
        this.updatePricelistAndFiscalPosition(partner);
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
            newPartnerFiscalPosition = newPartner.property_account_position_id
                ? this.models["account.fiscal.position"].find(
                      (position) => position.id === newPartner.property_account_position_id?.id
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

        if (!this.config.use_presets || !this.preset_id.fiscal_position_id) {
            this.fiscal_position_id = newPartnerFiscalPosition;
        }

        if (!this.config.use_presets || !this.preset_id.pricelist_id) {
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
        return this.shipping_date;
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

    _generateTicketCode() {
        return random5Chars();
    }

    // NOTE: Overrided in pos_loyalty to put loyalty rewards at this end of array.
    getOrderlines() {
        return this.lines;
    }

    serialize() {
        const data = super.serialize(...arguments);

        if (
            data.last_order_preparation_change &&
            typeof data.last_order_preparation_change === "object"
        ) {
            data.last_order_preparation_change = JSON.stringify(data.last_order_preparation_change);
        }

        return data;
    }
    getCustomerDisplayData() {
        return {
            lines: this.getSortedOrderlines().map((l) => ({
                ...l.getDisplayData(),
                isSelected: l.isSelected(),
                imageSrc: `/web/image/product.product/${l.product_id.id}/image_128`,
            })),
            finalized: this.finalized,
            amount: formatCurrency(this.getTotalWithTax() || 0),
            paymentLines: this.payment_ids.map((pl) => ({
                name: pl.payment_method_id.name,
                amount: formatCurrency(pl.getAmount()),
            })),
            change: this.getChange() && formatCurrency(this.getChange()),
            generalCustomerNote: this.general_customer_note || "",
        };
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

    // orderlines will be sorted on the basis of pos product category and sequence for group the orderlines in order cart
    getSortedOrderlines() {
        if (this.config.orderlines_sequence_in_cart_by_category && this.lines.length) {
            const linesToSort = [...this.lines];
            linesToSort.sort(this.sortBySequenceAndCategory);
            const resultLines = [];
            linesToSort.forEach((line) => {
                if (line.combo_line_ids?.length > 0) {
                    resultLines.push(line);
                    const sortedChildLines = line.combo_line_ids.sort(
                        this.sortBySequenceAndCategory
                    );
                    resultLines.push(...sortedChildLines);
                } else if (!line.combo_parent_id) {
                    resultLines.push(line);
                }
            });
            return resultLines;
        } else {
            return this.lines;
        }
    }
    getName() {
        return this.floatingOrderName || "";
    }
    setGeneralCustomerNote(note) {
        this.general_customer_note = note || "";
        this.setDirty();
    }
    setInternalNote(note) {
        this.internal_note = note || "";
        this.setDirty();
    }

    get orderChange() {
        return this.getChange();
    }

    get showRounding() {
        return !floatIsZero(this.taxTotals.order_rounding, this.currency.decimal_places);
    }

    get showChange() {
        return !floatIsZero(this.orderChange, this.currency.decimal_places) && this.finalized;
    }
}

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
