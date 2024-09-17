import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { serializeDateTime } from "@web/core/l10n/dates";
import { random5Chars, uuidv4 } from "@point_of_sale/utils";
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

        if (!this.session_id && typeof this.id === "string") {
            this.session_id = this.session;
        }

        // Data present in python model
        this.date_order = vals.date_order || serializeDateTime(luxon.DateTime.now());
        this.to_invoice = vals.to_invoice || false;
        this.shipping_date = vals.shipping_date || false;
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

        // !!Keep all uiState in one object!!
        this.uiState = {
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

        if (!this.session_id) {
            this.session_id = this.session;
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

<<<<<<< saas-18.1
    get presetTime() {
        const dateTime = DateTime.fromSQL(this.preset_time);
        return dateTime.isValid ? dateTime.toFormat("HH:mm") : false;
||||||| 69b404c7109ff689381f56520aad758424ec01aa
    getEmailItems() {
        return [_t("the receipt")].concat(this.is_to_invoice() ? [_t("the invoice")] : []);
=======
    get originalSplittedOrder() {
        return this.models["pos.order"].find((o) => o.uuid === this.uiState.splittedOrderUuid);
    }
    getEmailItems() {
        return [_t("the receipt")].concat(this.is_to_invoice() ? [_t("the invoice")] : []);
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
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
        const isRefund = this._isRefundOrder();
        const documentSign = isRefund ? -1 : 1;

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
        let cashRounding =
            !this.config.only_round_cash_method && this.config.cash_rounding
                ? this.config.rounding_method
                : null;

        const taxTotals = accountTaxHelpers.get_tax_totals_summary(baseLines, currency, company, {
            cash_rounding: cashRounding,
        });

        cashRounding = this.config.rounding_method;
        taxTotals.order_sign = documentSign;
        taxTotals.order_total =
            taxTotals.total_amount_currency - (taxTotals.cash_rounding_base_amount_currency || 0.0);
        taxTotals.order_rounding = taxTotals.cash_rounding_base_amount_currency || 0.0;
        taxTotals.order_to_pay = taxTotals.total_amount_currency;

        // Compute the amount left to pay (exclude the payment line for change).
        let amountPaid = 0.0;
        for (const payment of this.payment_ids) {
            if (payment.isDone() && !payment.is_change) {
                amountPaid += documentSign * payment.getAmount();
            }
        }

        // Compute the cash rounding amounts.
        // Basically, we have to determine if the residual amount if due to a cash rounding or not.
        let amountLeft = taxTotals.total_amount_currency - amountPaid;
        if (
            this.config.cash_rounding &&
            cashRounding &&
            this.payment_ids.some((x) => x.payment_method_id.is_cash_count)
        ) {
            if (!floatIsZero(amountLeft, this.currency.decimal_places)) {
                const roundingMethod = cashRounding.rounding_method;
                let lowerBound = 0.0;
                let upperBound = 0.0;
                if (roundingMethod === "UP") {
                    // Paid 15.70. It can be a cash rounding if in [15.66, 15.70].
                    lowerBound = -cashRounding.rounding + this.currency.rounding;
                } else if (roundingMethod === "DOWN") {
                    // Paid 15.70. It can be a cash rounding if in [15.70, 15.74].
                    upperBound = cashRounding.rounding - this.currency.rounding;
                } else if (roundingMethod === "HALF-UP") {
                    // Paid 15.70. It can be a cash rounding if in [15.66, 15.74].
                    const halfUpDelta =
                        this.currency.rounding *
                        Math.ceil(cashRounding.rounding / this.currency.rounding / 2);
                    lowerBound = -halfUpDelta;
                    upperBound = halfUpDelta;
                }
                const amountLeftWithRounding = amountLeft - taxTotals.order_rounding;
                if (
                    (lowerBound < amountLeftWithRounding && amountLeftWithRounding < upperBound) ||
                    floatIsZero(
                        lowerBound - amountLeftWithRounding,
                        this.currency.decimal_places
                    ) ||
                    floatIsZero(upperBound - amountLeftWithRounding, this.currency.decimal_places)
                ) {
                    taxTotals.payment_cash_rounding_amount_currency = -amountLeft;
                    taxTotals.order_rounding -= amountLeft;
                    taxTotals.order_to_pay -= amountLeft;
                    amountLeft = 0.0;
                }
            }
        }

        if (!floatIsZero(Math.min(0, amountLeft), this.currency.decimal_places)) {
            taxTotals.order_change = -amountLeft;
        }

        if (floatIsZero(taxTotals.order_rounding, this.currency.decimal_places)) {
            delete taxTotals.order_rounding;
        }

        return taxTotals;
    }

    /**
     * Get the amount to pay by default when creating a new payment.
     * @param paymentMethod: The payment method of the payment to be created.
     * @returns A monetary value.
     */
    getDefaultAmountDueToPayIn(paymentMethod) {
        let totalAmountDue = this.getDue();
        if (paymentMethod.is_cash_count && this.config.cash_rounding) {
            const cashRounding = this.config.rounding_method;
            const taxTotals = this.taxTotals;

            // Suppose you have a cash rounding 0.05 DOWN on the whole pos order.
            // Your pos order has a total amount of 15.72.
            // After the cash rounding, the total of your pos order becomes 15.70.
            // Now you pay 0.67 in bank. The residual amount to pay becomes 15.03.
            // Now you pay the rest using a cash payment method.
            // Without adding the cash rounding amount, the suggested amount to pay in cash will be 15.0 and
            // the total paid on the pos order will be 0.67 + 15.0 = 15.67 so a rounding of -0.05 has been applied.
            // This result is weird since the cash rounding method is on 0.05.
            // To avoid that, we add the collected rounding so far to compute the suggested amount.
            // That way, the suggested cash amount will be computed on 15.05 and not 15.03.
            totalAmountDue = roundPrecision(
                totalAmountDue -
                    (taxTotals.order_sign * taxTotals.cash_rounding_base_amount_currency || 0.0),
                cashRounding.rounding,
                cashRounding.rounding_method
            );
        }
        return totalAmountDue;
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
                        attribute_value_ids: line.attribute_value_ids.map((a) => ({
                            ...a.serialize({ orm: true }),
                            name: a.name,
                        })),
                        uuid: line.uuid,
                        isCombo: line.combo_item_id?.id,
                        product_id: line.getProduct().id,
                        name: line.getFullProductName(),
                        basic_name: line.getProduct().name,
                        note: line.getNote(),
                        quantity: line.getQuantity(),
                    };
                }
                line.setHasChange(false);
                line.saved_quantity = line.get_quantity();
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
                (orderline) =>
                    orderline.skip_change &&
                    !orderline.uiState.hideSkipChangeClass &&
                    !orderline.origin_order_id
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
        return false;
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

<<<<<<< saas-18.1
    getTotalWithTax() {
        return this.taxTotals.order_sign * this.taxTotals.total_amount_currency;
||||||| 69b404c7109ff689381f56520aad758424ec01aa
    get_total_with_tax() {
        return this.get_total_without_tax() + this.get_total_tax();
=======
    get_total_with_tax() {
        return this.get_total_with_tax_of_lines(this.lines);
    }

    get_total_with_tax_of_lines(lines) {
        return this.get_total_without_tax_of_lines(lines) + this.get_total_tax_of_lines(lines);
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
    }

<<<<<<< saas-18.1
    getTotalWithoutTax() {
        return this.taxTotals.order_sign * this.taxTotals.base_amount_currency;
||||||| 69b404c7109ff689381f56520aad758424ec01aa
    get_total_without_tax() {
        return roundPrecision(
            this.lines.reduce(function (sum, line) {
                return sum + line.get_price_without_tax();
            }, 0),
            this.currency.rounding
        );
=======
    get_total_without_tax() {
        return this.get_total_without_tax_of_lines(this.lines);
    }

    get_total_without_tax_of_lines(lines) {
        return roundPrecision(
            lines.reduce(function (sum, line) {
                return sum + line.get_price_without_tax();
            }, 0),
            this.currency.rounding
        );
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
    }

    _getIgnoredProductIdsTotalDiscount() {
        return [];
    }

    // sjai
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
<<<<<<< saas-18.1
                        orderLine.getUnitDisplayPriceBeforeDiscount() *
                        (orderLine.getDiscount() / 100) *
                        orderLine.getQuantity();
                    if (orderLine.displayDiscountPolicy() === "without_discount") {
||||||| 69b404c7109ff689381f56520aad758424ec01aa
                        orderLine.getUnitDisplayPriceBeforeDiscount() *
                        (orderLine.get_discount() / 100) *
                        orderLine.get_quantity();
                    if (orderLine.display_discount_policy() === "without_discount") {
=======
                        orderLine.get_all_prices().priceWithTaxBeforeDiscount -
                        orderLine.get_all_prices().priceWithTax;
                    if (orderLine.display_discount_policy() === "without_discount") {
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
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

<<<<<<< saas-18.1
    getTotalTax() {
        return this.taxTotals.order_sign * this.taxTotals.tax_amount_currency;
||||||| 69b404c7109ff689381f56520aad758424ec01aa
    get_total_tax() {
        if (this.company.tax_calculation_rounding_method === "round_globally") {
            // As always, we need:
            // 1. For each tax, sum their amount across all order lines
            // 2. Round that result
            // 3. Sum all those rounded amounts
            const groupTaxes = {};
            this.lines.forEach(function (line) {
                const taxDetails = line.get_tax_details();
                const taxIds = Object.keys(taxDetails);
                for (const taxId of taxIds) {
                    if (!(taxId in groupTaxes)) {
                        groupTaxes[taxId] = 0;
                    }
                    groupTaxes[taxId] += taxDetails[taxId].amount;
                }
            });

            let sum = 0;
            const taxIds = Object.keys(groupTaxes);
            for (var j = 0; j < taxIds.length; j++) {
                var taxAmount = groupTaxes[taxIds[j]];
                sum += roundPrecision(taxAmount, this.currency.rounding);
            }

            return sum;
        } else {
            return roundPrecision(
                this.lines.reduce(function (sum, orderLine) {
                    return sum + orderLine.get_tax();
                }, 0),
                this.currency.rounding
            );
        }
=======
    get_total_tax() {
        return this.get_total_tax_of_lines(this.lines);
    }

    get_total_tax_of_lines(lines) {
        if (this.company.tax_calculation_rounding_method === "round_globally") {
            // As always, we need:
            // 1. For each tax, sum their amount across all order lines
            // 2. Round that result
            // 3. Sum all those rounded amounts
            const groupTaxes = {};
            lines.forEach(function (line) {
                const taxDetails = line.get_tax_details();
                const taxIds = Object.keys(taxDetails);
                for (const taxId of taxIds) {
                    if (!(taxId in groupTaxes)) {
                        groupTaxes[taxId] = 0;
                    }
                    groupTaxes[taxId] += taxDetails[taxId].amount;
                }
            });

            let sum = 0;
            const taxIds = Object.keys(groupTaxes);
            for (var j = 0; j < taxIds.length; j++) {
                var taxAmount = groupTaxes[taxIds[j]];
                sum += roundPrecision(taxAmount, this.currency.rounding);
            }

            return sum;
        } else {
            return roundPrecision(
                lines.reduce(function (sum, orderLine) {
                    return sum + orderLine.get_tax();
                }, 0),
                this.currency.rounding
            );
        }
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
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
        return this.getTotalWithTax() + this.getRoundingApplied();
    }

<<<<<<< saas-18.1
    getTaxDetails() {
||||||| 69b404c7109ff689381f56520aad758424ec01aa
    get_tax_details() {
=======
    get_tax_details() {
        return this.get_tax_details_of_lines(this.lines);
    }

    get_tax_details_of_lines(lines) {
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
        const taxDetails = {};
<<<<<<< saas-18.1
        for (const line of this.lines) {
            for (const taxData of line.allPrices.taxesData) {
||||||| 69b404c7109ff689381f56520aad758424ec01aa
        for (const line of this.lines) {
            for (const taxData of line.get_all_prices().taxesData) {
=======
        for (const line of lines) {
            for (const taxData of line.get_all_prices().taxesData) {
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
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

    hasRemainingAmount() {
        const dueAmount = this.getDue();
        const changeAmount = this.getChange();
        const orderSign = this.taxTotals.order_sign;
        return (
            floatIsZero(changeAmount, this.currency.decimal_places) &&
            (floatIsZero(dueAmount, this.currency.decimal_places) || orderSign * dueAmount > 0.0)
        );
    }

    getChange() {
        return this.taxTotals.order_sign * (this.taxTotals.order_change || 0.0);
    }

    getDue() {
        const due = this.getTotalWithTax() - this.getTotalPaid() + this.getRoundingApplied();
        return roundPrecision(due, this.currency.rounding);
    }

    getRoundingApplied() {
        return (
            this.taxTotals.order_sign *
            (this.taxTotals.payment_cash_rounding_amount_currency || 0.0)
        );
    }

    isPaid() {
        return this.getDue() <= 0;
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
}

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
