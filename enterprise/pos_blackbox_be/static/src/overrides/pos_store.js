import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";

patch(PosStore.prototype, {
    async setup(
        env,
        {
            number_buffer,
            hardware_proxy,
            barcode_reader,
            ui,
            dialog,
            printer,
            bus_service,
            pos_data,
        }
    ) {
        await super.setup(...arguments);
        if (this.useBlackBoxBe()) {
            this.user_session_status = await this.getUserSessionStatus();
        }
        this.multiple_discount = false;
        this.lastBBWarning = false;
    },
    //#region User Status
    async getUserSessionStatus() {
        if (this.useBlackBoxBe()) {
            const cashier = this.get_cashier();
            if (!cashier) {
                return false;
            }
            return await this.data.call(
                "pos.session",
                "get_user_session_work_status",
                [this.session.id],
                {
                    user_id: cashier.id,
                }
            );
        }
        return true;
    },
    async setUserSessionStatus(status) {
        const cashier = this.get_cashier();
        if (!cashier) {
            return;
        }
        const users = await this.data.call(
            "pos.session",
            "set_user_session_work_status",
            [this.session.id],
            {
                user_id: cashier.id,
                status: status,
            }
        );
        if (this.config.module_pos_hr) {
            this.session.employees_clocked_ids = users.map((id) =>
                this.data.models["hr.employee"].get(id)
            );
        } else {
            this.session.users_clocked_ids = users.map((id) =>
                this.data.models["res.users"].get(id)
            );
        }
        this.user_session_status = status;
    },
    checkIfUserClocked(cashier_id = false) {
        if (!cashier_id) {
            cashier_id = this.get_cashier().id;
        }
        if (this.config.module_pos_hr) {
            return this.session.employees_clocked_ids.find(
                (employee) => employee.id === cashier_id
            );
        }
        return this.session.users_clocked_ids.find((user) => user.id === cashier_id);
    },
    //#region User Clocking
    async clock(printer, clock_in = true) {
        if (!this.clock_disabled) {
            try {
                this.clock_disabled = true;
                const order = await this.createOrderForClocking();
                await printer.print(OrderReceipt, {
                    data: this.orderExportForPrinting(order),
                    formatCurrency: (amount) => this.env.utils.formatCurrency(amount),
                });
                this.removeClockOrder(order);
                await this.setUserSessionStatus(clock_in);
            } finally {
                this.clock_disabled = false;
            }
        }
    },
    async createOrderForClocking() {
        if (this.config.module_pos_restaurant) {
            // if the configuration is a restaurant, the first table is selected
            this.selectedTable = this.models["restaurant.table"].getFirst();
        }
        const order = this.add_new_order();
        this.addLineToOrder(
            {
                product_id: this.user_session_status
                    ? this.config.work_out_product
                    : this.config.work_in_product,
            },
            order,
            {},
            false
        );
        try {
            order.uiState.clock = this.user_session_status ? "out" : "in";
            this.addPendingOrder([order.id]);
            order.state = "paid";
            const result = await this.syncAllOrders({ throw: true });
            if (this.config.module_pos_restaurant) {
                this.selectedTable = null;
            }
            return result[0];
        } catch (error) {
            const order = this.get_order();
            this.removeClockOrder(order);
            if (this.config.module_pos_restaurant) {
                this.selectedTable = null;
            }
            throw error;
        }
    },
    removeClockOrder(order) {
        this.removeOrder(order, false);
        this.selectNextOrder();
        if (this.config.module_pos_restaurant) {
            this.showScreen("FloorScreen");
        } else {
            this.showScreen("ProductScreen");
        }
    },
    //#region Override
    async addLineToCurrentOrder(vals, opt = {}, configure = true) {
        const product = vals.product_id;
        if (this.useBlackBoxBe()) {
            if (product.get_price(this.pricelist, opt.quantity || 1, opt.price_extra || 0) < 0) {
                this.dialog.add(AlertDialog, {
                    title: _t("POS error"),
                    body: _t(
                        "It's forbidden to sell product with negative price when using the black box.\nPerform a refund instead."
                    ),
                });
                return;
            } else if (product.taxes_id.length === 0 && !product.combo_ids) {
                this.dialog.add(AlertDialog, {
                    title: _t("POS error"),
                    body: _t("Product has no tax associated with it."),
                });
                return;
            } else if (
                !this.checkIfUserClocked() &&
                product !== this.config.work_in_product &&
                !opt.force
            ) {
                this.dialog.add(AlertDialog, {
                    title: _t("POS error"),
                    body: _t("User must be clocked in."),
                });
                return;
            } else if (
                !product.combo_ids &&
                !product.taxes_id.every((tax) => tax?.tax_group_id.pos_receipt_label)
            ) {
                this.dialog.add(AlertDialog, {
                    title: _t("POS error"),
                    body: _t(
                        "Product has no tax receipt label. Please add one on the tax group of the tax (A, B, C or D)."
                    ),
                });
                return;
            } else if (product.id === this.config.work_in_product.id && !opt.force) {
                this.dialog.add(AlertDialog, {
                    title: _t("POS error"),
                    body: _t("This product is not allowed to be sold"),
                });
                return;
            } else if (product.id === this.config.work_out_product.id && !opt.force) {
                this.dialog.add(AlertDialog, {
                    title: _t("POS error"),
                    body: _t("This product is not allowed to be sold"),
                });
                return;
            }
            const order = this.get_order();
            if (
                order.isValidNegativeOrder() &&
                order.lines.some((line) => line.get_quantity() < 0)
            ) {
                opt.qty_sign = -1;
            }
        }

        return await super.addLineToCurrentOrder(vals, opt, configure);
    },
    async processServerData(loadedData) {
        await super.processServerData(loadedData);

        this.config.work_in_product = this.models["product.product"].get(
            this.session._product_product_work_in
        );
        this.config.work_out_product = this.models["product.product"].get(
            this.session._product_product_work_out
        );
    },
    disallowLineQuantityChange() {
        const result = super.disallowLineQuantityChange();
        return this.useBlackBoxBe() || result;
    },
    restrictLineDiscountChange() {
        const result = super.restrictLineDiscountChange();
        return this.useBlackBoxBe() || result;
    },
    restrictLinePriceChange() {
        const result = super.restrictLinePriceChange();
        return this.useBlackBoxBe() || result;
    },
    doNotAllowRefundAndSales() {
        const result = super.doNotAllowRefundAndSales();
        return this.useBlackBoxBe() || result;
    },
    async preSyncAllOrders(orders) {
        if (this.useBlackBoxBe() && orders.length > 0) {
            for (const order of orders) {
                order.uiState.receipt_type = false;
                const result = await this.pushOrderToBlackbox(order);
                if (!result) {
                    order.state = "draft";
                    throw new Error(_t("Error pushing order to blackbox"));
                }
                this.setDataForPushOrderFromBlackbox(order, result);
                await this.createLog(order);
            }
        }
        return super.preSyncAllOrders(orders);
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.useBlackBoxBe = this.useBlackBoxBe();
        result.posIdentifier = this.config.name;
        if (order && this.useBlackBoxBe()) {
            result.receipt_type = order.uiState.receipt_type;
            result.blackbox_date = order.blackbox_date;
            result.blackbox_order_sequence = order.blackbox_order_sequence;
        }
        return result;
    },
    async increaseCashboxOpeningCounter() {
        await this.data.call("pos.session", "increase_cash_box_opening_counter", [this.session.id]);
    },
    async increaseCorrectionCounter(amount) {
        await this.data.call("pos.session", "increase_correction_counter", [
            this.session.id,
            amount,
        ]);
    },
    async transferOrder(orderUuid, destinationTable) {
        const order = this.models["pos.order"].getBy("uuid", orderUuid);

        if (this.useBlackBoxBe() && order) {
            await this.pushProFormaRefundOrder(order); //push the pro forma refund order to the blackbox and log. The first PS is done when returning to the floo screen
        }
        await super.transferOrder(orderUuid, destinationTable); //transfer the order sync the order so no need to call syncAllOrders again
    },
    async setDiscountFromUI(line, discount) {
        if (
            this.useBlackBoxBe() &&
            this.get_order() &&
            typeof line.discount === "number" &&
            discount !== line.get_discount_str() &&
            !this.multiple_discount
        ) {
            const selectedNumpadMode = this.numpadMode;
            const order = this.get_order();
            await this.pushCorrection(order, [line]);
            const res = await super.setDiscountFromUI(...arguments);
            this.addPendingOrder([order.id]);
            await this.syncAllOrders({ throw: true });
            this.numpadMode = selectedNumpadMode;
            return res;
        } else {
            return await super.setDiscountFromUI(...arguments);
        }
    },
    async _onBeforeDeleteOrder(order) {
        if (this.useBlackBoxBe() && !order.is_empty()) {
            /*
                Deleting an order in a certified POS involves registering the order as a PS.
                Then, registering it as a PR
                ultimately selling it as an NS at a price of 0.
            */
            try {
                this.ui.block();
                await this.pushCorrection(order);
                const serializedOrder = order.serialize();
                serializedOrder.blackbox_tax_category_a = 0;
                serializedOrder.blackbox_tax_category_b = 0;
                serializedOrder.blackbox_tax_category_c = 0;
                serializedOrder.blackbox_tax_category_d = 0;
                serializedOrder.receipt_type = "NS";
                serializedOrder.amount_tax = 0;
                serializedOrder.amount_total = 0;
                serializedOrder.lines = [];
                //add bb fields too
                const dataToSend = this.createOrderDataForBlackbox({
                    ...serializedOrder,
                    receipt_total: 0,
                    plu: order.getPlu([]),
                });
                const blackbox_response = await this.pushToBlackbox(dataToSend);
                order.uiState.receipt_type = "NS";
                order.blackbox_tax_category_a = 0;
                order.blackbox_tax_category_b = 0;
                order.blackbox_tax_category_c = 0;
                order.blackbox_tax_category_d = 0;
                this.setDataForPushOrderFromBlackbox(order, blackbox_response);
                await this.createLog(order, {}, false, false, true);
                await this.increaseCorrectionCounter(order.get_total_with_tax());
            } catch {
                return false;
            } finally {
                this.ui.unblock();
            }
        }
        return super._onBeforeDeleteOrder(...arguments);
    },
    async showLoginScreen() {
        try {
            this.ui.block();
            if (this.useBlackBoxBe() && this.checkIfUserClocked()) {
                await this.clock(this.printer, false);
            }
            this.user_session_status = await this.getUserSessionStatus();
            await super.showLoginScreen();
        } finally {
            this.ui.unblock();
        }
    },
    //#region Blackbox
    useBlackBoxBe() {
        return Boolean(this.config.iface_fiscal_data_module);
    },
    updateReceiptType(order) {
        const order_total_with_tax = order.get_total_with_tax();
        const sale = order.state == "paid" ? "NS" : "PS";
        const refund = order.state == "paid" ? "NR" : "PR";
        if (order_total_with_tax > 0) {
            order.uiState.receipt_type = sale;
        } else if (order_total_with_tax < 0) {
            order.uiState.receipt_type = refund;
        } else {
            if (order.lines.length > 0 && order.lines[0].get_quantity() < 0) {
                order.uiState.receipt_type = refund;
            } else {
                order.uiState.receipt_type = sale;
            }
        }
    },
    //#region Push Pro Forma
    async pushProFormaOrderLog(order) {
        this.updateReceiptType(order);
        const result = await this.pushOrderToBlackbox(order);
        if (result) {
            this.setDataForPushOrderFromBlackbox(order, result);
            await this.createLog(order);
        }
        return result;
    },
    async pushProFormaRefundOrder(order, lines = false) {
        const serializedOrder = order.serialize();
        if (lines) {
            serializedOrder.receipt_total = order.get_total_with_tax_of_lines(lines);
            serializedOrder.plu = order.getPlu(lines);
            serializedOrder.blackbox_tax_category_a = order.getTaxAmountByPercent(21, lines);
            serializedOrder.blackbox_tax_category_b = order.getTaxAmountByPercent(12, lines);
            serializedOrder.blackbox_tax_category_c = order.getTaxAmountByPercent(6, lines);
            serializedOrder.blackbox_tax_category_d = order.getTaxAmountByPercent(0, lines);
        } else {
            serializedOrder.plu = order.getPlu();
            serializedOrder.receipt_total = order.get_total_with_tax();
        }

        if (serializedOrder.receipt_total > 0) {
            serializedOrder.receipt_type = "PR";
        } else if (serializedOrder.receipt_total < 0) {
            serializedOrder.receipt_type = "PS";
        } else if (lines && lines.length > 0 && lines[0].get_quantity() < 0) {
            serializedOrder.receipt_type = "PS";
        } else if (lines && lines.length > 0 && lines[0].get_quantity() >= 0) {
            serializedOrder.receipt_type = "PR";
        } else if (order.lines && order.lines.length > 0 && order.lines[0].get_quantity() < 0) {
            serializedOrder.receipt_type = "PS";
        } else {
            serializedOrder.receipt_type = "PR";
        }

        //add bb fields too
        const dataToSend = this.createOrderDataForBlackbox(serializedOrder);
        const blackbox_response = await this.pushToBlackbox(dataToSend);
        if (!blackbox_response) {
            return;
        }
        await this.createLog(order, blackbox_response, serializedOrder.receipt_type, lines);
    },
    async pushCorrection(order, lines = []) {
        if (lines.length == 0) {
            lines = order.lines;
        }
        await this.pushProFormaOrderLog(order); //push the pro forma order to the blackbox and log
        await this.pushProFormaRefundOrder(order, lines); //push the pro forma refund order to the blackbox and log
    },
    getEmptyLogFields(order) {
        return {
            state: "paid",
            create_date: order.date_order,
            employee_name: this.get_cashier().name,
            amount_total: 0,
            amount_paid: 0,
            currency_id: order.currency.id,
            pos_reference: order.pos_reference,
            config_name: this.config.name,
            session_id: this.session.id,
            lines: [],
            blackbox_order_sequence: order.blackbox_order_sequence,
            plu_hash: order.plu_hash,
            pos_version: this.session._server_version.server_version,
            blackbox_ticket_counters: order.blackbox_ticket_counters,
            blackbox_unique_fdm_production_number: order.blackbox_unique_fdm_production_number,
            certified_blackbox_identifier: this.config.certified_blackbox_identifier,
            blackbox_signature: order.blackbox_signature,
        };
    },
    getLogFields(
        order,
        blackbox_response = {},
        receipt_type = false,
        lines = false,
        emptyNS = false
    ) {
        if (emptyNS) {
            return this.getEmptyLogFields(order);
        }
        if (!receipt_type) {
            receipt_type = order.uiState.receipt_type || "PS";
        }
        if (!lines) {
            lines = order.lines;
        }
        const amount_total = Math.abs(order.get_total_with_tax_of_lines(lines));
        const amount_paid = Math.abs(order.get_total_paid());
        const response = {
            state: order.state,
            create_date: order.date_order,
            employee_name: this.get_cashier().name,
            amount_total: receipt_type[1] == "R" ? -amount_total : amount_total,
            amount_paid: receipt_type[1] == "R" ? -amount_paid : amount_paid,
            currency_id: order.currency.id,
            pos_reference: order.pos_reference,
            config_name: this.config.name,
            session_id: this.session.id,
            lines: this.getLineLogFields(order, receipt_type, lines),
            blackbox_order_sequence: order.blackbox_order_sequence,
            plu_hash: order.plu_hash,
            pos_version: this.session._server_version.server_version,
            blackbox_ticket_counters: order.blackbox_ticket_counters,
            blackbox_unique_fdm_production_number: order.blackbox_unique_fdm_production_number,
            certified_blackbox_identifier: this.config.certified_blackbox_identifier,
            blackbox_signature: order.blackbox_signature,
        };
        if (Object.keys(blackbox_response).length > 0) {
            response.blackbox_signature = blackbox_response.signature;
            response.plu_hash = order.getPlu();
            response.blackbox_unique_fdm_production_number = blackbox_response.fdm_number;
            response.blackbox_ticket_counters =
                receipt_type +
                " " +
                blackbox_response.ticket_counter +
                "/" +
                blackbox_response.total_ticket_counter;
        }
        return response;
    },
    getLineLogFields(order, receipt_type, lines = false) {
        if (!lines) {
            lines = order.lines;
        }
        return lines.map((line) => ({
            product_name: line.product_id.display_name,
            qty: receipt_type[1] == "R" ? -line.get_quantity() : line.get_quantity(),
            price_subtotal_incl:
                receipt_type == "R"
                    ? -line.get_all_prices().priceWithTax
                    : line.get_all_prices().priceWithTax,
            discount: receipt_type == "R" ? -line.get_discount() : line.get_discount(),
        }));
    },
    async createLog(
        order,
        blackbox_response = {},
        receipt_type = false,
        lines = false,
        emptyNS = false
    ) {
        await this.data.call("pos.order", "create_log", [
            [this.getLogFields(order, blackbox_response, receipt_type, lines, emptyNS)],
        ]);
    },
    //#region Push to Blackbox
    async pushDataToBlackbox(data, action) {
        // The return value should be someting like this:
        // {
        //     value: {
        //         signature: "123456789",
        //         vsc: "123456789",
        //         fdm_number: "123456789",
        //         ticket_counter: 12,
        //         total_ticket_counter: 99,
        //         time: "123456",
        //         date: "20240101",
        //     },
        // };
        const fdm = this.hardwareProxy.deviceControllers.fiscal_data_module;
        return new Promise((resolve, reject) => {
            fdm.addListener((data) =>
                data.status.status === "connected" || data.status === "success"
                    ? resolve(data)
                    : reject(data)
            );
            fdm.action({
                action: action,
                high_level_message: data,
            })
                .then((response) => {
                    if (!response.result) {
                        reject({ errorMessage: _t("Blackbox is disconnected") });
                    }
                })
                .catch(() => reject({ errorMessage: _t("IoT Box is disconnected") }));
        });
    },
    async pushOrderToBlackbox(order) {
        await this.updateBlackboxFields(order);
        const clock = order.uiState.clock;
        const dataToSend = this.createOrderDataForBlackbox({
            ...order.serialize(),
            clock: clock,
            receipt_type: order.uiState.receipt_type,
            receipt_total: order.get_total_with_tax(),
            plu: order.getPlu(),
        });
        return this.pushToBlackbox(dataToSend);
    },
    async pushToBlackbox(dataToSend) {
        try {
            const data = await this.pushDataToBlackbox(dataToSend, "registerReceipt");
            const dataValue = this.extractValue(data);
            const errorCode = dataValue.error?.errorCode?.toString() || "0";
            if (!errorCode.startsWith("0")) {
                if (errorCode.startsWith("1")) {
                    this.showBlackboxWarning(errorCode, dataValue.error.errorMessage);
                } else {
                    throw dataValue.error;
                }
            }
            this.lastBBWarning = errorCode;
            return dataValue;
        } catch (err) {
            //the catch might actually not be an error
            const dataValue = this.extractValue(err);
            const errorCode = dataValue?.error?.errorCode?.toString() || "";
            if (errorCode.startsWith("0") || errorCode.startsWith("1")) {
                if (errorCode.startsWith("1")) {
                    this.showBlackboxWarning(errorCode, dataValue.error.errorMessage);
                }
                this.lastBBWarning = errorCode;
                return dataValue;
            }
            if (err.errorCode === "202000") {
                // need to be tested
                this.dialog.add(NumberPopup, {
                    title: _t("Enter Pin Code"),
                    getPayload: (num) => {
                        this.pushDataToBlackbox(num, "registerPIN");
                    },
                });
                throw new Error(_t("Pin code required"));
            } else {
                const defaultError = _t(
                    "Internal blackbox error, the blackbox may have disconnected."
                );
                this.dialog.add(AlertDialog, {
                    title: _t("Blackbox error"),
                    body: err.errorMessage || defaultError,
                });
                throw new Error(err.errorMessage || defaultError);
            }
        }
    },
    showBlackboxWarning(code, message) {
        if (this.lastBBWarning != code) {
            // Show warning only if it is different from the last code received by the blackbox
            this.notification.add(message || _t("Unknown blackbox warning"), {
                type: "warning",
            });
        }
    },
    extractValue(data) {
        // IoT Box v18.4+ replaced the "value" key with "result"
        const key = data.result ? "result" : "value";
        if (Array.isArray(data[key])) {
            return data[key]?.[0];
        } else {
            return data[key];
        }
    },
    async getBlackboxFields(order) {
        return {
            blackbox_tax_category_a: order.getTaxAmountByPercent(21),
            blackbox_tax_category_b: order.getTaxAmountByPercent(12),
            blackbox_tax_category_c: order.getTaxAmountByPercent(6),
            blackbox_tax_category_d: order.getTaxAmountByPercent(0),
            blackbox_order_sequence: await this.getBlackboxSequence(order),
            pos_version: this.session._server_version.server_version,
        };
    },
    async updateBlackboxFields(order) {
        const bbFields = await this.getBlackboxFields(order);
        Object.assign(order, bbFields);
        if (!order.uiState.receipt_type) {
            this.updateReceiptType(order);
        }
    },
    createOrderDataForBlackbox(order) {
        return {
            date: luxon.DateTime.now().toFormat("yyyyMMdd"),
            ticket_time: luxon.DateTime.now().toFormat("HHmmss"),
            insz_or_bis_number: this.config.module_pos_hr
                ? this.session._employee_insz_or_bis_number[this.get_cashier().id]
                : this.user.insz_or_bis_number,
            ticket_number: order.blackbox_order_sequence.toString(),
            type: order.receipt_type,
            receipt_total: Math.abs(order.receipt_total).toFixed(2).toString().replace(".", ""),
            vat1: order.blackbox_tax_category_a
                ? Math.abs(order.blackbox_tax_category_a).toFixed(2).replace(".", "")
                : "",
            vat2: order.blackbox_tax_category_b
                ? Math.abs(order.blackbox_tax_category_b).toFixed(2).replace(".", "")
                : "",
            vat3: order.blackbox_tax_category_c
                ? Math.abs(order.blackbox_tax_category_c).toFixed(2).replace(".", "")
                : "",
            vat4: order.blackbox_tax_category_d
                ? Math.abs(order.blackbox_tax_category_d).toFixed(2).replace(".", "")
                : "",
            plu: order.plu,
            clock: order.clock ? order.clock : false,
        };
    },
    setDataForPushOrderFromBlackbox(order, data) {
        if (!order.uiState.receipt_type) {
            this.updateReceiptType(order);
        }
        order.blackbox_signature = data.signature;
        order.blackbox_unit_id = data.vsc;
        order.plu_hash = order.getPlu();
        order.blackbox_vsc_identification_number = data.vsc;
        order.blackbox_unique_fdm_production_number = data.fdm_number;
        order.blackbox_ticket_counter = data.ticket_counter;
        order.blackbox_total_ticket_counter = data.total_ticket_counter;
        order.blackbox_ticket_counters =
            order.uiState.receipt_type +
            " " +
            data.ticket_counter +
            "/" +
            data.total_ticket_counter;
        order.blackbox_time = data.time.replace(/(\d{2})(\d{2})(\d{2})/g, "$1:$2:$3");
        order.blackbox_date = data.date.replace(/(\d{4})(\d{2})(\d{2})/g, "$3-$2-$1");
    },
    async getBlackboxSequence(order) {
        const functionToCall = (order.uiState.receipt_type || "").toLowerCase().startsWith("p")
            ? "get_PS_sequence_next"
            : "get_NS_sequence_next";
        return parseInt(await this.data.call("pos.config", functionToCall, [[this.config.id]]));
    },
});
