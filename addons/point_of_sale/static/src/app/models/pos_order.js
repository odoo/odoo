import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { computeComboItems } from "./utils/compute_combo_items";
import { localization } from "@web/core/l10n/localization";
import { formatDate, serializeDateTime } from "@web/core/l10n/dates";
import { PosOrderAccounting } from "./accounting/pos_order_accounting";

const { DateTime } = luxon;

export class PosOrder extends PosOrderAccounting {
    static pythonModel = "pos.order";

    setup(vals) {
        super.setup(vals);

        if (!this.session_id?.id && (!this.finalized || !this.isSynced)) {
            this.session_id = this.session;
        }

        // Data present in python model
        this.name = vals.name || "/";
        this.nb_print = vals.nb_print || 0;
        this.to_invoice = vals.to_invoice || false;
        this.setShippingDate(vals.shipping_date);
        this.state = vals.state || "draft";

        if (!vals.last_order_preparation_change) {
            this.last_order_preparation_change = {
                lines: {},
                metadata: {},
                general_customer_note: "",
                internal_note: "",
                sittingMode: 0,
            };
        } else {
            this.last_order_preparation_change =
                typeof vals.last_order_preparation_change === "object"
                    ? vals.last_order_preparation_change
                    : JSON.parse(vals.last_order_preparation_change);
        }

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
            lastPrints: [],
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
        return this.finalized && !this.isSynced;
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
            this.lines.forEach((l) => l.setQuantity(-Math.abs(l.getQuantity()), true));
        }
    }

    getCashierName() {
        return this.user_id?.name?.split(" ").at(0);
    }
    canPay() {
        return this.lines.length;
    }

    get isBooked() {
        return Boolean(this.uiState.booked || !this.isEmpty() || this.isSynced);
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
            orderlineIdx.push(line.preparationKey);

            if (this.last_order_preparation_change.lines[line.preparationKey]) {
                this.last_order_preparation_change.lines[line.preparationKey] = {
                    ...this.last_order_preparation_change.lines[line.preparationKey],
                    quantity: line.getQuantity(),
                    note: line.getNote(),
                    customer_note: line.getCustomerNote(),
                };
            } else {
                this.last_order_preparation_change.lines[line.preparationKey] = {
                    attribute_value_names: line.attribute_value_ids.map((a) => a.name),
                    uuid: line.uuid,
                    isCombo: Boolean(line?.combo_line_ids?.length),
                    combo_parent_uuid: line?.combo_parent_id?.uuid,
                    product_id: line.getProduct().id,
                    name: line.getFullProductName(),
                    basic_name: line.getProduct().name,
                    display_name: line.getProduct().display_name,
                    note: line.getNote(),
                    quantity: line.getQuantity(),
                    customer_note: line.getCustomerNote(),
                };
            }
            line.setHasChange(false);
            line.uiState.savedQuantity = line.getQuantity();
        });
        // Checks whether an orderline has been deleted from the order since it
        // was last sent to the preparation tools or updated. If so we delete older changes.
        for (const [key, change] of Object.entries(this.last_order_preparation_change.lines)) {
            const orderline = this.models["pos.order.line"].getBy("uuid", change.uuid);
            const lineNote = orderline?.note;
            const changeNote = change?.note;
            if (!orderline || (lineNote && changeNote && changeNote.trim() !== lineNote.trim())) {
                delete this.last_order_preparation_change.lines[key];
            }
        }
        this.last_order_preparation_change.general_customer_note = this.general_customer_note;
        this.last_order_preparation_change.internal_note = this.internal_note;
        this.last_order_preparation_change.sittingMode = this.preset_id?.id || 0;
        this.last_order_preparation_change.metadata = {
            serverDate: serializeDateTime(DateTime.now()),
        };
        this._markDirty();
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
                    return line.prices.total_excluded_currency;
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
            const { childLineFree, childLineExtra } = this.getFreeAndExtraChildLines(pLine);
            attributes_prices[pLine.id] = computeComboItems(
                pLine.product_id,
                childLineFree,
                pricelist,
                this.models["decimal.precision"].getAll(),
                this.models["product.template.attribute.value"].getAllBy("id"),
                childLineExtra,
                this.config_id.currency_id
            );
        }
        const combo_children_lines = this.lines.filter(
            (line) => line.price_type === "original" && line.combo_parent_id
        );
        combo_children_lines.forEach((line) => {
            const currentItem = attributes_prices[line.combo_parent_id.id].find(
                (item) => item.combo_item_id.id === line.combo_item_id.id
            );
            line.setUnitPrice(currentItem.price_unit);
            // Removing to be able to have extras that are the same as free products
            attributes_prices[line.combo_parent_id.id].splice(
                attributes_prices[line.combo_parent_id.id].indexOf(currentItem),
                1
            );
        });
    }

    getFreeAndExtraChildLines(pLine) {
        const childLineFree = [];
        const childLineExtra = [];
        const comboRemainingFree = {};
        for (const cLine of pLine.combo_line_ids) {
            if (!(cLine.combo_item_id.combo_id.id in comboRemainingFree)) {
                comboRemainingFree[cLine.combo_item_id.combo_id.id] =
                    cLine.combo_item_id.combo_id.qty_free;
            }
            const newQty = comboRemainingFree[cLine.combo_item_id.combo_id.id] - cLine.qty;
            const baseData = { combo_item_id: cLine.combo_item_id };
            if (cLine.attribute_value_ids) {
                baseData.configuration = { attribute_value_ids: cLine.attribute_value_ids };
            }
            if (cLine.qty) {
                if (newQty >= 0) {
                    comboRemainingFree[cLine.combo_item_id.combo_id.id] = newQty;
                    childLineFree.push({ ...baseData, qty: cLine.qty });
                } else {
                    childLineExtra.push({ ...baseData, qty: cLine.qty });
                }
            }
        }
        return { childLineFree, childLineExtra };
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
        const existingCash = this.payment_ids.find((pl) => pl.payment_method_id.is_cash_count);

        if (this.electronicPaymentInProgress()) {
            return {
                status: false,
                data: _t("There is already an electronic payment in progress."),
            };
        }

        if (existingCash && payment_method.is_cash_count) {
            return { status: false, data: _t("There is already a cash payment line.") };
        }

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
        return { status: true, data: newPaymentLine };
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

    _getIgnoredProductIdsTotalDiscount() {
        return [];
    }

    getTotalDiscount() {
        const ignored_product_ids = this._getIgnoredProductIdsTotalDiscount();
        return this.currency.round(
            this.lines.reduce((sum, orderLine) => {
                if (!ignored_product_ids.includes(orderLine.product_id.id)) {
                    const data = orderLine.order_id.prices.baseLineByLineUuids[orderLine.uuid];
                    sum += data.tax_details.discount_amount;
                    if (
                        orderLine.displayDiscountPolicy() === "without_discount" &&
                        !(orderLine.price_type === "manual") &&
                        orderLine.discount == 0
                    ) {
                        sum +=
                            (orderLine.displayPriceUnit - orderLine.displayPriceUnitNoDiscount) *
                            orderLine.getQuantity();
                    }
                }
                return sum;
            }, 0)
        );
    }

    isPaid() {
        return this.orderHasZeroRemaining;
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

    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (
            data.last_order_preparation_change &&
            typeof data.last_order_preparation_change === "object"
        ) {
            data.last_order_preparation_change = JSON.stringify(data.last_order_preparation_change);
        }
        return data;
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

    get discountLines() {
        return this.lines?.filter(
            (line) => line.product_id.id === this.config.discount_product_id?.id
        );
    }

    get globalDiscountPc() {
        return this.discountLines?.[0]?.extra_tax_data?.discount_percentage || 0;
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

    get showChange() {
        return !this.currency.isZero(this.change) && this.finalized;
    }

    getLinesToCompute() {
        return this.lines.filter(
            (line) =>
                line.price_type === "original" &&
                !(line.combo_line_ids?.length || line.combo_parent_id)
        );
    }
}

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
