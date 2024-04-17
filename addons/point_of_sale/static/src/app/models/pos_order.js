/** @odoo-module */
import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { _t } from "@web/core/l10n/translation";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { omit } from "@web/core/utils/objects";
import { qrCodeSrc, random5Chars, uuidv4 } from "@point_of_sale/utils";
import { renderToElement } from "@web/core/utils/render";
import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { computeComboLines } from "./utils/compute_combo_lines";
import { changesToOrder } from "./utils/order_change";

const { DateTime } = luxon;

export class PosOrder extends Base {
    static pythonModel = "pos.order";

    setup(vals) {
        super.setup(vals);

        // Data present in python model
        this.date_order = vals.date_order || luxon.DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss");
        this.to_invoice = vals.to_invoice || false;
        this.shipping_date = vals.shipping_date || false;
        this.state = vals.state || "draft";
        this.uuid = vals.uuid ? vals.uuid : uuidv4();
        this.last_order_preparation_change = vals.last_order_preparation_change
            ? JSON.parse(vals.last_order_preparation_change)
            : {};

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

    getEmailItems() {
        return [_t("the receipt")].concat(this.is_to_invoice() ? [_t("the invoice")] : []);
    }

    export_for_printing(baseUrl, headerData) {
        const paymentlines = this.payment_ids
            .filter((p) => !p.is_change)
            .map((p) => p.export_for_printing());
        this.receiptDate ||= formatDateTime(luxon.DateTime.now());
        return {
            orderlines: this.lines.map((l) => omit(l.getDisplayData(), "internalNote")),
            paymentlines,
            amount_total: this.get_total_with_tax(),
            total_without_tax: this.get_total_without_tax(),
            amount_tax: this.get_total_tax(),
            total_paid: this.get_total_paid(),
            total_discount: this.get_total_discount(),
            rounding_applied: this.get_rounding_applied(),
            tax_details: this.get_tax_details(),
            change: this.uiState.locked ? this.amount_return : this.get_change(),
            name: this.name,
            invoice_id: null, //TODO
            cashier: this.employee_id?.name || this.user_id?.name,
            date: this.receiptDate,
            pos_qr_code:
                this.company.point_of_sale_use_ticket_qr_code &&
                this.finalized &&
                qrCodeSrc(`${baseUrl}/pos/ticket/validate?access_token=${this.access_token}`),
            ticket_code:
                this.company.point_of_sale_ticket_unique_code && this.finalized && this.ticketCode,
            base_url: baseUrl,
            footer: this.config.receipt_footer,
            // FIXME: isn't there a better way to handle this date?
            shippingDate:
                this.shipping_date && formatDate(DateTime.fromJSDate(new Date(this.shipping_date))),
            headerData: {
                ...headerData,
                trackingNumber: this.tracking_number,
            },
        };
    }
    canPay() {
        return this.lines.length;
    }
    recomputeOrderData() {
        this.amount_paid = this.get_total_paid();
        this.amount_tax = this.get_total_tax();
        this.amount_total = this.get_total_with_tax();
        this.amount_return = this.get_change();
    }

    // NOTE args added [unwatchedPrinter]
    async printChanges(skipped = false, orderPreparationCategories, cancelled, unwatchedPrinter) {
        const orderChange = changesToOrder(this, skipped, orderPreparationCategories, cancelled);
        const d = new Date();

        let isPrintSuccessful = true;

        let hours = "" + d.getHours();
        hours = hours.length < 2 ? "0" + hours : hours;

        let minutes = "" + d.getMinutes();
        minutes = minutes.length < 2 ? "0" + minutes : minutes;

        orderChange.new.sort((a, b) => {
            const sequenceA = a.pos_categ_sequence;
            const sequenceB = b.pos_categ_sequence;
            if (sequenceA === 0 && sequenceB === 0) {
                return a.pos_categ_id - b.pos_categ_id;
            }

            return sequenceA - sequenceB;
        });

        for (const printer of unwatchedPrinter) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids,
                orderChange
            );
            if (changes["new"].length > 0 || changes["cancelled"].length > 0) {
                const printingChanges = {
                    new: changes["new"],
                    cancelled: changes["cancelled"],
                    table_name: this.config.module_pos_restaurant ? this.table_id.name : false,
                    floor_name: this.config.module_pos_restaurant
                        ? this.table_id.floor_id.name
                        : false,
                    name: this.name || "unknown order",
                    time: {
                        hours,
                        minutes,
                    },
                };
                const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
                    changes: printingChanges,
                });
                const result = await printer.printReceipt(receipt);
                if (!result.successful) {
                    isPrintSuccessful = false;
                }
            }
        }

        return isPrintSuccessful;
    }

    get isBooked() {
        return this.uiState.booked || !this.is_empty() || typeof this.id === "number";
    }

    _getPrintingCategoriesChanges(categories, currentOrderChange) {
        const filterFn = (change) => {
            const product = this.models["product.product"].get(change["product_id"]);
            const categoryIds = product.parentPosCategIds;

            for (const categoryId of categoryIds) {
                if (categories.includes(categoryId)) {
                    return true;
                }
            }
        };

        return {
            new: currentOrderChange["new"].filter(filterFn),
            cancelled: currentOrderChange["cancelled"].filter(filterFn),
        };
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
                const note = line.getNote();
                const lineKey = `${line.uuid} - ${note}`;
                orderlineIdx.push(lineKey);

                if (this.last_order_preparation_change[lineKey]) {
                    this.last_order_preparation_change[lineKey]["quantity"] = line.get_quantity();
                } else {
                    this.last_order_preparation_change[lineKey] = {
                        attribute_value_ids: line.attribute_value_ids.map((a) =>
                            a.serialize({ orm: true })
                        ),
                        line_uuid: line.uuid,
                        product_id: line.get_product().id,
                        name: line.get_full_product_name(),
                        note: note,
                        quantity: line.get_quantity(),
                    };
                }
                line.setHasChange(false);
            }
        });

        // Checks whether an orderline has been deleted from the order since it
        // was last sent to the preparation tools. If so we delete it to the changes.
        for (const lineKey in this.last_order_preparation_change) {
            if (!this.getOrderedLine(lineKey)) {
                delete this.last_order_preparation_change[lineKey];
            }
        }
    }

    getOrderedLine(lineKey) {
        return this.lines.find(
            (line) =>
                line.uuid === this.last_order_preparation_change[lineKey]["line_uuid"] &&
                line.note === this.last_order_preparation_change[lineKey]["note"]
        );
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
                line.uiState.price_type === "original" &&
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
            (line) => line.uiState.price_type === "original" && line.combo_line_ids?.length
        );
        for (const pLine of combo_parent_lines) {
            attributes_prices[pLine.id] = computeComboLines(
                pLine.product_id,
                pLine.combo_line_ids.map((cLine) => {
                    if (cLine.attribute_value_ids) {
                        return {
                            combo_line_id: cLine.combo_line_id,
                            configuration: {
                                attribute_value_ids: cLine.attribute_value_ids,
                            },
                        };
                    } else {
                        return { combo_line_id: cLine.combo_line_id };
                    }
                }),
                pricelist,
                this.models["decimal.precision"].getAll(),
                this.models["product.template.attribute.value"].getAllBy("id")
            );
        }
        const combo_children_lines = this.lines.filter(
            (line) => line.uiState.price_type === "original" && line.combo_parent_id
        );
        combo_children_lines.forEach((line) => {
            line.set_unit_price(
                attributes_prices[line.combo_parent_id.id].find(
                    (item) => item.combo_line_id.id === line.combo_line_id.id
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
        const selected = this.lines.find(
            (line) => line.uuid === this.uiState.selected_orderline_uuid
        );

        if (!selected && this.lines.length > 0) {
            this.select_orderline(this.get_last_orderline());
        }

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

        line.delete();
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
        return this.get_total_without_tax() + this.get_total_tax();
    }

    get_total_without_tax() {
        return roundPrecision(
            this.lines.reduce(function (sum, line) {
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
                        orderLine.getUnitDisplayPriceBeforeDiscount() *
                        (orderLine.get_discount() / 100) *
                        orderLine.get_quantity();
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

    get_tax_details() {
        const taxDetails = {};
        for (const line of this.lines) {
            for (const taxData of line.get_all_prices().taxesData) {
                const taxId = taxData.id;
                if (!taxDetails[taxId]) {
                    taxDetails[taxId] = Object.assign({}, taxData, {
                        amount: 0.0,
                        base: 0.0,
                        tax_percentage: taxData.amount,
                    });
                }
                taxDetails[taxId].base += taxData.display_base;
                taxDetails[taxId].amount += taxData.tax_amount_factorized;
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
        return this.get_due() <= 0 && this.check_paymentlines_rounding();
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
}

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
