import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { formatDate, formatDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { omit } from "@web/core/utils/objects";
import { parseUTCString, qrCodeSrc, random5Chars, uuidv4 } from "@point_of_sale/utils";
import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { computeComboItems } from "./utils/compute_combo_items";

const { DateTime } = luxon;
const formatCurrency = registry.subRegistries.formatters.content.monetary[1];

export class PosOrder extends Base {
    static pythonModel = "pos.order";

    setup(vals) {
        super.setup(vals);

        if (!this.session_id && typeof this.id === "string") {
            this.update({ session_id: this.session });
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
                  generalNote: "",
                  sittingMode: "dine in",
              };
        this.general_note = vals.general_note || "";
        this.tracking_number =
            vals.tracking_number && !isNaN(parseInt(vals.tracking_number))
                ? vals.tracking_number
                : ((this.session?.id % 10) * 100 + (this.sequence_number % 100)).toString();

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
        return this.models["res.currency"].getFirst();
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

    get isUnsyncedPaid() {
        return this.finalized && typeof this.id === "string";
    }

    get originalSplittedOrder() {
        return this.models["pos.order"].find((o) => o.uuid === this.uiState.splittedOrderUuid);
    }
    getEmailItems() {
        return [_t("the receipt")].concat(this.is_to_invoice() ? [_t("the invoice")] : []);
    }

    export_for_printing(baseUrl, headerData) {
        const paymentlines = this.payment_ids
            .filter((p) => !p.is_change)
            .map((p) => p.export_for_printing());
        return {
            orderlines: this.getSortedOrderlines().map((l) =>
                omit(l.getDisplayData(), "internalNote")
            ),
            paymentlines,
            amount_total: this.get_total_with_tax(),
            total_without_tax: this.get_total_without_tax(),
            amount_tax: this.get_total_tax(),
            total_paid: this.get_total_paid(),
            total_discount: this.get_total_discount(),
            rounding_applied: this.get_rounding_applied(),
            tax_details: this.get_tax_details(),
            change: this.amount_return,
            name: this.pos_reference,
            generalNote: this.general_note || "",
            invoice_id: null, //TODO
            cashier: this.getCashierName(),
            date: formatDateTime(parseUTCString(this.date_order)),
            pos_qr_code:
                this.company.point_of_sale_use_ticket_qr_code &&
                this.finalized &&
                qrCodeSrc(`${baseUrl}/pos/ticket/`),
            ticket_code: this.ticket_code,
            base_url: baseUrl,
            footer: this.config.receipt_footer,
            // FIXME: isn't there a better way to handle this date?
            shippingDate: this.shipping_date && formatDate(DateTime.fromSQL(this.shipping_date)),
            headerData: {
                ...headerData,
                trackingNumber: this.tracking_number,
            },
            screenName: "ReceiptScreen",
        };
    }
    getCashierName() {
        return this.user_id?.name;
    }
    canPay() {
        return this.lines.length;
    }
    recomputeOrderData() {
        this.amount_paid = this.get_total_paid();
        this.amount_tax = this.get_total_tax();
        this.amount_total = this.get_total_with_tax();
        this.amount_return = this.get_change();
        this.lines.forEach((line) => {
            line.price_subtotal = line.get_price_without_tax();
            line.price_subtotal_incl = line.get_price_with_tax();
        });
    }

    get isBooked() {
        return Boolean(this.uiState.booked || !this.is_empty() || typeof this.id === "number");
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
                        line.get_quantity();
                } else {
                    this.last_order_preparation_change.lines[line.preparationKey] = {
                        attribute_value_ids: line.attribute_value_ids.map((a) => ({
                            ...a.serialize({ orm: true }),
                            name: a.name,
                        })),
                        uuid: line.uuid,
                        isCombo: line.combo_item_id?.id,
                        product_id: line.get_product().id,
                        name: line.get_full_product_name(),
                        basic_name: line.get_product().name,
                        note: line.getNote(),
                        quantity: line.get_quantity(),
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
        this.last_order_preparation_change.sittingMode = this.takeaway ? "takeaway" : "dine in";
        this.last_order_preparation_change.generalNote = this.general_note;
    }

    hasSkippedChanges() {
        return this.lines.find((orderline) => orderline.skip_change) ? true : false;
    }

    is_empty() {
        return this.lines.length === 0;
    }

    generate_unique_id() {
        // Generates a public identification number for the order.
        // The generated number must be unique and sequential. They are made 12 digit long
        // to fit into EAN-13 barcodes, should it be needed

        function zero_pad(num, size) {
            var s = "" + num;
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
        }
        return (
            zero_pad(this.session.id, 5) +
            "-" +
            zero_pad(this.session.login_number, 3) +
            "-" +
            zero_pad(this.sequence_number, 4)
        );
    }

    updateSavedQuantity() {
        this.lines.forEach((line) => line.updateSavedQuantity());
    }

    assert_editable() {
        if (this.finalized) {
            throw new Error("Finalized Order cannot be modified");
        }
        return true;
    }

    get_orderline(id) {
        const orderlines = this.lines;
        for (let i = 0; i < orderlines.length; i++) {
            if (orderlines[i].id === id) {
                return orderlines[i];
            }
        }
        return null;
    }

    get_orderlines_grouped_by_tax_ids() {
        const orderlines_by_tax_group = {};
        const lines = this.get_orderlines();
        for (const line of lines) {
            const tax_group = this._get_tax_group_key(line);
            if (!(tax_group in orderlines_by_tax_group)) {
                orderlines_by_tax_group[tax_group] = [];
            }
            orderlines_by_tax_group[tax_group].push(line);
        }
        return orderlines_by_tax_group;
    }

    _get_tax_group_key(line) {
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
    calculate_base_amount(tax_ids_array, lines) {
        // Consider price_include taxes use case
        const has_taxes_included_in_price = tax_ids_array.filter(
            (tax_id) => this.models["account.tax"].get(tax_id).price_include
        ).length;

        const base_amount = lines.reduce(
            (sum, line) =>
                sum +
                line.get_price_without_tax() +
                (has_taxes_included_in_price ? line.get_total_taxes_included_in_price() : 0),
            0
        );
        return base_amount;
    }

    get_last_orderline() {
        const orderlines = this.lines;
        return this.lines.at(orderlines.length - 1);
    }

    get_tip() {
        const tip_product = this.config.tip_product_id;
        const lines = this.lines;
        if (!tip_product) {
            return 0;
        } else {
            for (const line of lines) {
                if (line.get_product() === tip_product) {
                    return line.get_unit_price();
                }
            }
            return 0;
        }
    }

    set_pricelist(pricelist) {
        if (pricelist) {
            this.update({ pricelist_id: pricelist });
        } else {
            this.update({ pricelist_id: false });
        }

        const lines_to_recompute = this.lines.filter(
            (line) =>
                line.price_type === "original" &&
                !(line.combo_line_ids?.length || line.combo_parent_id)
        );

        for (const line of lines_to_recompute) {
            const newPrice = line.product_id.get_price(
                pricelist,
                line.get_quantity(),
                line.get_price_extra()
            );
            line.set_unit_price(newPrice);
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
            line.set_unit_price(
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

            if (this.assert_editable()) {
                lineToRemove.delete();
            }
        }
        if (!this.lines.length) {
            this.general_note = ""; // reset general note on empty order
        }
        this.select_orderline(this.get_last_orderline());
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

    get_selected_orderline() {
        return this.lines.find((line) => line.uuid === this.uiState.selected_orderline_uuid);
    }

    get_selected_paymentline() {
        return this.payment_ids.find(
            (line) => line.uuid === this.uiState.selected_paymentline_uuid
        );
    }

    select_orderline(line) {
        if (line) {
            this.uiState.selected_orderline_uuid = line.uuid;
        } else {
            this.uiState.selected_orderline_uuid = undefined;
        }
    }

    deselect_orderline() {
        if (this.uiState.selected_orderline_uuid) {
            this.uiState.selected_orderline_uuid = undefined;
        }
    }

    /* ---- Payment Lines --- */
    add_paymentline(payment_method) {
        this.assert_editable();
        if (this.electronic_payment_in_progress()) {
            return false;
        } else {
            const newPaymentline = this.models["pos.payment"].create({
                pos_order_id: this,
                payment_method_id: payment_method,
            });

            this.select_paymentline(newPaymentline);
            if (this.config.cash_rounding) {
                newPaymentline.set_amount(0);
            }
            newPaymentline.set_amount(this.get_due());

            if (
                payment_method.payment_terminal ||
                payment_method.payment_method_type === "qr_code"
            ) {
                newPaymentline.set_payment_status("pending");
            }
            return newPaymentline;
        }
    }

    get_paymentline_by_uuid(uuid) {
        var lines = this.payment_ids;
        return lines.find(function (line) {
            return line.uuid === uuid;
        });
    }

    remove_paymentline(line) {
        this.assert_editable();

        if (this.get_selected_paymentline() === line) {
            this.select_paymentline(undefined);
        }

        line.delete({ backend: true });
    }

    clean_empty_paymentlines() {
        const lines = this.payment_ids;
        const empty = [];

        for (const line of lines) {
            if (!line.get_amount()) {
                empty.push(line);
            }
        }

        for (const em of empty) {
            this.remove_paymentline(em);
        }
    }

    select_paymentline(line) {
        if (line) {
            this.uiState.selected_paymentline_uuid = line?.uuid;
        } else {
            this.uiState.selected_paymentline_uuid = undefined;
        }
    }

    electronic_payment_in_progress() {
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
    stop_electronic_payment() {
        const lines = this.payment_ids;
        const line = lines.find(function (line) {
            var status = line.get_payment_status();
            return (
                status && !["done", "reversed", "reversing", "pending", "retry"].includes(status)
            );
        });

        if (line) {
            line.set_payment_status("waitingCancel");
            line.payment_method_id.payment_terminal
                .send_payment_cancel(this, line.uuid)
                .finally(function () {
                    line.set_payment_status("retry");
                });
        }
    }

    /* ---- Payment Status --- */
    get_subtotal() {
        return roundPrecision(
            this.lines.reduce(function (sum, orderLine) {
                return sum + orderLine.get_display_price();
            }, 0),
            this.currency.rounding
        );
    }

    get_total_with_tax() {
        return this.get_total_with_tax_of_lines(this.lines);
    }

    get_total_with_tax_of_lines(lines) {
        return this.get_total_without_tax_of_lines(lines) + this.get_total_tax_of_lines(lines);
    }

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
    }

    _get_ignored_product_ids_total_discount() {
        return [];
    }

    _reduce_total_discount_callback(sum, orderLine) {
        let discountUnitPrice =
            orderLine.getUnitDisplayPriceBeforeDiscount() * (orderLine.get_discount() / 100);
        if (orderLine.display_discount_policy() === "without_discount") {
            discountUnitPrice +=
                orderLine.get_taxed_lst_unit_price() -
                orderLine.getUnitDisplayPriceBeforeDiscount();
        }
        return sum + discountUnitPrice * orderLine.get_quantity();
    }

    get_total_discount() {
        const ignored_product_ids = this._get_ignored_product_ids_total_discount();
        return roundPrecision(
            this.lines.reduce((sum, orderLine) => {
                if (!ignored_product_ids.includes(orderLine.product_id.id)) {
                    sum +=
                        orderLine.get_all_prices().priceWithTaxBeforeDiscount -
                        orderLine.get_all_prices().priceWithTax;
                    if (orderLine.display_discount_policy() === "without_discount") {
                        sum +=
                            (orderLine.get_taxed_lst_unit_price() -
                                orderLine.getUnitDisplayPriceBeforeDiscount()) *
                            orderLine.get_quantity();
                    }
                }
                return sum;
            }, 0),
            this.currency.rounding
        );
    }

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
    }

    get_total_paid() {
        return roundPrecision(
            this.payment_ids.reduce(function (sum, paymentLine) {
                if (paymentLine.is_done()) {
                    sum += paymentLine.get_amount();
                }
                return sum;
            }, 0),
            this.currency.rounding
        );
    }

    getTotalDue() {
        return this.get_total_with_tax() + this.get_rounding_applied();
    }

    get_tax_details() {
        return this.get_tax_details_of_lines(this.lines);
    }

    get_tax_details_of_lines(lines) {
        const taxDetails = {};
        for (const line of lines) {
            for (const taxData of line.get_all_prices().taxesData) {
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

    // FIXME tax_id is an array of number ?
    get_total_for_taxes(tax_id) {
        let total = 0;

        if (!(tax_id instanceof Array)) {
            tax_id = [tax_id];
        }

        const tax_set = {};

        for (var i = 0; i < tax_id.length; i++) {
            tax_set[tax_id[i]] = true;
        }

        this.lines.forEach((line) => {
            var taxes_ids = this.tax_ids || line.get_product().taxes_id;
            for (var i = 0; i < taxes_ids.length; i++) {
                if (tax_set[taxes_ids[i]]) {
                    total += line.get_price_with_tax();
                    return;
                }
            }
        });

        return total;
    }

    get_change(paymentline) {
        if (!paymentline) {
            var change =
                this.get_total_paid() - this.get_total_with_tax() - this.get_rounding_applied();
        } else {
            change = -this.get_total_with_tax();
            var lines = this.payment_ids;
            for (var i = 0; i < lines.length; i++) {
                change += lines[i].get_amount();
                if (lines[i] === paymentline) {
                    break;
                }
            }
        }
        return roundPrecision(Math.max(0, change), this.currency.rounding);
    }

    get_due(paymentline) {
        let due = 0;
        if (!paymentline) {
            due = this.get_total_with_tax() - this.get_total_paid() + this.get_rounding_applied();
        } else {
            due = this.get_total_with_tax();

            for (const payment of this.payment_ids) {
                if (payment.uuid !== paymentline.uuid) {
                    due -= payment.get_amount();
                }
            }
        }
        return roundPrecision(due, this.currency.rounding);
    }

    get_rounding_applied() {
        if (this.config.cash_rounding) {
            const only_cash = this.config.only_round_cash_method;
            const paymentlines = this.payment_ids;
            const last_line = paymentlines ? paymentlines[paymentlines.length - 1] : false;
            const last_line_is_cash = last_line
                ? last_line.payment_method_id.is_cash_count == true
                : false;
            if (!only_cash || (only_cash && last_line_is_cash)) {
                var rounding_method = this.config.rounding_method.rounding_method;
                var remaining = this.get_total_with_tax() - this.get_total_paid();
                var sign = this.get_total_with_tax() > 0 ? 1.0 : -1.0;
                if (
                    ((this.get_total_with_tax() < 0 && remaining > 0) ||
                        (this.get_total_with_tax() > 0 && remaining < 0)) &&
                    rounding_method !== "HALF-UP"
                ) {
                    rounding_method = rounding_method === "UP" ? "DOWN" : "UP";
                }

                remaining *= sign;
                var total = roundPrecision(remaining, this.config.rounding_method.rounding);
                var rounding_applied = total - remaining;

                // because floor and ceil doesn't include decimals in calculation, we reuse the value of the half-up and adapt it.
                if (floatIsZero(rounding_applied, this.currency.decimal_places)) {
                    // https://xkcd.com/217/
                    return 0;
                } else if (
                    Math.abs(this.get_total_with_tax()) < this.config.rounding_method.rounding
                ) {
                    return 0;
                } else if (rounding_method === "UP" && rounding_applied < 0 && remaining > 0) {
                    rounding_applied += this.config.rounding_method.rounding;
                } else if (rounding_method === "UP" && rounding_applied > 0 && remaining < 0) {
                    rounding_applied -= this.config.rounding_method.rounding;
                } else if (rounding_method === "DOWN" && rounding_applied > 0 && remaining > 0) {
                    rounding_applied -= this.config.rounding_method.rounding;
                } else if (rounding_method === "DOWN" && rounding_applied < 0 && remaining < 0) {
                    rounding_applied += this.config.rounding_method.rounding;
                } else if (
                    rounding_method === "HALF-UP" &&
                    rounding_applied === this.config.rounding_method.rounding / -2
                ) {
                    rounding_applied += this.config.rounding_method.rounding;
                }
                return sign * rounding_applied;
            } else {
                return 0;
            }
        }
        return 0;
    }

    has_not_valid_rounding() {
        if (
            !this.config.rounding_method ||
            this.get_total_with_tax() < this.config.rounding_method.rounding
        ) {
            return false;
        }

        const only_cash = this.config.only_round_cash_method;
        const lines = this.payment_ids;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (only_cash && !line.payment_method_id.is_cash_count) {
                continue;
            }

            if (
                !floatIsZero(
                    line.amount - roundPrecision(line.amount, this.config.rounding_method.rounding),
                    6
                )
            ) {
                return line;
            }
        }
        return false;
    }

    is_paid() {
        return this.get_due() <= 0;
    }

    is_paid_with_cash() {
        return !!this.payment_ids.find(function (pl) {
            return pl.payment_method_id.is_cash_count;
        });
    }

    check_paymentlines_rounding() {
        if (this.config.cash_rounding) {
            var cash_rounding = this.config.rounding_method.rounding;
            var default_rounding = this.currency.rounding;
            for (var id in this.payment_ids) {
                const line = this.payment_ids[id];
                const diff = roundPrecision(
                    roundPrecision(line.amount, cash_rounding) -
                        roundPrecision(line.amount, default_rounding),
                    default_rounding
                );
                if (this.get_total_with_tax() < this.config.rounding_method.rounding) {
                    return true;
                }
                if (diff && line.payment_method_id.is_cash_count) {
                    return false;
                } else if (!this.config.only_round_cash_method && diff) {
                    return false;
                }
            }
            return true;
        }
        return true;
    }

    get_total_cost() {
        return this.lines.reduce(function (sum, orderLine) {
            return sum + orderLine.get_total_cost();
        }, 0);
    }

    /* ---- Invoice --- */
    set_to_invoice(to_invoice) {
        this.assert_editable();
        this.to_invoice = to_invoice;
    }

    // FIXME remove this
    is_to_invoice() {
        return this.to_invoice;
    }

    /* ---- Partner --- */
    // the partner related to the current order.
    set_partner(partner) {
        this.assert_editable();
        this.update({ partner_id: partner });
        this.updatePricelistAndFiscalPosition(partner);
    }

    get_partner() {
        return this.partner_id;
    }

    get_partner_name() {
        return this.partner_id ? this.partner_id.name : "";
    }

    get_cardholder_name() {
        const card_payment_line = this.payment_ids.find((pl) => pl.cardholder_name);
        return card_payment_line ? card_payment_line.cardholder_name : "";
    }

    /* ---- Screen Status --- */
    // the order also stores the screen status, as the PoS supports
    // different active screens per order. This method is used to
    // store the screen status.
    set_screen_data(value) {
        this.uiState.screen_data["value"] = value;
    }

    get_current_screen_data() {
        return this.uiState.screen_data["value"] ?? { name: "ProductScreen" };
    }

    //see set_screen_data
    get_screen_data() {
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

    wait_for_push_order() {
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

        this.set_pricelist(newPartnerPricelist);
        this.update({ fiscal_position_id: newPartnerFiscalPosition });
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
    get_orderlines() {
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
            amount: formatCurrency(this.get_total_with_tax() || 0),
            paymentLines: this.payment_ids.map((pl) => ({
                name: pl.payment_method_id.name,
                amount: formatCurrency(pl.get_amount()),
            })),
            change: this.get_change() && formatCurrency(this.get_change()),
            generalNote: this.general_note || "",
        };
    }
    getFloatingOrderName() {
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
        return this.getFloatingOrderName() || "";
    }
}

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
