import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { computeComboItems } from "./utils/compute_combo_items";
import { PosOrderAccounting } from "./accounting/pos_order_accounting";
import { getStrNotes } from "./utils/order_change";
import { accountTaxHelpers } from "@account/helpers/account_tax";

const { DateTime } = luxon;

export class PosOrder extends PosOrderAccounting {
    static pythonModel = "pos.order";
    static excludedLazyGetters = [
        "user",
        "company",
        "currency",
        "pickingType",
        "session",
        "finalized",
        "isUnsyncedPaid",
        "originalSplittedOrder",
        "isRefund",
        "floatingOrderName",
    ];

    setup(vals) {
        super.setup(vals);

        if (!this.session_id?.id && (!this.finalized || !this.isSynced)) {
            this.session_id = this.session;
        }

        // Data present in python model
        this.name = vals.name || "/";
        this.nb_print = vals.nb_print || 0;
        this.to_invoice = vals.to_invoice || false;
        this.state = vals.state || "draft";

        this.general_customer_note = vals.general_customer_note || "";
        this.internal_note = vals.internal_note || "";

        if (!this.date_order) {
            this.date_order = DateTime.now();
        }
        if (!this.user_id && this.models["res.users"]) {
            this.user_id = this.user;
        }

        if (!this.config_id) {
            this.config_id = this.config;
        }
    }

    initState() {
        super.initState();
        // !!Keep all uiState in one object!!
        this.uiState = {
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
            tip: { value: false, type: false },
            last_general_customer_note: this.general_customer_note || "",
            last_internal_note: this.internal_note || "",
        };
    }

    get user() {
        return this.models["res.users"].getFirst();
    }

    get company() {
        return this.config.company_id;
    }

    get config() {
        return this.models["pos.config"].get(odoo.pos_config_id);
    }

    get currency() {
        return this.config.currency_id;
    }

    get session() {
        return this.models["pos.session"].get(odoo.pos_session_id);
    }

    get finalized() {
        return this.state !== "draft";
    }

    get canBeRemovedFromIndexedDB() {
        return (this.finalized && this.isSynced) || this.state === "cancel";
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
        return this.formatDateOrTime("preset_time", "date");
    }

    get isFutureDate() {
        return this.preset_time?.startOf("day") > DateTime.now().startOf("day");
    }

    get presetTime() {
        return this.preset_time && this.preset_time.isValid
            ? this.formatDateOrTime("preset_time", "time")
            : false;
    }

    get invoiceName() {
        return this.account_move?.name || "";
    }

