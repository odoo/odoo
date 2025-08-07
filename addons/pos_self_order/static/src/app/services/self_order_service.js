import { Reactive } from "@web/core/utils/reactive";
import { ConnectionLostError, RPCError, rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency as webFormatCurrency } from "@web/core/currency";
import { attributeFormatter } from "@pos_self_order/app/utils";
import { markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";
import { formatDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { printerService } from "@point_of_sale/app/services/printer_service";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { HWPrinter } from "@point_of_sale/app/utils/printer/hw_printer";
import { renderToElement } from "@web/core/utils/render";
import { TimeoutPopup } from "@pos_self_order/app/components/timeout_popup/timeout_popup";
import { UnavailableProductsDialog } from "@pos_self_order/app/components/unavailable_product_dialog/unavailable_product_dialog";
import { constructFullProductName, deduceUrl, random5Chars } from "@point_of_sale/utils";
import { getOrderLineValues } from "./card_utils";
import {
    getTaxesAfterFiscalPosition,
    getTaxesValues,
} from "@point_of_sale/app/models/utils/tax_utils";

export class SelfOrder extends Reactive {
    constructor(...args) {
        super();
        this.ready = this.setup(...args).then(() => this);
    }

    async setup(
        env,
        { notification, router, printer, renderer, barcode, bus_service, dialog, pos_data }
    ) {
        // services
        this.notification = notification;
        this.router = router;
        this.data = pos_data;
        this.env = env;
        this.printer = printer;
        this.renderer = renderer;
        this.barcode = barcode;
        this.bus = bus_service;
        this.dialog = dialog;

        // data
        this.models = this.data.models;
        this.session = this.models["pos.session"].getFirst();
        this.config = this.models["pos.config"].getFirst();
        this.company = this.config.company_id;
        this.currency = this.config.currency_id;

        this.markupDescriptions();
        this.access_token = this.config.access_token;
        this.lastEditedProductId = null;
        this.currentProduct = 0;
        this.currentTable = null;
        this.priceLoading = false;
        this.rpcLoading = false;
        this.paymentError = false;
        this.selectedOrderUuid = null;
        this.ordering = false;
        this.orderTakeAwayState = {};
        this.orderSubscribtion = new Set();
        this.kitchenPrinters = [];
        this.productCategories = [];
        this.currentCategory = null;
        this.productByCategIds = {};
        this.availableCategories = [];

        this.initData();
        if (this.config.self_ordering_mode === "kiosk") {
            this.initKioskData();
        } else {
            await this.initMobileData();
        }

        this.data.connectWebSocket("ORDER_STATE_CHANGED", () => this.getUserDataFromServer());
        this.data.connectWebSocket("PRODUCT_CHANGED", (payload) => {
            const productTemplateIds = payload["product.template"].map((tmpl) => tmpl.id);
            const existingProductIds = this.models["product.template"].filter((tmpl) =>
                productTemplateIds.includes(tmpl.id)
            );
            const hasNewProducts = productTemplateIds.length !== existingProductIds.length;
            this.models.connectNewData(payload);
            if (hasNewProducts) {
                this.initProducts();
            }
        });
        if (this.config.self_ordering_mode === "kiosk") {
            this.data.connectWebSocket("STATUS", ({ status }) => {
                if (status === "closed") {
                    this.pos_session = [];
                    this.ordering = false;
                } else {
                    // reload to get potential new settings
                    // more easier than RPC for now
                    window.location.reload();
                }
            });
            this.data.connectWebSocket("PAYMENT_STATUS", ({ payment_result, data }) => {
                if (payment_result === "Success") {
                    this.models.connectNewData(data);
                    const order = this.models["pos.order"].find(
                        (o) => o.access_token === data["pos.order"][0].access_token
                    );
                    if (["paid", "done"].includes(order?.state)) {
                        this.notification.add(_t("Your order has been paid"), {
                            type: "success",
                        });
                        this.confirmationPage(
                            "order",
                            this.config.self_ordering_mode,
                            order.access_token
                        );
                    }
                } else {
                    this.paymentError = true;
                }
            });
        }
        barcode.bus.addEventListener("barcode_scanned", (ev) => {
            if (!this.ordering) {
                this.notification.add(_t("We're currently closed"), {
                    type: "danger",
                });
                return;
            }
            const product = this.models["product.product"].filter(
                (p) => p.barcode === ev.detail.barcode
            )?.[0];
            if (!product) {
                this.notification.add(_t("Product not found"), {
                    type: "danger",
                });
                return;
            }
            if (!product.self_order_available) {
                this.notification.add(_t("Product is not available"), {
                    type: "danger",
                });
                return;
            }
            const productTemplate = product.product_tmpl_id;
            if (productTemplate.isConfigurable()) {
                this.router.navigate("product", { id: productTemplate.id });
                return;
            }
            this.addToCart(productTemplate, 1, "", {}, {});
            this.router.navigate("cart");
        });
    }

    get selfService() {
        const presets = this.models["pos.preset"].getAll();
        return this.config.use_presets && presets.length > 0
            ? this.currentOrder?.preset_id?.service_at
            : this.config.self_ordering_service_mode;
    }

    getAvailableCategories() {
        let now = luxon.DateTime.now();
        now = now.hour + now.minute / 60;
        const availableCategories = this.productCategories
            .filter((c) => this.productByCategIds[c.id]?.length > 0)
            .sort((a, b) => a.sequence - b.sequence);
        return availableCategories.filter((c) => {
            const hourStart = c.hour_after;
            const hourUntil = c.hour_until;
            if (hourStart === hourUntil || (hourStart === 0 && hourUntil === 24)) {
                // if equal, it means open the whole day
                return true;
            } else if (hourStart < hourUntil) {
                // in this case, if current time is in between, then shop is open
                return now >= hourStart && now <= hourUntil;
            } else {
                // in this case, if current time is in between, then shop is closed
                return !(now >= hourStart && now <= hourUntil);
            }
        });
    }
    computeAvailableCategories() {
        this.availableCategories = this.getAvailableCategories();
        this.currentCategory = this.availableCategories[0];
    }

    isCategoryAvailable(categId) {
        return this.availableCategories.find((c) => c.id === categId);
    }

    removeLine(line) {
        this.currentOrder.removeOrderline(line);
    }

    async syncPresetSlotAvaibility(preset) {
        try {
            const presetAvailabilities = await rpc(`/pos-self-order/get-slots`, {
                access_token: this.access_token,
                preset_id: this.currentOrder?.preset_id?.id,
            });

            preset.computeAvailabilities(presetAvailabilities);
        } catch {
            console.info("Offline mode, cannot update the slot avaibility");
        }
    }

    showComboSelectionPage(product) {
        const selectedCombos = [];
        for (const combo of product.combo_ids) {
            const { combo_item_ids } = combo;
            if (
                combo_item_ids.length > 1 ||
                combo.qty_max > 1 ||
                combo_item_ids[0]?.product_id.isConfigurable()
            ) {
                return { show: true, selectedCombos: [] };
            }
            selectedCombos.push({
                combo_item_id: this.models["product.combo.item"].get(combo_item_ids[0].id),
                configuration: {
                    attribute_custom_values: [],
                    attribute_value_ids: [],
                    price_extra: 0,
                },
            });
        }
        return { show: false, selectedCombos };
    }

    async addToCart(
        productTemplate,
        qty,
        customer_note,
        selectedValues = {},
        customValues = {},
        comboValues = {}
    ) {
        const product = productTemplate.product_variant_ids[0];
        const values = getOrderLineValues(
            this,
            productTemplate,
            qty,
            customer_note,
            selectedValues,
            customValues,
            comboValues
        );
        const newLine = this.models["pos.order.line"].create(values);
        newLine.full_product_name = constructFullProductName(
            newLine,
            this.models["product.template.attribute.value"].getAllBy("id"),
            product.name
        );
        const lineToMerge = this.currentOrder.lines.find(
            (l) => l.canBeMergedWith(newLine) && l.id !== newLine.id
        );

        if (lineToMerge) {
            lineToMerge.setQuantity(lineToMerge.qty + newLine.qty);
            newLine.delete();
        }
    }
    async confirmationPage(screen_mode, device, access_token) {
        if (!access_token) {
            throw new Error("No access token provided for confirmation page");
        }

        this.router.navigate("confirmation", {
            orderAccessToken: access_token || this.currentOrder.access_token,
            screenMode: screen_mode,
        });
        this.printKioskChanges(access_token);
    }
    hasPaymentMethod() {
        return this.filterPaymentMethods(this.models["pos.payment.method"].getAll()).length > 0;
    }

    filterPaymentMethods(pms) {
        //based on _load_pos_self_data_domain from pos_payment_method.py
        return this.config.self_ordering_mode === "kiosk"
            ? pms.filter((rec) => ["adyen", "stripe"].includes(rec.use_payment_terminal))
            : [];
    }

    async confirmOrder() {
        const payAfter = this.config.self_ordering_pay_after; // each, meal
        const device = this.config.self_ordering_mode; // kiosk, mobile
        const service = this.selfService; // table, counter, delivery
        const paymentMethods = this.filterPaymentMethods(
            this.models["pos.payment.method"].getAll()
        ); // Stripe, Adyen, Online

        let order = this.currentOrder;
        const orderHasChanges = Object.keys(order.changes).length > 0;

        // Stand number page will recall this function after the stand number is set
        if (
            service === "table" &&
            !order.isTakeaway &&
            device === "kiosk" &&
            !order.table_stand_number
        ) {
            this.router.navigate("stand_number");
            return;
        }

        order = await this.sendDraftOrderToServer();

        if (!order) {
            return;
        }

        // When no payment methods redirect to confirmation page
        // the client will be able to pay at counter
        if (paymentMethods.length === 0) {
            let screenMode = "pay";

            if (orderHasChanges) {
                screenMode = payAfter === "meal" ? "order" : "pay";
            }

            this.confirmationPage(screenMode, device, order.access_token);
        } else {
            // In meal mode, first time the customer validate his order, we send it to the server
            // and we redirect him to the confirmation page, the next time he validate his order
            // if the order is already saved on the server, we redirect him to the payment page
            // In each mode, we redirect the customer to the payment page directly
            if (payAfter === "meal" && orderHasChanges) {
                await this.sendDraftOrderToServer();
                this.confirmationPage("order", device, order.access_token);
            } else {
                this.router.navigate("payment");
            }
        }
    }

    get currentOrder() {
        const orderAvailable = (o) => {
            const isDraft = o.state === "draft";
            const isPaid = o.state === "paid";
            const isZeroAmount = o.amount_total === 0;
            const isKiosk = this.config.self_ordering_mode === "kiosk";

            return (
                isDraft ||
                (isPaid && isZeroAmount && isKiosk) ||
                (isPaid && this.router.activeSlot === "confirmation")
            );
        };

        const order = this.models["pos.order"].getBy("uuid", this.selectedOrderUuid);
        if (order && orderAvailable(order)) {
            return order;
        }

        const existingOrder = this.models["pos.order"].find((o) => orderAvailable(o));
        if (existingOrder) {
            this.selectedOrderUuid = existingOrder.uuid;
            return existingOrder;
        }
        return this.createNewOrder();
    }

    createNewOrder() {
        const autoSelectedPresets =
            this.models["pos.preset"].length === 1 && this.config.use_presets;

        const fiscalPosition = autoSelectedPresets
            ? this.config.default_preset_id?.fiscal_position_id
            : this.config.default_fiscal_position_id;

        const pricelist = autoSelectedPresets
            ? this.config.default_preset_id?.pricelist_id
            : this.config.pricelist_id;

        return this.models["pos.order"].create({
            company_id: this.company,
            ticket_code: random5Chars(),
            session_id: this.session,
            config_id: this.config,
            fiscal_position_id: fiscalPosition,
            pricelist_id: pricelist,
            preset_id: autoSelectedPresets ? this.config.default_preset_id : false,
        });
    }

    get kioskMode() {
        return this.config.self_ordering_mode === "kiosk";
    }

    markupDescriptions() {
        for (const product of this.models["product.template"].getAll()) {
            product.public_description = product.public_description
                ? markup(product.public_description)
                : "";
        }
    }

    initProducts() {
        this.productCategories = this.models["pos.category"].getAll();
        this.productByCategIds = this.models["product.template"].getAllBy("pos_categ_ids");

        const excludedProductTemplateIds = new Set(
            this.config._pos_special_products_ids
                .map((id) => this.models["product.product"].get(id)?.product_tmpl_id?.id)
                .filter(Boolean)
        );

        for (const category_id in this.productByCategIds) {
            this.productByCategIds[category_id] = this.productByCategIds[category_id].filter(
                (p) => !excludedProductTemplateIds.has(p.id)
            );
        }
        const productWoCat = this.models["product.template"].filter(
            (p) => p.pos_categ_ids.length === 0 && !excludedProductTemplateIds.has(p.id)
        );

        if (productWoCat.length && !this.config.iface_available_categ_ids.length) {
            this.productCategories.push({
                id: 0,
                hour_after: 0,
                hour_until: 24,
                name: _t("Uncategorised"),
            });
            this.productByCategIds["0"] = productWoCat;
        }
    }

    initData() {
        this.initProducts();
        this._initLanguages();

        for (const printerConfig of this.models["pos.printer"].getAll()) {
            const printer = this.createPrinter(printerConfig);
            if (printer) {
                printer.config = printerConfig;
                this.kitchenPrinters.push(printer);
            }
        }
    }

    _initLanguages() {
        const languages = this.config.self_ordering_available_language_ids;
        this.currentLanguage = languages.find((l) => l.code === cookie.get("frontend_lang"));
        if (languages && !this.currentLanguage) {
            this.currentLanguage = this.config.self_ordering_default_language_id;
        }
        languages?.forEach((lg) => {
            // To display  "Français (BE)"  instead of "French (BE) / Français (BE)"
            lg.display_name = lg.name.split("/").pop();
        });
        cookie.set("frontend_lang", this.currentLanguage?.code || "en_US");
    }

    createPrinter(printer) {
        const url = deduceUrl(printer.proxy_ip || "");
        return new HWPrinter({ url });
    }

    _getKioskPrintingCategoriesChanges(order, categories) {
        return order.lines.filter((orderline) => {
            const baseProductId = orderline.combo_parent_id
                ? orderline.combo_parent_id.product_id.id
                : orderline.product_id.id;
            return categories.some((category) =>
                this.models["product.product"]
                    .get(baseProductId)
                    .pos_categ_ids.map((categ) => categ.id)
                    .includes(category.id)
            );
        });
    }

    async printKioskChanges(access_token = "") {
        const d = new Date();
        let hours = "" + d.getHours();
        hours = hours.length < 2 ? "0" + hours : hours;
        let minutes = "" + d.getMinutes();
        minutes = minutes.length < 2 ? "0" + minutes : minutes;
        const order = access_token
            ? this.models["pos.order"].find((o) => o.access_token === access_token)
            : this.currentOrder;

        for (const printer of this.kitchenPrinters) {
            const orderlines = this._getKioskPrintingCategoriesChanges(
                order,
                Object.values(printer.config.product_categories_ids)
            );
            if (orderlines) {
                const printingChanges = {
                    new: orderlines,
                    tracker: order.table_stand_number,
                    trackingNumber: order.tracking_number || "unknown number",
                    name: order.pos_reference || "unknown order",
                    time: {
                        hours,
                        minutes,
                    },
                    preset_name: order.preset_id?.name || "",
                    preset_time: order.presetDateTime,
                };
                const receipt = renderToElement("pos_self_order.OrderChangeReceipt", {
                    changes: printingChanges,
                });
                await printer.printReceipt(receipt);
            }
        }
    }
    initKioskData() {
        if (this.session && this.access_token) {
            this.ordering = true;
        }

        window.addEventListener("click", (event) => {
            clearTimeout(this.idleTimout);
            this.timeoutPopup?.();
            this.idleTimout = setTimeout(() => {
                if (this.router.activeSlot !== "payment" && this.router.activeSlot !== "default") {
                    this.timeoutPopup = this.dialog.add(TimeoutPopup, {
                        onTimeout: () => {
                            this.dialog.closeAll();
                            this.router.navigate("default");
                        },
                    });
                }
            }, 1000 * 90);
        });
    }

    async initMobileData() {
        if (this.config.self_ordering_mode !== "qr_code") {
            if (
                this.session &&
                this.access_token &&
                this.config.self_ordering_mode !== "consultation"
            ) {
                await this.getUserDataFromServer();
                const tableIdentifier = this.router.getTableIdentifier();

                if (tableIdentifier) {
                    this.currentTable = this.models["restaurant.table"].find(
                        (t) => t.identifier === tableIdentifier
                    );
                }

                this.ordering = true;
            }

            if (!this.ordering) {
                return;
            }
        }
    }

    cancelOrder() {
        const lineToDelete = [];
        for (const line of this.currentOrder.lines) {
            const changes = line.changes;
            if (Object.values(changes).some((v) => v)) {
                if (line.qty <= changes.qty) {
                    lineToDelete.push(line);
                } else {
                    line.update({
                        qty: changes["qty"],
                        customer_note: changes["customer_note"],
                        attribute_value_ids: changes["attribute_value_ids"]
                            ? JSON.parse(changes["attribute_value_ids"]).map((a) => [
                                  "link",
                                  this.models["product.template.attribute.value"].get(a),
                              ])
                            : [],
                        custom_attribute_value_ids: changes["custom_attribute_value_ids"]
                            ? JSON.parse(changes["custom_attribute_value_ids"]).map((a) => [
                                  "link",
                                  this.models["product.attribute.custom.value"].get(a),
                              ])
                            : [],
                    });
                }
            }
        }

        for (const line of lineToDelete) {
            line.delete();
        }

        this.currentOrder.recomputeChanges();
        if (Math.max(this.currentOrder.lines.map((l) => l.qty)) <= 0) {
            this.router.navigate("default");
            this.currentOrder.delete();
            this.selectedOrderUuid = null;
        }
    }

    async sendDraftOrderToServer() {
        if (
            Object.keys(this.currentOrder.changes).length === 0 ||
            this.currentOrder.lines.length === 0
        ) {
            return this.currentOrder;
        }

        try {
            const tableIdentifier = this.router.getTableIdentifier([]);
            let uuid = this.selectedOrderUuid;
            this.currentOrder.recomputeOrderData();
            const data = await rpc(
                `/pos-self-order/process-order/${this.config.self_ordering_mode}`,
                {
                    order: this.currentOrder.serializeForORM(),
                    access_token: this.access_token,
                    table_identifier: this.currentOrder?.table_id?.identifier || tableIdentifier,
                }
            );
            const result = this.models.connectNewData(data);
            if (result["pos.order"][0].uuid !== this.selectedOrderUuid) {
                this.orderTakeAwayState[result["pos.order"][0].uuid] =
                    this.orderTakeAwayState[this.selectedOrderUuid];
                delete this.orderTakeAwayState[this.selectedOrderUuid];
                this.currentOrder.delete();
                uuid = result["pos.order"][0].uuid;
            }
            this.data.debouncedSynchronizeLocalDataInIndexedDB();

            if (this.config.self_ordering_pay_after === "each") {
                this.selectedOrderUuid = null;
            }

            this.currentOrder.recomputeChanges();
            return this.models["pos.order"].getBy("uuid", uuid);
        } catch (error) {
            const order = this.models["pos.order"].getBy("uuid", this.selectedOrderUuid);
            this.handleErrorNotification(error, [order.access_token]);
            return false;
        }
    }

    async getUserDataFromServer(tokens = []) {
        const tableIdentifier = this.router.getTableIdentifier([]);
        const dbAccessToken = this.models["pos.order"]
            .filter((o) => o.state === "draft" && typeof o.id === "number")
            .map((order) => ({
                access_token: order.access_token,
                write_date: serializeDateTime(order.write_date.plus({ seconds: 1 })),
            }))
            .filter((order) => order.access_token);

        // Token given in argument are probably not in the local database
        // so write_date is set to 1970-01-01 00:00:00
        const argTokens = tokens.map((token) => ({
            access_token: token,
            write_date: "1970-01-01 00:00:00",
        }));

        const accessTokens = [...dbAccessToken, ...argTokens];
        if (Object.keys(accessTokens).length === 0 && !tableIdentifier) {
            return;
        }

        try {
            const data = await rpc(`/pos-self-order/get-user-data/`, {
                access_token: this.access_token,
                order_access_tokens: accessTokens,
                table_identifier: tableIdentifier,
            });
            this.selectedOrderUuid = null;
            const result = this.models.connectNewData(data);
            const openOrder = result["pos.order"]?.find((o) => o.state === "draft");
            if (openOrder && this.router.activeSlot !== "confirmation") {
                this.selectedOrderUuid = openOrder.uuid;

                // Remove all other open orders in draft and add orderline in the current order
                const lineCmd = [];
                for (const order of this.models["pos.order"].filter((o) => o.state === "draft")) {
                    if (order.uuid !== openOrder.uuid) {
                        lineCmd.push(...order.lines);
                        order.delete();
                    }
                }

                openOrder.update({
                    lines: [["link", lineCmd]],
                });
                openOrder.recomputeChanges();
            }
            this.data.debouncedSynchronizeLocalDataInIndexedDB();
        } catch (error) {
            this.handleErrorNotification(
                error,
                this.models["pos.order"].map((order) => order.access_token)
            );
        }
    }

    changeOrderState(access_token, state) {
        const order = this.orders.filter((o) => o.access_token === access_token);
        let message = _t("Your order status has been changed");

        if (order.length === 0) {
            this.handleErrorNotification(new Error("Warning, no order with this access_token"));
        } else if (order.length !== 1) {
            this.handleErrorNotification(
                new Error("Warning, two orders with the same access_token")
            );
        } else {
            order[0].state = state;
        }

        if (state === "paid") {
            this.selectedOrderUuid = null;
            message = _t("Your order has been paid");
        } else if (state === "cancel") {
            this.selectedOrderUuid = null;
            message = _t("Your order has been cancelled");
        }

        this.notification.add(message, {
            type: "success",
        });
        this.router.navigate("default");
    }

    isOrder() {
        if (!this.currentOrder || !this.currentOrder.lines.length) {
            this.router.navigate("default");
        }
    }

    handleErrorNotification(error, accessToken = []) {
        this.rpcLoading = false;

        let message = _t("An error has occurred");
        let cleanOrders = false;

        if (error instanceof RPCError) {
            if (error.data.name === "werkzeug.exceptions.Unauthorized") {
                message = _t("You're not authorized to perform this action");
                cleanOrders = true;
            } else if (error.data.name === "werkzeug.exceptions.NotFound") {
                message = _t("Orders not found on server");
                cleanOrders = true;
            } else if (error?.data?.name === "odoo.exceptions.UserError") {
                message = error.data.message;
                this.resetTableIdentifier();
            }
        } else if (error instanceof ConnectionLostError) {
            message = _t("Connection lost, please try again later");
        }

        this.notification.add(message, {
            type: "danger",
        });

        if (accessToken && cleanOrders) {
            this.selectedOrderUuid = null;

            for (const index in this.orders) {
                if (accessToken.includes(this.orders[index].access_token)) {
                    this.orders.splice(index, 1);
                }
            }
        }
    }

    formatMonetary(price) {
        return webFormatCurrency(price, this.currency.id);
    }

    verifyCart() {
        let result = true;
        const unavailableProducts = new Set();

        for (const line of this.currentOrder.unsentLines) {
            if (line.combo_parent_id?.uuid) {
                continue;
            }

            const lineChanges = this.currentOrder.uiState.lineChanges[line.uuid];
            const alreadySent = lineChanges
                ? Object.values(this.currentOrder.uiState.lineChanges[line.uuid]).every((v) => !v)
                : false;

            const wrongChild = line.combo_line_ids.find((l) => !l.product_id.self_order_available);
            if (wrongChild || !line.product_id?.self_order_available) {
                if (alreadySent) {
                    line.qty = alreadySent.qty;
                    line.customer_note = alreadySent.customer_note;
                    line.selected_attributes = alreadySent.selected_attributes;
                } else {
                    const productName = !line.product_id?.self_order_available
                        ? line.product_id?.name
                        : wrongChild?.product_id?.name;

                    if (productName) {
                        unavailableProducts.add(productName);
                    }
                    // Remove all children and parent if any product is unavailable
                    line.combo_line_ids.forEach((childLine) => {
                        childLine.delete();
                    });
                    line.delete();
                }
                result = false;
            }
        }

        if (unavailableProducts.size) {
            const productNames = Array.from(unavailableProducts);
            const goBackIfCartEmpty = () => {
                if (!this.currentOrder.unsentLines.length) {
                    this.router.back();
                }
            };
            this.dialog.add(UnavailableProductsDialog, {
                productNames: productNames,
                onClose: goBackIfCartEmpty,
            });
        }
        return result;
    }

    getProductPriceInfo(productTemplate, product) {
        const pricelist = this.config.use_presets
            ? this.currentOrder.preset_id?.pricelist_id
            : this.config.pricelist_id;
        const price = productTemplate.getPrice(pricelist, 1, 0, false, product);
        let taxes = productTemplate.taxes_id;

        if (!product) {
            product = productTemplate;
        }

        // Fiscal position.
        const order = this.currentOrder;
        if (order && order.fiscal_position_id) {
            taxes = getTaxesAfterFiscalPosition(taxes, order.fiscal_position_id, this.models);
        }

        // Taxes computation.
        const taxesData = getTaxesValues(taxes, price, 1, product, {}, this.company, this.currency);

        return { pricelist_price: price, ...taxesData };
    }
    getProductDisplayPrice(productTemplate, product) {
        const taxesData = this.getProductPriceInfo(productTemplate, product);
        if (this.isTaxesIncludedInPrice()) {
            return taxesData.total_included;
        } else {
            return taxesData.total_excluded;
        }
    }

    isTaxesIncludedInPrice() {
        return this.config.iface_tax_included === "total";
    }
    getLinePrice(line) {
        return this.config.iface_tax_included ? line.price_subtotal_incl : line.price_subtotal;
    }
    getSelectedAttributes(line) {
        const attributeValues = line.attribute_value_ids;
        const customAttr = line.custom_attribute_value_ids;
        return attributeFormatter(
            this.models["product.attribute"].getAllBy("id"),
            attributeValues,
            customAttr
        );
    }
    getFullProductName(line) {
        const attrs = this.getSelectedAttributes(line);
        const attrsStr = " (" + attrs.map((a) => a.value).join(", ") + ")";
        return line.full_product_name + (attrs.length ? attrsStr : "");
    }
    showDownloadButton(order) {
        return this.config.self_ordering_mode === "mobile" && order.state === "paid";
    }
    async downloadReceipt(order) {
        const link = document.createElement("a");
        const currentDate = formatDateTime(luxon.DateTime.now(), {
            format: "MM_dd_yyyy-HH_mm_ss",
        });
        const companyName = this.company.name.replaceAll(" ", "_");
        link.download = `${companyName}-${currentDate}.png`;
        const png = await this.renderer.toCanvas(
            OrderReceipt,
            {
                order: order,
            },
            {}
        );
        link.href = png.toDataURL().replace("data:image/jpeg;base64,", "");
        link.click();
    }

    hasPresets() {
        return this.config.use_presets && this.models["pos.preset"].length > 1;
    }

    get kioskBackgroundImageUrl() {
        const imageId = this.config._self_ordering_image_background_ids[0];
        if (imageId) {
            return `url('/web/image/ir.attachment/${imageId}/raw')`;
        }
        return "none";
    }
}

export const selfOrderService = {
    dependencies: [
        "notification",
        "router",
        "pos_data",
        "printer",
        "renderer",
        "barcode",
        "bus_service",
        "dialog",
    ],
    async start(env, services) {
        return new SelfOrder(env, services).ready;
    },
};

registry.category("services").add("printer", printerService);
registry.category("services").add("self_order", selfOrderService);

/**
 * @returns {SelfOrder}
 */
export function useSelfOrder() {
    return useService("self_order");
}
