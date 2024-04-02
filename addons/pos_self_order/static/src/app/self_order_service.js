/** @odoo-module */
import { Reactive, effect } from "@web/core/utils/reactive";
import { ConnectionLostError, RPCError, rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency as webFormatCurrency } from "@web/core/currency";
import { Product } from "@pos_self_order/app/models/product";
import { session } from "@web/session";
import { getColor } from "@web/core/colors/colors";
import { categorySorter, attributeFormatter, attributeFlatter } from "@pos_self_order/app/utils";
import { Order } from "@pos_self_order/app/models/order";
import { batched } from "@web/core/utils/timing";
import { useState, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";
import { formatDateTime } from "@web/core/l10n/dates";
import { printerService } from "@point_of_sale/app/printer/printer_service";
import {
    qrCodeSrc,
    getOnNotified,
    constructFullProductName,
    deduceUrl,
    uuidv4,
    random5Chars,
} from "@point_of_sale/utils";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { Line } from "./models/line";
import { HWPrinter } from "@point_of_sale/app/printer/hw_printer";
import { renderToElement } from "@web/core/utils/render";
export class SelfOrder extends Reactive {
    constructor(...args) {
        super();
        this.ready = this.setup(...args).then(() => this);
    }

    async setup(env, { notification, router, printer, renderer, barcode, bus_service, pos_data }) {
        // services
        this.notification = notification;
        this.router = router;
        this.env = env;
        this.printer = printer;
        this.renderer = renderer;
        this.barcode = barcode;
        this.bus = bus_service;
        this.data = pos_data;

        // data
        Object.assign(this, {
            ...session.pos_self_order_data,
        });

        this.productsGroupedByCategory = {};
        this.lastEditedProductId = null;
        this.attributeValueById = {};
        this.currentProduct = 0;
        this.attributeById = {};
        this.priceLoading = false;
        this.rpcLoading = false;
        this.productByIds = {};
        this.paymentError = false;
        this.editedOrder = null;
        this.comboByIds = {};
        this.ordering = false;
        this.orders = [];
        this.availableCategoryListIds = [];
        this.kitchenPrinters = [];

        this.initData();

        if (this.config.self_ordering_mode === "kiosk") {
            this.initKioskData();
        } else {
            await this.initMobileData();
        }
        effect(
            batched((orders) => {
                for (const order of orders) {
                    if (!order.access_token) {
                        return;
                    }
                    const onNotified = getOnNotified(this.bus, order.access_token);
                    onNotified("ORDER_STATE_CHANGED", ({ access_token, state }) => {
                        this.changeOrderState(access_token, state);
                    });
                    onNotified("ORDER_CHANGED", ({ order }) => {
                        this.updateOrdersFromServer([order], [order.access_token]);
                    });
                }
            }),
            [this.orders]
        );
        this.onNotified = getOnNotified(this.bus, this.access_token);
        this.onNotified("PRODUCT_CHANGED", (payload) => {
            this.handleProductChanges(payload);
        });
        if (this.config.self_ordering_mode === "kiosk") {
            this.onNotified("STATUS", ({ status }) => {
                if (status === "closed") {
                    this.session = [];
                    this.ordering = false;
                } else {
                    // reload to get potential new settings
                    // more easier than RPC for now
                    window.location.reload();
                }
            });
            this.onNotified("PAYMENT_STATUS", ({ payment_result, order }) => {
                if (payment_result === "Success") {
                    this.updateOrderFromServer(order);
                    this.router.navigate("payment_success");
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
            const product = Object.values(this.productByIds).filter(
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
            if (product.attributes.length) {
                this.router.navigate("product", { id: product.id });
                return;
            }
            this.addToCart(product, 1, "", {}, {});
            this.router.navigate("cart");
        });
    }

    async addToCart(product, qty, customer_note, selectedValues, customValues) {
        const lineToMerge =
            !product.pos_combo_ids.length &&
            (this.editedLine ||
                this.currentOrder.lines.find(
                    (l) =>
                        JSON.stringify(l.attribute_value_ids.sort()) ===
                            JSON.stringify(attributeFlatter(selectedValues).sort()) &&
                        l.customer_note === customer_note &&
                        l.product_id === product.id
                ));
        if (lineToMerge) {
            lineToMerge.attribute_value_ids = attributeFlatter(selectedValues);
            lineToMerge.customer_note = customer_note;
            lineToMerge.full_product_name = product.name;
            if (this.editedLine) {
                lineToMerge.qty = qty;
            } else {
                lineToMerge.qty += qty;
            }
        } else {
            const mainLine = new Line({
                qty,
                product_id: product.id,
                customer_note,
                custom_attribute_value_ids: Object.values(customValues),
                attribute_value_ids: attributeFlatter(selectedValues),
            });
            mainLine.full_product_name = constructFullProductName(
                mainLine,
                this.attributeValueById,
                product.name
            );
            this.currentOrder.lines.push(mainLine);
        }
        await this.getPricesFromServer();
        // If a command line does not have a quantity greater than 0, we consider it deleted
        this.currentOrder.lines = this.currentOrder.lines.filter((o) => o.qty > 0);
    }
    async confirmationPage(screen_mode, device) {
        this.router.navigate("confirmation", {
            orderAccessToken: this.currentOrder.access_token,
            screenMode: screen_mode,
        });
        if (device === "kiosk") {
            this.printKioskChanges();
        }
    }

    async confirmOrder() {
        const payAfter = this.config.self_ordering_pay_after; // each, meal
        const device = this.config.self_ordering_mode; // kiosk, mobile
        const service = this.config.self_ordering_service_mode; // table, counter
        const paymentMethods = this.models["pos.payment.method"].getAll(); // Stripe, Adyen, Online
        const order = this.currentOrder;

        // Stand number page will recall this function after the stand number is set
        if (
            service === "table" &&
            !order.takeaway &&
            device === "kiosk" &&
            !order.table_stand_number
        ) {
            this.router.navigate("stand_number");
            return;
        }

        // if the amount is 0, we don't need to go to the payment page
        // this directive works for both mode each and meal
        if (order.amount_total === 0 && order.lines.length > 0) {
            await this.sendDraftOrderToServer();
            this.confirmationPage("order", device);
            return;
        }

        // When no payment methods redirect to confirmation page
        // the client will be able to pay at counter
        if (paymentMethods.length === 0) {
            let screenMode = "pay";

            if (!order.isSavedOnServer) {
                await this.sendDraftOrderToServer();
                screenMode = payAfter === "meal" ? "order" : "pay";
            }
            this.confirmationPage(screenMode, device);
        } else {
            // In meal mode, first time the customer validate his order, we send it to the server
            // and we redirect him to the confirmation page, the next time he validate his order
            // if the order is already saved on the server, we redirect him to the payment page
            // In each mode, we redirect the customer to the payment page directly
            if (payAfter === "meal" && !order.isSavedOnServer) {
                await this.sendDraftOrderToServer();
                this.confirmationPage("order", device);
            } else {
                this.router.navigate("payment");
            }
        }
    }

    get currentOrder() {
        if (
            this.editedOrder &&
            (this.editedOrder.state === "draft" ||
                (this.editedOrder.state === "paid" &&
                    this.editedOrder.amount_total === 0 &&
                    this.config.self_ordering_mode === "kiosk"))
        ) {
            return this.editedOrder;
        }
        const existingOrder = this.orders.find(
            (o) =>
                o.state === "draft" ||
                (o.state === "paid" &&
                    o.amount_total === 0 &&
                    this.config.self_ordering_mode === "kiosk")
        );
        if (!existingOrder) {
            const newOrder = this.models["pos.order"].create({
                session_id: this.session,
                company_id: this.company,
                config_id: this.config,
                sequence_number: this.session.sequence_number,
                access_token: uuidv4(),
                ticket_code: random5Chars(),
            });

            this.orders.push(newOrder);
            this.editedOrder = newOrder;
        } else {
            this.editedOrder = existingOrder;
        }

        return this.editedOrder;
    }

    initData() {
        this.session = this.data.models["pos.session"].getFirst();
        this.config = this.data.models["pos.config"].getFirst();
        this.company = this.data.models["res.company"].getFirst();
        this.currency = this.data.models["res.currency"].getFirst();

        // Custom data
        this.access_token = odoo.access_token;
        this.server_version = this.data.custom.server_version;
        this.base_url = this.data.custom.base_url;
        this.links = this.data.custom.links;
        this.models = this.data.models;
        this.color = getColor(this.company.color);
        this.currentLanguage = this.config.self_ordering_available_language_ids.find(
            (l) => l.code === cookie.get("frontend_lang")
        );

        if (this.config.self_ordering_default_language_id && !this.currentLanguage) {
            this.currentLanguage = this.config.self_ordering_default_language_id;
        }

        for (const product of this.models["product.product"].getAll()) {
            product.description_self_order = product.description_self_order
                ? markup(product.description_self_order)
                : "";
        }

        cookie.set("frontend_lang", this.currentLanguage?.code);
    }

    create_printer(printer) {
        const url = deduceUrl(printer.proxy_ip || "");
        return new HWPrinter({ url });
    }

    _getKioskPrintingCategoriesChanges(categories) {
        return this.currentOrder.lines.filter((orderline) =>
            categories.some((categId) =>
                this.productByIds[orderline["product_id"]].pos_categ_ids
                    .map((categ) => categ.id)
                    .includes(categId)
            )
        );
    }

    async printKioskChanges() {
        const d = new Date();
        let hours = "" + d.getHours();
        hours = hours.length < 2 ? "0" + hours : hours;
        let minutes = "" + d.getMinutes();
        minutes = minutes.length < 2 ? "0" + minutes : minutes;
        for (const printer of this.kitchenPrinters) {
            const orderlines = this._getKioskPrintingCategoriesChanges(
                Object.values(printer.config.product_categories_ids)
            );
            if (orderlines) {
                const printingChanges = {
                    new: orderlines,
                    tracker: this.currentOrder.table_stand_number,
                    trackingNumber: this.currentOrder.trackingNumber || "unknown number",
                    name: this.currentOrder.pos_reference || "unknown order",
                    time: {
                        hours,
                        minutes,
                    },
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

        this.idleTimout = false;
        window.addEventListener("click", (event) => {
            this.idleTimout && clearTimeout(this.idleTimout);
            this.idleTimout = setTimeout(() => {
                if (this.router.activeSlot !== "payment") {
                    this.router.navigate("default");
                }
            }, 5 * 1000 * 60);
        });
    }

    async initMobileData() {
        if (this.config.self_ordering_mode !== "qr_code") {
            if (this.session && this.access_token) {
                this.ordering = true;
            }

            if (!this.ordering) {
                return;
            }

            // effect(
            //     batched(
            //         (state) =>
            //             Array.isArray(state.orders) &&
            //             localStorage.setItem("orders", JSON.stringify(state.orders))
            //     ),
            //     [this]
            // );
            // const orders = JSON.parse(localStorage.getItem("orders")) ?? [];
            // this.orders.push(
            //     ...orders.map((o) => {
            //         o.lines = o.lines.filter((l) => this.productByIds[l.product_id]);
            //         return this.models["pos.order"].create(o);
            //     })
            // );
            await this.getOrdersFromServer();
            await this.getPricesFromServer();
        }
    }

    updateCategoryList() {
        let now = luxon.DateTime.now();
        now = now.hour + now.minute / 60;
        const productByCateg = this.models["product.product"].getAllBy("pos_categ_ids");
        const availableCategories = this.models["pos.category"]
            .sort((a, b) => a.sequence - b.sequence)
            .filter((c) => productByCateg[c.id])
            .sort((a, b) => categorySorter(a, b, this.config.iface_start_categ_id));
        this.categoryList = new Set(availableCategories);
        this.availableCategoryListIds = availableCategories
            .filter((c) => {
                return now > c.hour_after && now < c.hour_until;
            })
            .map((c) => c.id);
        this.currentCategory =
            this.models["pos.category"].length > 0 ? this.models["pos.category"].getFirst() : null;
    }

    isCategoryAvailable(categoryId) {
        return this.availableCategoryListIds.includes(categoryId);
    }

    cancelOrder() {
        const changes = this.currentOrder.uiState.lastChangesSent;
        const lines = this.currentOrder.lines;
        const keptLines = [];

        for (const line of lines) {
            const change = changes[line.uuid];

            if (change) {
                line.qty = change.qty;
                line.customer_note = change.customer_note;
                line.attribute_value_ids = change.attribute_value_ids;
                keptLines.push(line);
            }
        }

        this.currentOrder.lines = keptLines;

        if (this.currentOrder.totalQuantity === 0) {
            this.router.navigate("default");
            this.editedOrder = null;
            this.flushNotSentOrder();
        }
    }

    flushNotSentOrder() {
        this.orders = this.orders.filter((o) => o.isSavedOnServer);
    }

    async sendDraftOrderToServer() {
        if (this.currentOrder.isSavedOnServer || this.currentOrder.lines.length === 0) {
            return this.currentOrder;
        }

        try {
            const rpcUrl = this.currentOrder.isAlreadySent
                ? "/pos-self-order/update-existing-order"
                : `/pos-self-order/process-new-order/${this.config.self_ordering_mode}`;

            const order = await rpc(rpcUrl, {
                order: this.currentOrder,
                access_token: this.access_token,
                table_identifier: this.table ? this.table.identifier : null,
            });

            this.editedOrder.access_token = order.access_token;
            this.updateOrdersFromServer([order], [order.access_token]);
            this.editedOrder.updateLastChanges();

            if (this.config.self_ordering_pay_after === "each") {
                this.editedOrder = null;
            }

            return order;
        } catch (error) {
            this.handleErrorNotification(error, [this.editedOrder.access_token]);
            return false;
        }
    }

    async getOrdersFromServer() {
        const accessTokens = this.orders.map((order) => order.access_token).filter(Boolean);

        if (accessTokens.length === 0) {
            return;
        }

        try {
            const orders = await rpc(`/pos-self-order/get-orders/`, {
                access_token: this.access_token,
                order_access_tokens: accessTokens,
            });

            this.updateOrdersFromServer(orders, accessTokens);
            this.editedOrder = null;
        } catch (error) {
            this.handleErrorNotification(
                error,
                this.orders.map((order) => order.access_token)
            );
        }
    }

    updateOrdersFromServer(ordersFromServer, localAccessToken) {
        const accessTokensFromServer = ordersFromServer.map((order) => order.access_token);

        for (const order of this.orders) {
            if (order.access_token) {
                const orderFromServer = ordersFromServer.find(
                    (o) => o.access_token === order.access_token
                );
                if (orderFromServer) {
                    order.updateDataFromServer(orderFromServer);
                    const newLine = this.currentOrder.lines.find((l) => !l.id);
                    if (!newLine) {
                        order.updateLastChanges();
                    }
                }
            }
        }

        for (const index in this.orders) {
            if (
                !accessTokensFromServer.includes(this.orders[index].access_token) &&
                localAccessToken.includes(this.orders[index].access_token)
            ) {
                this.orders.splice(index, 1);
            }
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
            this.editedOrder = null;
            message = _t("Your order has been paid");
        } else if (state === "cancel") {
            this.editedOrder = null;
            message = _t("Your order has been cancelled");
        }

        this.notification.add(message, {
            type: "success",
        });
        this.router.navigate("default");
    }

    updateOrderFromServer(order) {
        this.currentOrder.updateDataFromServer(order);
    }

    isOrder() {
        if (!this.currentOrder || !this.currentOrder.lines.length) {
            this.router.navigate("default");
        }
    }

    async getPricesFromServer() {
        try {
            if (!this.currentOrder) {
                return;
            }
            if (this.priceLoading) {
                this.priceLoading.abort(false);
            }

            this.priceLoading = rpc(`/pos-self-order/get-orders-taxes/`, {
                order: this.currentOrder.serialize({ orm: true }),
                access_token: this.access_token,
            });
            await this.priceLoading.then((taxes) => {
                this.currentOrder.updateDataFromServer(taxes);
                this.priceLoading = false;
            });
        } catch (error) {
            this.handleErrorNotification(error);
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
            }
        } else if (error instanceof ConnectionLostError) {
            message = _t("Connection lost, please try again later");
        }

        this.notification.add(message, {
            type: "danger",
        });

        if (accessToken && cleanOrders) {
            this.editedOrder = null;

            for (const index in this.orders) {
                if (accessToken.includes(this.orders[index].access_token)) {
                    this.orders.splice(index, 1);
                }
            }
        }
    }

    formatMonetary(price) {
        return webFormatCurrency(price, this.currency_id);
    }

    handleProductChanges(payload) {
        const product = new Product(payload.product, this.config.iface_tax_included);
        this.productByIds[payload.product.id] = product;
        for (const categ of payload.product.pos_categ_ids) {
            if (!this.pos_category.map((c) => c.id).includes(categ.id)) {
                continue;
            }
            const index = this.productsGroupedByCategory[categ.id].findIndex(
                (p) => p.id === product.id
            );
            if (index >= 0) {
                this.productsGroupedByCategory[categ.id][index] = product;
            } else {
                this.productsGroupedByCategory[categ.id].push(product);
            }
        }
    }

    verifyCart() {
        let result = true;
        for (const line of this.currentOrder.hasNotAllLinesSent()) {
            if (line.combo_parent_uuid) {
                continue;
            }
            const alreadySent = this.currentOrder.uiState.lastChangesSent
                ? this.currentOrder.uiState.lastChangesSent[line.uuid]
                : false;
            const wrongChild = line.child_lines.find(
                (l) => !this.productByIds[l.product_id]?.self_order_available
            );
            if (wrongChild || !this.productByIds[line.product_id]?.self_order_available) {
                if (alreadySent) {
                    line.qty = alreadySent.qty;
                    line.customer_note = alreadySent.customer_note;
                    line.selected_attributes = alreadySent.selected_attributes;
                } else {
                    this.currentOrder.removeOrderline(line);
                }
                this.notification.add(
                    _t(
                        "%s is not available anymore, it has thus been removed from your order. Please review your order and validate it again.",
                        line.full_product_name
                    ),
                    { type: "danger" }
                );
                result = false;
            }
        }

        return result;
    }

    getProductDisplayPrice(product) {
        return product.get_price();
    }
    getLinePrice(line) {
        return this.config.iface_tax_included ? line.price_subtotal_incl : line.price_subtotal;
    }
    getSelectedAttributes(line) {
        const attributeValues = line.attribute_value_ids;
        const customAttr = line.custom_attribute_value_ids;
        return attributeFormatter(this.attributeById, attributeValues, customAttr);
    }
    getFullProductName(line) {
        const attrs = this.getSelectedAttributes(line);
        const attrsStr = " (" + attrs.map((a) => a.value).join(", ") + ")";
        return line.full_product_name + (attrs.length ? attrsStr : "");
    }
    getLineDisplayData(line) {
        return {
            productName: this.getFullProductName(line),
            price: this.formatMonetary(this.getLinePrice(line)),
            qty: line.qty.toString(),
            unitPrice: this.formatMonetary(this.getLinePrice(line) / line.qty),
            comboParent: line.combo_parent_uuid
                ? this.currentOrder.lines.find((l) => l.uuid === line.combo_parent_uuid)
                      .full_product_name
                : "",
            customerNote: line.customer_note,
        };
    }
    export_for_printing(order) {
        order.receiptDate ||= formatDateTime(luxon.DateTime.now());
        return {
            orderlines: order.lines.map(this.getLineDisplayData.bind(this)),
            amount_total: order.amount_total,
            amount_tax: order.amount_tax,
            total_without_tax: order.amount_total - order.amount_tax,
            total_paid: order.amount_paid,
            paymentlines: order.payment_lines,
            change: 0,
            tax_details: order.tax_details,
            name: order.pos_reference,
            date: order.receiptDate,
            ticket_code: this.company.point_of_sale_ticket_unique_code && order.ticketCode,
            base_url: this.base_url,
            footer: this.config.receipt_footer,
            headerData: {
                header: this.config.receipt_header,
                company: this.company,
                trackingNumber: order.trackingNumber,
                bigTrackingNumber: true,
                pickingService: this.config.self_ordering_service_mode,
                tableTracker: order.table_stand_number,
            },
            pos_qr_code:
                this.company.point_of_sale_use_ticket_qr_code &&
                qrCodeSrc(
                    `${this.base_url}/pos/ticket/validate?access_token=${order.access_token}`
                ),
        };
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
                data: this.export_for_printing(order),
                formatCurrency: this.formatMonetary,
            },
            {}
        );
        link.href = png.toDataURL().replace("data:image/jpeg;base64,", "");
        link.click();
    }
}

export const selfOrderService = {
    dependencies: [
        "notification",
        "router",
        "printer",
        "renderer",
        "barcode",
        "bus_service",
        "pos_data",
    ],
    async start(env, services) {
        return new SelfOrder(env, services).ready;
    },
};

registry.category("services").add("printer", printerService);
registry.category("services").add("self_order", selfOrderService);

export function useSelfOrder() {
    return useState(useService("self_order"));
}