    get presetDateTime() {
        return this.preset_time?.isValid
            ? this.preset_time.hasSame(this.date_order, "day")
                ? this.formatDateOrTime("preset_time", "time")
                : this.formatDateOrTime("preset_time")
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

    get adjustableTipLine() {
        return this.payment_ids.find((p) => p.canBeAdjusted());
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

    isEmpty() {
        return this.lines.length === 0;
    }

    isEmptyOrder() {
        return this.getOrderlines().length === 0 && this.payment_ids.length === 0;
    }

    updateSavedQuantity() {
        this.lines.forEach((line) => line.updateSavedQuantity());
    }

    assertEditable() {
        if (this.finalized && (this.nb_print || this.state == "done")) {
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

    setTip(amount, tipType, tipValue) {
        this.is_tipped = !!amount;
        this.tip_amount = amount || false;
        this.uiState.tip.type = tipType || false;
        this.uiState.tip.value = tipValue || amount || false;
    }

    setPricelist(pricelist) {
        this.pricelist_id = pricelist ? pricelist : false;
        const lines_to_recompute = this.getLinesToCompute();
        for (const line of lines_to_recompute) {
            this.setLinePriceFromPriceList(line, pricelist);
        }
        const attributes_prices = {};
        const combo_parent_lines = this.lines.filter(
            (line) => line.price_type === "original" && line.combo_line_ids?.length
        );
        for (const pLine of combo_parent_lines) {
            const { childLineFree, childLineExtra } = this.getFreeAndExtraChildLines(pLine);
            attributes_prices[pLine.uuid] = computeComboItems(
                pLine.product_id,
                childLineFree,
                pricelist,
                this.models["decimal.precision"].getAll(),
                this.models["product.template.attribute.value"].getAllBy("id"),
                childLineExtra,
                this.currency
            );
        }
        const combo_children_lines = this.lines.filter(
            (line) => line.price_type === "original" && line.combo_parent_id
        );
        combo_children_lines.forEach((line) => {
            const currentItem = attributes_prices[line.combo_parent_id.uuid].find(
                (item) => item.combo_item_id.id === line.combo_item_id.id
            );
            line.setUnitPrice(currentItem.price_unit);
            // Removing to be able to have extras that are the same as free products
            attributes_prices[line.combo_parent_id.uuid].splice(
                attributes_prices[line.combo_parent_id.uuid].indexOf(currentItem),
                1
            );
        });
    }

    setLinePriceFromPriceList(line, pricelist) {
        const newPrice = line.product_id.product_tmpl_id.getPrice(
            pricelist,
            line.getQuantity(),
            line.getPriceExtra(),
            false,
            line.product_id
        );
        line.setUnitPrice(newPrice);
    }

    getFreeAndExtraChildLines(pLine) {
        const childLineFree = [];
        const childLineExtra = [];
        const comboRemainingFree = {};
        const parentQty = pLine.getQuantity() || 1;

        for (const cLine of pLine.combo_line_ids) {
            const comboId = cLine.combo_item_id.combo_id.id;

            if (!(comboId in comboRemainingFree)) {
                comboRemainingFree[comboId] = cLine.combo_item_id.combo_id.qty_free * parentQty;
            }

            const childQty = cLine.getQuantity();
            if (childQty <= 0) {
                continue;
            }

            const newQty = comboRemainingFree[comboId] - childQty;
            const baseData = { combo_item_id: cLine.combo_item_id };

            if (cLine.attribute_value_ids) {
                baseData.configuration = { attribute_value_ids: cLine.attribute_value_ids };
            }

            if (newQty >= 0) {
                comboRemainingFree[comboId] = newQty;
                childLineFree.push({ ...baseData, qty: childQty / parentQty });
            } else {
                childLineExtra.push({ ...baseData, qty: childQty / parentQty });
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
    removeOrderline(line, deep = true) {
        // Remove tip
        if (this.config.iface_tipproduct && this.config.tip_product_id.id === line.product_id.id) {
            this.setTip(false);
        }

        let linesToRemove = [];
        if (deep) {
            linesToRemove = line.getAllLinesInCombo();
        } else {
            linesToRemove = [line];
        }

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
    addPaymentline(payment_method, args = {}) {
        this.assertEditable();

        const { status: canSend, message } = payment_method.getPaymentInterfaceStates();
        if (!canSend) {
            return { status: false, data: message };
        }
        const totalAmountDue = this.getDefaultAmountDueToPayIn(payment_method);
        const newPaymentLine = this.models["pos.payment"].create({
            pos_order_id: this,
            payment_method_id: payment_method,
        });
        this.selectPaymentline(newPaymentLine);
        newPaymentLine.setAmount(totalAmountDue);

        if ((payment_method.payment_interface && !this.isRefund) || payment_method.useBankQrCode) {
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
        this.uiState.selected_paymentline_uuid = line?.uuid;
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

    toBeValidate() {
        // Return true if order has payment lines and no due is remaining.
        if (this.payment_ids.length > 0) {
            return this.orderHasZeroRemaining;
        }
        // Check if multiple payment methods are configured.
        return this.config_id.payment_method_ids.length;
    }

    isRefundInProcess() {
        return (
            this.isRefund &&
            this.payment_ids.some((pl) => pl.payment_provider && pl.payment_status !== "done")
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

    findFiscalPosition(fiscalPosition) {
        if (fiscalPosition) {
            return this.models["account.fiscal.position"].find(
                (position) => position.id === fiscalPosition.id
            );
        }
        return false;
    }

    updatePricelistAndFiscalPosition(newPartner) {
        let newPartnerPricelist, newPartnerFiscalPosition;
        const defaultFiscalPosition = this.models["account.fiscal.position"].find(
            (position) => position.id === this.config.default_fiscal_position_id?.id
        );

        if (newPartner) {
            newPartnerFiscalPosition =
                this.findFiscalPosition(newPartner.fiscal_position_id) || defaultFiscalPosition;
            newPartnerPricelist =
                this.config.available_pricelist_ids.find(
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
        return this.toBeValidate() && this._isValidEmptyOrder() && !this.isCustomerRequired;
    }

    // NOTE: Overrided in pos_loyalty to put loyalty rewards at this end of array.
    getOrderlines() {
        const regularLines = [];
        const serviceFeeLines = [];
        for (const line of this.lines) {
            (line.isServiceFeeLine() ? serviceFeeLines : regularLines).push(line);
        }
        return [...regularLines, ...serviceFeeLines];
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
        return {
            value: this.discountLines?.[0]?.extra_tax_data?.discount_value || 0,
            type: this.discountLines?.[0]?.extra_tax_data?.discount_type || "",
        };
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

    get lastPrints() {
        return this.print_history || [];
    }
    pushLastPrints(data) {
        if (!this.print_history) {
            this.print_history = [];
        }
        this.print_history.push({
            addedQuantity: data.addedQuantity,
            noteChange: data.noteChange,
            noteUpdate: data.noteUpdate,
            removedQuantity: data.removedQuantity,
            internal_note: data.internal_note,
            general_customer_note: data.general_customer_note,
        });
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

    get prepLines() {
        return this.prep_order_ids?.flatMap((po) => po.prep_line_ids);
    }
    get preparationCategories() {
        return this.config.preparationCategories;
    }

    dataMaker(prepOrPosLine, quantity) {
        const line = prepOrPosLine.pos_order_line_id || prepOrPosLine;
        const product = line.product_id;
        const attributes = line.attribute_value_ids || [];
        return {
            line: line,
            data: {
                basic_name: line.order_id?.config_id.module_pos_restaurant
                    ? line.product_id.name
                    : line.product_id.display_name,
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
    }

    get preparationChanges() {
        const changes = {
            quantity: 0,
            categoryCount: {},
            addedQuantity: [],
            removedQuantity: [],
            noteUpdate: [],
        };

        const hasPreparationCategory = (product) => {
            if (!product) {
                return false;
            }
            return product.parentPosCategIds.some((id) => this.preparationCategories.has(id));
        };

        const addCategoryCount = (category, delta) => {
            if (!changes.categoryCount[category.id]) {
                changes.categoryCount[category.id] = { name: category.name, count: 0 };
            }
            changes.quantity += Math.abs(delta);
            changes.categoryCount[category.id].count += delta;
        };

        for (const orderline of this.lines) {
            const product = orderline.product_id;
            const category = product.pos_categ_ids.find((c) =>
                this.preparationCategories.has(c.id)
            );
            const shouldCountCategory = category && !orderline.combo_line_ids?.length;
            const hasPrepaCategory =
                hasPreparationCategory(product) ||
                orderline.combo_line_ids?.some((line) => hasPreparationCategory(line.getProduct()));

            if (!hasPrepaCategory) {
                orderline.setHasChange(false);
                continue;
            }

            const quantityDiff = orderline.qty - orderline.prepQty;
            if (quantityDiff !== 0) {
                changes[quantityDiff > 0 ? "addedQuantity" : "removedQuantity"].push(
                    this.dataMaker(orderline, quantityDiff)
                );
                if (shouldCountCategory) {
                    addCategoryCount(category, quantityDiff);
                }
            } else if (orderline.changeNote) {
                changes.noteUpdate.push(this.dataMaker(orderline, orderline.qty));
                if (shouldCountCategory) {
                    changes.categoryCount["noteUpdate"] ??= { name: _t("Note"), count: 0 };
                    changes.categoryCount["noteUpdate"].count += 1;
                }
            }
            orderline.setHasChange(quantityDiff !== 0 || orderline.changeNote);
        }

        // Checks whether an orderline has been deleted from the order since it
        // was last sent to the preparation tools. If so we addthis.prep_order_ids this to the changes.

        const removedOrderlines =
            this.prep_order_ids
                ?.flatMap((o) => o.prep_line_ids)
                .filter((l) => !l.pos_order_line_id && l.quantity > l.cancelled) ?? [];
        const removedByKey = {};

        for (const prepLine of removedOrderlines) {
            const key = keyMaker(prepLine);
            if (!removedByKey[key]) {
                removedByKey[key] = { quantity: 0, prepLine };
            }
            removedByKey[key].quantity += prepLine.quantity - prepLine.cancelled;
        }
        for (const { quantity, prepLine } of Object.values(removedByKey)) {
            if (quantity <= 0) {
                continue;
            }
            const product = prepLine.product_id;
            const category = product.pos_categ_ids.find((c) =>
                this.preparationCategories.has(c.id)
            );
            const lineData = this.dataMaker(prepLine, -quantity);
            changes.removedQuantity.push(lineData);
            if (category && lineData.data.combo_line_ids?.length === 0) {
                addCategoryCount(category, -quantity);
            }
        }

        if (this.uiState.last_general_customer_note !== this.general_customer_note) {
            changes.general_customer_note = this.general_customer_note;
        }

        if (this.uiState.last_internal_note !== this.internal_note) {
            changes.internal_note = this.internal_note;
        }

        const noteCount = ["general_customer_note", "internal_note"].reduce(
            (count, note) => count + (note in changes ? 1 : 0),
            0
        );

        if (noteCount) {
            changes.categoryCount["generalNoteUpdate"] = {
                name: _t("Message"),
                count: noteCount,
            };
        }

        changes.categoryCount = Object.values(changes.categoryCount);

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
            const changes = this.preparationChanges;
            const allChanges = [...changes.addedQuantity, ...changes.removedQuantity];

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
                    let toCancel = -data.quantity;
                    let prepLinesToCancel;
                    if (line.model.name === "pos.order.line") {
                        prepLinesToCancel = line.prep_line_ids;
                    } else {
                        const mainKey = keyMaker(line);
                        prepLinesToCancel = [...this.prepLines].filter(
                            (pl) => !pl.pos_order_line_id && keyMaker(pl) === mainKey
                        );
                    }
                    for (const prepLine of prepLinesToCancel.toReversed()) {
                        const lineQty = prepLine.quantity - prepLine.cancelled;
                        const cancellable = Math.min(lineQty, toCancel);
                        prepLine.cancelled += cancellable;
                        toCancel -= cancellable;
                        if (toCancel <= 0) {
                            break;
                        }
                    }
                }
            }
        }

        // Update last known state to avoid re-sending changes
        this.uiState.last_general_customer_note = this.general_customer_note;
        this.uiState.last_internal_note = this.internal_note;
        this.lines.forEach((line) => {
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
        const changes = this.preparationChanges;
        let addedQuantity = [];
        let removedQuantity = [];
        let noteUpdate = [];
        if (opts.cancelled) {
            removedQuantity = this.lines.map(
                (l) =>
                    this.dataMaker(
                        l,
                        l.prep_line_ids.reduce(
                            (sum, obj) => sum + (obj.quantity - obj.cancelled),
                            0
                        )
                    ).data
            );
        } else {
            addedQuantity = changes.addedQuantity.map((c) => c.data);
            removedQuantity = changes.removedQuantity.map((c) => c.data);
            noteUpdate = changes.noteUpdate.map((c) => c.data);
        }
        return {
            ...changes,
            noteChange: false,
            addedQuantity: addedQuantity,
            removedQuantity: removedQuantity,
            noteUpdate: noteUpdate,
        };
    }

    get serviceFeeLines() {
        return this.lines?.filter((line) => line.isServiceFeeLine());
    }
    removeAllServiceFeeLines() {
        for (const line of this.serviceFeeLines) {
            line.delete();
        }
    }
    recomputeServiceFees() {
        const taxKey = (taxIds) =>
            taxIds
                .map((tax) => tax.id)
                .sort((a, b) => a - b)
                .join("_");

        if (this.state !== "draft") {
            return;
        }

        if (!this.preset_id?.service_fee) {
            this.removeAllServiceFeeLines();
            return;
        }

        const preset = this.preset_id;
        const serviceFeeProduct = preset?.service_fee_product_id;

        const lines = this.getOrderlines();
        const serviceFeeApplicableLines = lines.filter((line) => line.isServiceFeeApplicable());

        if (serviceFeeApplicableLines.length === 0) {
            this.removeAllServiceFeeLines();
            return;
        }

        const serviceFeeLinesMap = {};
        (this.serviceFeeLines || []).forEach((line) => {
            const key = taxKey(line.tax_ids);
            serviceFeeLinesMap[key] = line;
        });

        const baseLines = serviceFeeApplicableLines.map((line) =>
            accountTaxHelpers.prepare_base_line_for_taxes_computation(
                line,
                line.prepareBaseLineForTaxesComputationExtraValues()
            )
        );

        let priceUnit;
        if (preset.service_fee_based_on === "pre_discount") {
            baseLines.forEach((line) => {
                line.discount = 0;
            });
        }

        accountTaxHelpers.add_tax_details_in_base_lines(baseLines, this.company_id);
        accountTaxHelpers.round_base_lines_tax_details(baseLines, this.company_id);
        let amount = preset.service_fee_amount;
        if (preset.service_fee_type === "percent") {
            amount *= 100;
        }
        const serviceFeeBaseLines = accountTaxHelpers.reduce_base_lines_to_target_amount(
            baseLines,
            this.company_id,
            preset.service_fee_type,
            amount,
            {
                grouping_function: (base_line) => ({
                    grouping_key: { product_id: serviceFeeProduct },
                    raw_grouping_key: { product_id: serviceFeeProduct.id },
                }),
            }
        );

        for (const baseLine of serviceFeeBaseLines) {
            const extraTaxData = accountTaxHelpers.export_base_line_extra_tax_data(baseLine);
            const key = taxKey(baseLine.tax_ids);
            const existingLine = serviceFeeLinesMap[key];

            if (existingLine) {
                existingLine.extra_tax_data = extraTaxData;
                existingLine.price_unit = baseLine.price_unit;
                delete serviceFeeLinesMap[key];
            } else {
                priceUnit = baseLine.price_unit;
                this.models["pos.order.line"].create({
                    order_id: this,
                    product_id: serviceFeeProduct,
                    price_unit: priceUnit,
                    tax_ids: [["link", ...baseLine.tax_ids]],
                    product_tmpl_id: serviceFeeProduct.product_tmpl_id,
                    qty: 1,
                    price_type: "manual",
                    // course_id is only available when pos_restaurant is installed
                    course_id: this.hasCourses?.() ? this.getLastCourse() : undefined,
                    extra_tax_data: extraTaxData,
                });
            }
        }

        Object.values(serviceFeeLinesMap).forEach((line) => {
            line.delete();
        });
    }
}

const keyMaker = (prepLine) => {
    const objectKey = {
        product_id: prepLine.product_id.id,
        combo_parent_id: prepLine.combo_parent_id?.id,
        combo_line_ids: prepLine.combo_line_ids.map((c) => c.id).sort(),
        attribute_value_ids: prepLine.attribute_value_ids.map((a) => a.id).sort(),
    };
    return JSON.stringify(objectKey);
};

registry.category("pos_available_models").add(PosOrder.pythonModel, PosOrder);
