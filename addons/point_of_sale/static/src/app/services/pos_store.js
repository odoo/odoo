/* global waitForWebfonts */

import { Mutex } from "@web/core/utils/concurrency";
import { markRaw } from "@odoo/owl";
import { floatIsZero } from "@web/core/utils/numbers";
import { renderToElement } from "@web/core/utils/render";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { deduceUrl, random5Chars, uuidv4, getOnNotified, Counter } from "@point_of_sale/utils";
import { HWPrinter } from "@point_of_sale/app/utils/printer/hw_printer";
import { ConnectionAbortedError, ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { EditListPopup } from "@point_of_sale/app/components/popups/select_lot_popup/select_lot_popup";
import { ProductConfiguratorPopup } from "@point_of_sale/app/components/popups/product_configurator_popup/product_configurator_popup";
import { ComboConfiguratorPopup } from "@point_of_sale/app/components/popups/combo_configurator_popup/combo_configurator_popup";
import {
    makeAwaitable,
    ask,
    makeActionAwaitable,
} from "@point_of_sale/app/utils/make_awaitable_dialog";
import { PartnerList } from "../screens/partner_list/partner_list";
import { ScaleScreen } from "../screens/scale_screen/scale_screen";
import { computeComboItems } from "../models/utils/compute_combo_items";
import { changesToOrder, getOrderChanges } from "../models/utils/order_change";
import { QRPopup } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { ActionScreen } from "@point_of_sale/app/screens/action_screen";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { SelectionPopup } from "../components/popups/selection_popup/selection_popup";
import { user } from "@web/core/user";
import { fuzzyLookup } from "@web/core/utils/search";
import { unaccent } from "@web/core/utils/strings";
import { WithLazyGetterTrap } from "@point_of_sale/lazy_getter";

export class PosStore extends WithLazyGetterTrap {
    loadingSkipButtonIsShown = false;
    mainScreen = { name: null, component: null };

    static serviceDependencies = [
        "bus_service",
        "number_buffer",
        "barcode_reader",
        "hardware_proxy",
        "ui",
        "pos_data",
        "dialog",
        "notification",
        "printer",
        "action",
        "alert",
        "mail.sound_effects",
    ];
    constructor({ traps, env, deps }) {
        super({ traps });
        this.ready = this.setup(env, deps).then(() => this);
    }
    // use setup instead of constructor because setup can be patched.
    async setup(
        env,
        {
            number_buffer,
            hardware_proxy,
            barcode_reader,
            ui,
            dialog,
            notification,
            printer,
            bus_service,
            pos_data,
            action,
            alert,
        }
    ) {
        this.env = env;
        this.numberBuffer = number_buffer;
        this.barcodeReader = barcode_reader;
        this.ui = ui;
        this.dialog = dialog;
        this.printer = printer;
        this.bus = bus_service;
        this.data = pos_data;
        this.action = action;
        this.alert = alert;
        this.sound = env.services["mail.sound_effects"];
        this.notification = notification;
        this.unwatched = markRaw({});
        this.pushOrderMutex = new Mutex();

        // Object mapping the order's name (which contains the uuid) to it's server_id after
        // validation (order paid then sent to the backend).
        this.validated_orders_name_server_id_map = {};
        this.numpadMode = "quantity";
        this.mobile_pane = "right";
        this.ticket_screen_mobile_pane = "left";
        this.productListView = window.localStorage.getItem("productListView") || "grid";

        this.ticketScreenState = {
            offsetByDomain: {},
            totalCount: 0,
        };

        this.loadingOrderState = false; // used to prevent orders fetched to be put in the update set during the reactive change

        // Handle offline mode
        // All of Set of ids
        this.pendingOrder = {
            write: new Set(),
            delete: new Set(),
            create: new Set(),
        };

        this.synch = { status: "connected", pending: 0 };
        this.hardwareProxy = hardware_proxy;
        this.hiddenProductIds = new Set();
        this.selectedOrderUuid = null;
        this.selectedPartner = null;
        this.selectedCategory = null;
        this.searchProductWord = "";
        this.mainProductVariant = {};
        this.ready = new Promise((resolve) => {
            this.markReady = resolve;
        });
        this.isScaleScreenVisible = false;
        this.scaleData = null;
        this.scaleWeight = 0;
        this.scaleTare = 0;
        this.totalPriceOnScale = 0;

        this.orderCounter = new Counter(0);

        // FIXME POSREF: the hardwareProxy needs the pos and the pos needs the hardwareProxy. Maybe
        // the hardware proxy should just be part of the pos service?
        this.hardwareProxy.pos = this;
        this.syncingOrders = new Set();
        await this.initServerData();
        if (this.config.useProxy) {
            await this.connectToProxy();
        }
        this.closeOtherTabs();
    }

    get firstScreen() {
        if (odoo.from_backend) {
            // Remove from_backend params in the URL but keep the rest
            const url = new URL(window.location.href);
            url.searchParams.delete("from_backend");
            window.history.replaceState({}, "", url);

            if (!this.config.module_pos_hr) {
                this.setCashier(this.user);
            }
        }

        return !this.cashier ? "LoginScreen" : this.defaultScreen;
    }

    get defaultScreen() {
        return "ProductScreen";
    }

    async reloadData(fullReload = false) {
        await this.data.resetIndexedDB();
        const url = new URL(window.location.href);

        if (fullReload) {
            url.searchParams.set("limited_loading", "0");
        }

        window.location.href = url.href;
    }

    showLoginScreen() {
        this.resetCashier();
        this.showScreen("LoginScreen");
        this.dialog.closeAll();
    }

    resetCashier() {
        this.cashier = false;
        this._resetConnectedCashier();
    }

    checkPreviousLoggedCashier() {
        const savedCashier = this._getConnectedCashier();
        if (savedCashier) {
            this.setCashier(savedCashier);
        }
    }

    setCashier(user) {
        if (!user) {
            return;
        }

        this.cashier = user;
        this._storeConnectedCashier(user);
    }

    getProductPrice(product, price = false, formatted = false) {
        const order = this.getOrder();
        const fiscalPosition = order.fiscal_position_id || this.config.fiscal_position_id;
        const pricelist = order.pricelist_id || this.config.pricelist_id;
        const pPrice = product.getProductPrice(price, pricelist, fiscalPosition);

        if (formatted) {
            const formattedPrice = this.env.utils.formatCurrency(pPrice);
            if (product.to_weight) {
                return `${formattedPrice}/${product.uom_id.name}`;
            } else {
                return formattedPrice;
            }
        }

        return pPrice;
    }

    _getConnectedCashier() {
        const cashier_id = Number(sessionStorage.getItem(`connected_cashier_${this.config.id}`));
        if (cashier_id && this.models["res.users"].get(cashier_id)) {
            return this.models["res.users"].get(cashier_id);
        }
        return false;
    }

    _storeConnectedCashier(user) {
        sessionStorage.setItem(`connected_cashier_${this.config.id}`, user.id);
    }

    _resetConnectedCashier() {
        sessionStorage.removeItem(`connected_cashier_${this.config.id}`);
    }

    async initServerData() {
        await this.processServerData();
        this.onNotified = getOnNotified(this.bus, this.config.access_token);
        return await this.afterProcessServerData();
    }

    get session() {
        return this.data.models["pos.session"].getFirst();
    }

    async processServerData() {
        // These fields should be unique for the pos_config
        // and should not change during the session, so we can
        // safely take the first element.this.models
        this.config = this.data.models["pos.config"].getFirst();
        this.company = this.data.models["res.company"].getFirst();
        this.user = this.data.models["res.users"].getFirst();
        this.currency = this.config.currency_id;
        this.pickingType = this.data.models["stock.picking.type"].getFirst();
        this.models = this.data.models;

        // Check cashier
        this.checkPreviousLoggedCashier();

        // Add Payment Interface to Payment Method
        for (const pm of this.models["pos.payment.method"].getAll()) {
            const PaymentInterface = this.electronic_payment_interfaces[pm.use_payment_terminal];
            if (PaymentInterface) {
                pm.payment_terminal = new PaymentInterface(this, pm);
            }
        }

        // Create printer with hardware proxy, this will override related model data
        this.unwatched.printers = [];
        for (const relPrinter of this.models["pos.printer"].getAll()) {
            const printer = relPrinter.serialize();
            const HWPrinter = this.createPrinter(printer);

            HWPrinter.config = printer;
            this.unwatched.printers.push(HWPrinter);
        }
        this.config.iface_printers = !!this.unwatched.printers.length;

        // Monitor product pricelist
        this.models["product.product"].addEventListener(
            "create",
            this.computeProductPricelistCache.bind(this)
        );
        this.models["product.pricelist.item"].addEventListener("create", () => {
            const order = this.getOrder();
            if (!order) {
                return;
            }
            const currentPricelistId = order.pricelist_id?.id;
            order.setPricelist(this.models["product.pricelist"].get(currentPricelistId));
        });

        await this.processProductAttributes();
    }
    cashMove() {
        this.hardwareProxy.openCashbox(_t("Cash in / out"));
        return makeAwaitable(this.dialog, CashMovePopup);
    }
    async closeSession() {
        const info = await this.getClosePosInfo();

        if (info) {
            this.dialog.add(ClosePosPopup, info);
        }
    }
    async processProductAttributes() {
        const productIds = new Set();
        const productTmplIds = new Set();
        const productByTmplId = {};

        for (const product of this.models["product.product"].getAll()) {
            if (product.product_template_variant_value_ids.length > 0) {
                productTmplIds.add(product.raw.product_tmpl_id);
                productIds.add(product.id);

                if (!productByTmplId[product.raw.product_tmpl_id]) {
                    productByTmplId[product.raw.product_tmpl_id] = [];
                }

                productByTmplId[product.raw.product_tmpl_id].push(product);
            }
        }

        if (productIds.size > 0) {
            try {
                await this.data.searchRead("product.product", [
                    "&",
                    ["id", "not in", [...productIds]],
                    ["product_tmpl_id", "in", [...productTmplIds]],
                ]);
            } catch (error) {
                console.warn("Error while fetching product variants", error);
            }
        }

        for (const product of this.models["product.product"].filter(
            (p) => !productIds.has(p.id) && p.product_template_variant_value_ids.length > 0
        )) {
            productByTmplId[product.raw.product_tmpl_id].push(product);
        }

        for (const products of Object.values(productByTmplId)) {
            const nbrProduct = products.length;

            for (let i = 0; i < nbrProduct - 1; i++) {
                products[i].available_in_pos = false;
                this.mainProductVariant[products[i].id] = products[nbrProduct - 1];
            }
        }
    }

    async onDeleteOrder(order) {
        if (order.getOrderlines().length > 0) {
            const confirmed = await ask(this.dialog, {
                title: _t("Existing orderlines"),
                body: _t(
                    "%s has a total amount of %s, are you sure you want to delete this order?",
                    order.pos_reference,
                    this.env.utils.formatCurrency(order.getTotalWithTax())
                ),
            });
            if (!confirmed) {
                return false;
            }
        }
        const orderIsDeleted = await this.deleteOrders([order]);
        if (orderIsDeleted) {
            order.uiState.displayed = false;
            await this.afterOrderDeletion();
        }
        return orderIsDeleted;
    }
    async afterOrderDeletion() {
        this.setOrder(this.getOpenOrders().at(-1) || this.addNewOrder());
    }

    async deleteOrders(orders, serverIds = []) {
        const ids = new Set();
        for (const order of orders) {
            if (order && (await this._onBeforeDeleteOrder(order))) {
                if (
                    typeof order.id === "number" &&
                    Object.keys(order.last_order_preparation_change).length > 0 &&
                    !order.isTransferedOrder
                ) {
                    await this.sendOrderInPreparation(order, true);
                }

                const cancelled = this.removeOrder(order, true);
                this.removePendingOrder(order);
                if (!cancelled) {
                    return false;
                } else if (typeof order.id === "number") {
                    ids.add(order.id);
                }
            }
        }

        if (serverIds.length > 0) {
            for (const id of serverIds) {
                if (typeof id !== "number") {
                    continue;
                }
                ids.add(id);
            }
        }

        if (ids.size > 0) {
            await this.data.call("pos.order", "action_pos_order_cancel", [Array.from(ids)]);
        }

        return true;
    }
    /**
     * Override to do something before deleting the order.
     * Make sure to return true to proceed on deleting the order.
     * @param {*} order
     * @returns {boolean}
     */
    async _onBeforeDeleteOrder(order) {
        return true;
    }
    computeProductPricelistCache(data) {
        if (!data) {
            return;
        }

        let products = this.models[data.model].readMany(data.ids);
        if (data.model === "product.template") {
            products = products.flatMap((p) => p.product_variant_ids);
        }

        this._loadMissingPricelistItems(products);
    }

    async _loadMissingPricelistItems(products) {
        if (!products.length) {
            return;
        }

        const product_tmpl_ids = products
            .filter((p) => typeof p.id === "number")
            .map((product) => product.product_tmpl_id.id);
        const product_ids = products
            .filter((p) => typeof p.id === "number")
            .map((product) => product.id);
        await this.data.callRelated("pos.session", "get_pos_ui_product_pricelist_item_by_product", [
            odoo.pos_session_id,
            product_tmpl_ids,
            product_ids,
            this.config.id,
        ]);
    }

    async afterProcessServerData() {
        // Adding the not synced paid orders to the pending orders
        const paidUnsyncedOrderIds = this.models["pos.order"]
            .filter((order) => order.isUnsyncedPaid)
            .map((order) => order.id);

        if (paidUnsyncedOrderIds.length > 0) {
            this.addPendingOrder(paidUnsyncedOrderIds);
        }

        const openOrders = this.data.models["pos.order"].filter((order) => !order.finalized);
        this.syncAllOrders();

        if (!this.config.module_pos_restaurant) {
            this.selectedOrderUuid = openOrders.length
                ? openOrders[openOrders.length - 1].uuid
                : this.addNewOrder().uuid;
        }

        this.markReady();
        this.showScreen(this.firstScreen);
    }

    get productListViewMode() {
        const viewMode = this.productListView && this.ui.isSmall ? this.productListView : "grid";
        if (viewMode === "grid") {
            return "d-grid gap-2";
        } else {
            return "";
        }
    }
    get productViewMode() {
        const viewMode = this.productListView && this.ui.isSmall ? this.productListView : "grid";
        if (viewMode === "grid") {
            return "flex-column";
        } else {
            return "flex-row-reverse justify-content-between m-1";
        }
    }
    async openConfigurator(pTemplate) {
        const attrById = this.models["product.attribute"].getAllBy("id");
        const attributeLines = pTemplate.attribute_line_ids.filter(
            (attr) => attr.attribute_id?.id in attrById
        );
        const attributeLinesValues = attributeLines.map((attr) => attr.product_template_value_ids);
        if (attributeLinesValues.some((values) => values.length > 1 || values[0].is_custom)) {
            return await makeAwaitable(this.dialog, ProductConfiguratorPopup, {
                productTemplate: pTemplate,
            });
        }
        return {
            attribute_value_ids: attributeLinesValues.map((values) => values[0].id),
            attribute_custom_values: [],
            price_extra: attributeLinesValues
                .filter((attr) => attr[0].attribute_id.create_variant !== "always")
                .reduce((acc, values) => acc + values[0].price_extra, 0),
            quantity: 1,
        };
    }
    getDefaultSearchDetails() {
        let field = "RECEIPT_NUMBER";
        let term = "";
        if (this.getOrder()?.getPartner()) {
            field = "PARTNER";
            term = this.getOrder().getPartner().name;
        }
        return {
            fieldName: field,
            searchTerm: term,
        };
    }

    async setTip(tip) {
        const currentOrder = this.getOrder();
        const tipProduct = this.config.tip_product_id;
        let line = currentOrder.lines.find((line) => line.product_id.id === tipProduct.id);

        if (line) {
            line.setUnitPrice(tip);
        } else {
            line = await this.addLineToCurrentOrder(
                {
                    product_id: tipProduct,
                    price_unit: tip,
                    product_tmpl_id: tipProduct.product_tmpl_id,
                },
                {}
            );
        }

        currentOrder.is_tipped = true;
        currentOrder.tip_amount = tip;
        return line;
    }

    selectOrderLine(order, line) {
        order.selectOrderline(line);
        this.numpadMode = "quantity";
    }
    // This method should be called every time a product is added to an order.
    // The configure parameter is available if the orderline already contains all
    // the information without having to be calculated. For example, importing a SO.
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        let merge = true;
        let order = this.getOrder();
        order.assertEditable();

        if (!order) {
            order = await this.addNewOrder();
        }

        const options = {
            ...opts,
        };

        if ("price_unit" in vals) {
            merge = false;
        }

        const productTemplate = vals.product_tmpl_id;
        const values = {
            price_type: "price_unit" in vals ? "manual" : "original",
            price_extra: 0,
            price_unit: 0,
            order_id: this.getOrder(),
            qty: this.getOrder().preset_id?.is_return ? -1 : 1,
            tax_ids: productTemplate.taxes_id.map((tax) => ["link", tax]),
            product_id: productTemplate.product_variant_ids[0],
            ...vals,
        };

        // Handle refund constraints
        if (
            order.doNotAllowRefundAndSales() &&
            order._isRefundOrder() &&
            (!values.qty || values.qty > 0)
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Refund and Sales not allowed"),
                body: _t("It is not allowed to mix refunds and sales"),
            });
            return;
        }

        // In case of configurable product a popup will be shown to the user
        // We assign the payload to the current values object.
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (productTemplate.isConfigurable() && configure) {
            const payload = await this.openConfigurator(productTemplate);

            if (payload) {
                // Find candidate based on instantly created variants.
                const attributeValues = this.models["product.template.attribute.value"]
                    .readMany(payload.attribute_value_ids)
                    .map((value) => value.id);

                let candidate = productTemplate.product_variant_ids.find((variant) => {
                    const attributeIds = variant.product_template_variant_value_ids.map(
                        (value) => value.id
                    );
                    return (
                        attributeValues.every((id) => attributeIds.includes(id)) &&
                        attributeValues.length
                    );
                });

                const isDynamic = productTemplate.attribute_line_ids.some(
                    (line) => line.attribute_id.create_variant === "dynamic"
                );

                if (!candidate && isDynamic) {
                    // Need to create the new product.
                    const result = await this.data.callRelated(
                        "product.template",
                        "create_product_variant_from_pos",
                        [productTemplate.id, payload.attribute_value_ids, this.config.id]
                    );
                    candidate = result["product.product"][0];
                }

                Object.assign(values, {
                    attribute_value_ids: payload.attribute_value_ids.map((id) => [
                        "link",
                        this.models["product.template.attribute.value"].get(id),
                    ]),
                    custom_attribute_value_ids: Object.entries(payload.attribute_custom_values).map(
                        ([id, cus]) => [
                            "create",
                            {
                                custom_product_template_attribute_value_id:
                                    this.models["product.template.attribute.value"].get(id),
                                custom_value: cus,
                            },
                        ]
                    ),
                    price_extra: values.price_extra + payload.price_extra,
                    qty: payload.qty || values.qty,
                    product_id: candidate || productTemplate.product_variant_ids[0],
                });
            } else {
                return;
            }
        } else if (values.product_id.product_template_variant_value_ids.length > 0) {
            // Verify price extra of variant products
            const priceExtra = values.product_id.product_template_variant_value_ids
                .filter((attr) => attr.attribute_id.create_variant !== "always")
                .reduce((acc, attr) => acc + attr.price_extra, 0);

            values.price_extra += priceExtra;
            values.attribute_value_ids = values.product_id.product_template_variant_value_ids.map(
                (attr) => ["link", attr]
            );
        }

        // In case of clicking a combo product a popup will be shown to the user
        // It will return the combo prices and the selected products
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (values.product_tmpl_id.isCombo() && configure) {
            const payload = await makeAwaitable(this.dialog, ComboConfiguratorPopup, {
                productTemplate: values.product_tmpl_id,
            });

            if (!payload) {
                return;
            }

            // Product template of combo should not have more than 1 variant.
            const comboPrices = computeComboItems(
                values.product_tmpl_id.product_variant_ids[0],
                payload,
                order.pricelist_id,
                this.data.models["decimal.precision"].getAll(),
                this.data.models["product.template.attribute.value"].getAllBy("id")
            );

            values.combo_line_ids = comboPrices.map((comboItem) => [
                "create",
                {
                    product_id: comboItem.combo_item_id.product_id,
                    tax_ids: comboItem.combo_item_id.product_id.taxes_id.map((tax) => [
                        "link",
                        tax,
                    ]),
                    combo_item_id: comboItem.combo_item_id,
                    price_unit: comboItem.price_unit,
                    price_type: "manual",
                    order_id: order,
                    qty: 1,
                    attribute_value_ids: comboItem.attribute_value_ids?.map((attr) => [
                        "link",
                        attr,
                    ]),
                    custom_attribute_value_ids: Object.entries(
                        comboItem.attribute_custom_values
                    ).map(([id, cus]) => [
                        "create",
                        {
                            custom_product_template_attribute_value_id:
                                this.data.models["product.template.attribute.value"].get(id),
                            custom_value: cus,
                        },
                    ]),
                },
            ]);
        }

        // In the case of a product with tracking enabled, we need to ask the user for the lot/serial number.
        // It will return an instance of pos.pack.operation.lot
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        const code = opts.code;
        if (values.product_tmpl_id.isTracked() && (configure || code)) {
            let pack_lot_ids = {};
            const packLotLinesToEdit =
                (!values.product_tmpl_id.isAllowOnlyOneLot() &&
                    this.getOrder()
                        .getOrderlines()
                        .filter((line) => !line.getDiscount())
                        .find((line) => line.product_id.id === values.product_id.id)
                        ?.getPackLotLinesToEdit()) ||
                [];

            // if the lot information exists in the barcode, we don't need to ask it from the user.
            if (code && code.type === "lot") {
                // consider the old and new packlot lines
                const modifiedPackLotLines = Object.fromEntries(
                    packLotLinesToEdit.filter((item) => item.id).map((item) => [item.id, item.text])
                );
                const newPackLotLines = [{ lot_name: code.code }];
                pack_lot_ids = { modifiedPackLotLines, newPackLotLines };
            } else {
                pack_lot_ids = await this.editLots(values.product_id, packLotLinesToEdit);
            }

            if (!pack_lot_ids) {
                return;
            } else {
                const packLotLine = pack_lot_ids.newPackLotLines;
                values.pack_lot_ids = packLotLine.map((lot) => ["create", lot]);
            }
        }

        // In case of clicking a product with tracking weight enabled a popup will be shown to the user
        // It will return the weight of the product as quantity
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (values.product_tmpl_id.to_weight && this.config.iface_electronic_scale && configure) {
            if (values.product_tmpl_id.isScaleAvailable) {
                this.isScaleScreenVisible = true;
                this.scaleData = {
                    productName: values?.product_id?.display_name,
                    uomName: values.product_tmpl_id.uom_id?.name,
                    uomRounding: values.product_tmpl_id.uom_id?.rounding,
                    productPrice: this.getProductPrice(values.product_id),
                };
                const weight = await makeAwaitable(
                    this.env.services.dialog,
                    ScaleScreen,
                    this.scaleData
                );
                if (weight) {
                    values.qty = weight;
                }
                this.isScaleScreenVisible = false;
                this.scaleWeight = 0;
                this.scaleTare = 0;
                this.totalPriceOnScale = 0;
            } else {
                await values.product_tmpl_id._onScaleNotAvailable();
            }
        }

        // Handle price unit
        if (!values.product_tmpl_id.isCombo() && vals.price_unit === undefined) {
            values.price_unit = values.product_id.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra,
                false,
                values.product_id
            );
        }
        const isScannedProduct = opts.code && opts.code.type === "product";
        if (values.price_extra && !isScannedProduct) {
            const price = values.product_tmpl_id.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra
            );

            values.price_unit = price;
        }

        const line = this.data.models["pos.order.line"].create({ ...values, order_id: order });
        line.setOptions(options);
        this.selectOrderLine(order, line);
        this.numberBuffer.reset();

        const selectedOrderline = order.getSelectedOrderline();
        if (options.draftPackLotLines && configure) {
            selectedOrderline.setPackLotLines({
                ...options.draftPackLotLines,
                setQuantity: options.quantity === undefined,
            });
        }

        let to_merge_orderline;
        for (const curLine of order.lines) {
            if (curLine.id !== line.id) {
                if (curLine.canBeMergedWith(line) && merge !== false) {
                    to_merge_orderline = curLine;
                }
            }
        }

        if (to_merge_orderline) {
            to_merge_orderline.merge(line);
            line.delete();
            this.selectOrderLine(order, to_merge_orderline);
        } else if (!selectedOrderline) {
            this.selectOrderLine(order, order.getLastOrderline());
        }

        this.numberBuffer.reset();

        // FIXME: Put this in an effect so that we don't have to call it manually.
        order.recomputeOrderData();

        this.numberBuffer.reset();

        this.hasJustAddedProduct = true;
        clearTimeout(this.productReminderTimeout);
        this.productReminderTimeout = setTimeout(() => {
            this.hasJustAddedProduct = false;
        }, 3000);

        this.addPendingOrder([order.id]);
        return order.getSelectedOrderline();
    }

    createPrinter(config) {
        const url = deduceUrl(config.proxy_ip || "");
        return new HWPrinter({ url });
    }
    async _loadFonts() {
        return new Promise(function (resolve, reject) {
            // Waiting for fonts to be loaded to prevent receipt printing
            // from printing empty receipt while loading Inconsolata
            // ( The font used for the receipt )
            waitForWebfonts(["Lato", "Inconsolata"], function () {
                resolve();
            });
            // The JS used to detect font loading is not 100% robust, so
            // do not wait more than 5sec
            setTimeout(resolve, 5000);
        });
    }

    setSelectedCategory(categoryId) {
        if (categoryId === this.selectedCategory?.id) {
            if (this.selectedCategory.parent_id) {
                this.selectedCategory = this.selectedCategory.parent_id;
            } else {
                this.selectedCategory = this.models["pos.category"].get(0);
            }
        } else {
            this.selectedCategory = this.models["pos.category"].get(categoryId);
        }
    }
    setScaleWeight(weight) {
        this.scaleWeight = weight;
    }
    setScaleTare(tare) {
        this.scaleTare = tare;
    }

    /**
     * Remove the order passed in params from the list of orders
     * @param order
     */
    removeOrder(order, removeFromServer = true) {
        if (this.config.isShareable || removeFromServer) {
            if (typeof order.id === "number" && !order.finalized) {
                this.addPendingOrder([order.id], true);
            }
        }

        if (typeof order.id === "string" && order.finalized) {
            this.addPendingOrder([order.id]);
            return;
        }

        return this.data.localDeleteCascade(order, removeFromServer);
    }

    /**
     * Return the current cashier (in this case, the user)
     * @returns {name: string, id: int, role: string}
     */
    getCashier() {
        this.user.role = this.user._raw.role;
        return this.user;
    }
    getCashierUserId() {
        return this.user.id;
    }
    cashierHasPriceControlRights() {
        return !this.config.restrict_price_control || this.getCashier()._role == "manager";
    }
    createNewOrder(data = {}) {
        const fiscalPosition = this.models["account.fiscal.position"].find(
            (fp) => fp.id === this.config.default_fiscal_position_id?.id
        );

        const order = this.models["pos.order"].create({
            session_id: this.session,
            company_id: this.company,
            config_id: this.config,
            picking_type_id: this.pickingType,
            user_id: this.user,
            access_token: uuidv4(),
            ticket_code: random5Chars(),
            fiscal_position_id: fiscalPosition,
            tracking_number: "",
            sequence_number: 0,
            pos_reference: "",
            ...data,
        });

        this.getNextOrderRefs(order);
        order.setPricelist(this.config.pricelist_id);

        if (this.config.use_presets) {
            this.selectPreset(this.config.default_preset_id, order);
        }

        order.recomputeOrderData();

        return order;
    }
    addNewOrder(data = {}) {
        if (this.getOrder()) {
            this.getOrder().updateSavedQuantity();
        }
        const order = this.createOrderIfNeeded(data);
        this.selectedOrderUuid = order.uuid;
        this.searchProductWord = "";
        this.mobile_pane = "right";
        return order;
    }
    createOrderIfNeeded(data) {
        return this.createNewOrder(data);
    }
    async getNextOrderRefs(order) {
        try {
            const [pos_reference, sequence_number, tracking_number] = await this.data.call(
                "pos.session",
                "get_next_order_refs",
                [[this.session.id], parseInt(odoo.login_number, 10), null, ""]
            );
            order.pos_reference = pos_reference;
            order.sequence_number = sequence_number;
            order.tracking_number = tracking_number;
            return true;
        } catch (error) {
            if (
                error instanceof ConnectionLostError ||
                error instanceof ConnectionAbortedError ||
                error instanceof RPCError
            ) {
                return this.getNextOrderRefsLocal(_t("Order"), order);
            } else {
                throw error;
            }
        } finally {
            this.data.synchronizeLocalDataInIndexedDB();
        }
    }
    /**
     * Return value of this method is used when the client is offline.
     * Side-effect: increments the order counter.
     */
    getNextOrderRefsLocal(refPrefix, order) {
        const sequenceNumber = this.orderCounter.next();
        const trackingNumber = sequenceNumber.toString().padStart(3, "0");
        const YY = new Date().getFullYear().toString().slice(-2);
        const LL = (odoo.login_number % 100).toString().padStart(2, "0");
        const SSS = this.session.id.toString().padStart(3, "0");
        const F = "1";
        const OOOO = sequenceNumber.toString().padStart(4, "0");
        const posReference = `${refPrefix} ${YY}${LL}-${SSS}-${F}${OOOO}`;
        order.pos_reference = posReference;
        order.sequence_number = sequenceNumber;
        order.tracking_number = trackingNumber;
        return true;
    }
    selectNextOrder() {
        const orders = this.models["pos.order"].filter((order) => !order.finalized);
        if (orders.length > 0) {
            this.selectedOrderUuid = orders[0].uuid;
        } else {
            return this.addNewOrder();
        }
    }

    addPendingOrder(orderIds, remove = false) {
        if (remove) {
            for (const id of orderIds) {
                this.pendingOrder["create"].delete(id);
                this.pendingOrder["write"].delete(id);
            }

            this.pendingOrder["delete"].add(...orderIds);
            return true;
        }

        for (const id of orderIds) {
            if (typeof id === "number") {
                this.pendingOrder["write"].add(id);
            } else {
                this.pendingOrder["create"].add(id);
            }
        }

        return true;
    }

    getPendingOrder() {
        const orderToCreate = this.models["pos.order"].filter(
            (order) =>
                this.pendingOrder.create.has(order.id) &&
                (order.lines.length > 0 ||
                    order.payment_ids.some((p) => p.payment_method_id.type === "pay_later"))
        );
        const orderToUpdate = this.models["pos.order"].readMany(
            Array.from(this.pendingOrder.write)
        );
        const orderToDelele = this.models["pos.order"].readMany(
            Array.from(this.pendingOrder.delete)
        );

        return {
            orderToDelele,
            orderToCreate,
            orderToUpdate,
        };
    }

    getOrderIdsToDelete() {
        return [...this.pendingOrder.delete];
    }

    removePendingOrder(order) {
        this.pendingOrder["create"].delete(order.id);
        this.pendingOrder["write"].delete(order.id);
        this.pendingOrder["delete"].delete(order.id);
        return true;
    }

    clearPendingOrder() {
        this.pendingOrder = {
            create: new Set(),
            write: new Set(),
            delete: new Set(),
        };
    }

    getSyncAllOrdersContext(orders, options = {}) {
        return {
            config_id: this.config.id,
            login_number: odoo.login_number,
        };
    }

    // There for override
    preSyncAllOrders(orders) {}
    postSyncAllOrders(orders) {}
    async syncAllOrders(options = {}) {
        const { orderToCreate, orderToUpdate } = this.getPendingOrder();
        let orders = [...orderToCreate, ...orderToUpdate];

        // Filter out orders that are already being synced
        orders = orders.filter((order) => !this.syncingOrders.has(order.id));

        try {
            const orderIdsToDelete = this.getOrderIdsToDelete();
            if (orderIdsToDelete.length > 0) {
                await this.deleteOrders([], orderIdsToDelete);
            }

            const context = this.getSyncAllOrdersContext(orders, options);
            this.preSyncAllOrders(orders);

            // Allow us to force the sync of the orders In the case of
            // pos_restaurant is usefull to get unsynced orders
            // for a specific table
            if (orders.length === 0 && !context.force) {
                return;
            }

            // Add order IDs to the syncing set
            orders.forEach((order) => this.syncingOrders.add(order.id));

            // Re-compute all taxes, prices and other information needed for the backend
            for (const order of orders) {
                order.recomputeOrderData();
            }

            const serializedOrder = orders.map((order) =>
                order.serialize({ orm: true, clear: true })
            );
            const data = await this.data.call("pos.order", "sync_from_ui", [serializedOrder], {
                context,
            });
            const missingRecords = await this.data.missingRecursive(data);
            const newData = this.models.loadData(this.models, missingRecords);

            for (const line of newData["pos.order.line"]) {
                const refundedOrderLine = line.refunded_orderline_id;

                if (refundedOrderLine) {
                    const order = refundedOrderLine.order_id;
                    delete order.uiState.lineToRefund[refundedOrderLine.uuid];
                    refundedOrderLine.refunded_qty += Math.abs(line.qty);
                }
            }

            this.postSyncAllOrders(newData["pos.order"]);

            if (data["pos.session"].length > 0) {
                // Replace the original session by the rescue one. And the rescue one will have
                // a higher id than the original one since it's the last one created.
                const session = this.models["pos.session"].sort((a, b) => a.id - b.id)[0];
                session.delete();
                this.models["pos.order"]
                    .getAll()
                    .filter((order) => order.state === "draft")
                    .forEach((order) => (order.session_id = this.session));
            }

            this.clearPendingOrder();
            return newData["pos.order"];
        } catch (error) {
            if (options.throw) {
                throw error;
            }

            console.warn("Offline mode active, order will be synced later");
            return error;
        } finally {
            orders.forEach((order) => this.syncingOrders.delete(order.id));
        }
    }

    pushSingleOrder(order) {
        return this.pushOrderMutex.exec(() => this.syncAllOrders(order));
    }

    setLoadingOrderState(bool) {
        this.loadingOrderState = bool;
    }
    async pay() {
        const currentOrder = this.getOrder();

        if (!currentOrder.canPay()) {
            return;
        }

        if (
            currentOrder.lines.some(
                (line) => line.getProduct().tracking !== "none" && !line.hasValidProductLot()
            ) &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots)
        ) {
            const confirmed = await ask(this.env.services.dialog, {
                title: _t("Some Serial/Lot Numbers are missing"),
                body: _t(
                    "You are trying to sell products with serial/lot numbers, but some of them are not set.\nWould you like to proceed anyway?"
                ),
            });
            if (confirmed) {
                this.mobile_pane = "right";
                this.showScreen("PaymentScreen", {
                    orderUuid: this.selectedOrderUuid,
                });
            }
        } else {
            this.mobile_pane = "right";
            this.showScreen("PaymentScreen", {
                orderUuid: this.selectedOrderUuid,
            });
        }
    }
    async getServerOrders() {
        await this.syncAllOrders();
        return await this.loadServerOrders([
            ["config_id", "in", [...this.config.raw.trusted_config_ids, this.config.id]],
            ["state", "=", "draft"],
        ]);
    }
    async loadServerOrders(domain) {
        const orders = await this.data.searchRead("pos.order", domain);
        for (const order of orders) {
            order.config_id = this.config;
            order.session_id = this.session;
        }
        return orders;
    }
    async getProductInfo(productTemplate, quantity, priceExtra = 0, productProduct = false) {
        const order = this.getOrder();
        // check back-end method `get_product_info_pos` to see what it returns
        // We do this so it's easier to override the value returned and use it in the component template later
        const productInfo = await this.data.call("product.template", "get_product_info_pos", [
            [productTemplate?.id],
            productTemplate.getPrice(order.pricelist_id, quantity, priceExtra, false),
            quantity,
            this.config.id,
            productProduct?.id,
        ]);

        const priceWithoutTax = productInfo["all_prices"]["price_without_tax"];
        const margin = priceWithoutTax - productTemplate.standard_price;
        const orderPriceWithoutTax = order.getTotalWithoutTax();
        const orderCost = order.getTotalCost();
        const orderMargin = orderPriceWithoutTax - orderCost;

        const costCurrency = this.env.utils.formatCurrency(productTemplate.standard_price);
        const marginCurrency = this.env.utils.formatCurrency(margin);
        const marginPercent = priceWithoutTax
            ? Math.round((margin / priceWithoutTax) * 10000) / 100
            : 0;
        const orderPriceWithoutTaxCurrency = this.env.utils.formatCurrency(orderPriceWithoutTax);
        const orderCostCurrency = this.env.utils.formatCurrency(orderCost);
        const orderMarginCurrency = this.env.utils.formatCurrency(orderMargin);
        const orderMarginPercent = orderPriceWithoutTax
            ? Math.round((orderMargin / orderPriceWithoutTax) * 10000) / 100
            : 0;
        return {
            costCurrency,
            marginCurrency,
            marginPercent,
            orderPriceWithoutTaxCurrency,
            orderCostCurrency,
            orderMarginCurrency,
            orderMarginPercent,
            productInfo,
        };
    }
    async getClosePosInfo() {
        return await this.data.call("pos.session", "get_closing_control_data", [[this.session.id]]);
    }
    // return the current order
    getOrder() {
        if (!this.selectedOrderUuid) {
            return undefined;
        }

        return this.models["pos.order"].getBy("uuid", this.selectedOrderUuid);
    }
    get selectedOrder() {
        return this.getOrder();
    }

    // change the current order
    setOrder(order, options) {
        if (this.getOrder()) {
            this.getOrder().updateSavedQuantity();
        }
        this.selectedOrderUuid = order?.uuid;
    }

    // return the list of unpaid orders
    getOpenOrders() {
        return this.models["pos.order"].filter((o) => !o.finalized);
    }

    // To be used in the context of closing the POS
    // Saves the order locally and try to send it to the backend.
    // If there is an error show a popup
    async pushOrdersWithClosingPopup(opts = {}) {
        try {
            await this.syncAllOrders(opts);
            return true;
        } catch (error) {
            console.warn(error);
            const reason = this.failed
                ? _t(
                      "Some orders could not be submitted to " +
                          "the server due to configuration errors. " +
                          "You can exit the Point of Sale, but do " +
                          "not close the session before the issue " +
                          "has been resolved."
                  )
                : _t(
                      "Some orders could not be submitted to " +
                          "the server due to internet connection issues. " +
                          "You can exit the Point of Sale, but do " +
                          "not close the session before the issue " +
                          "has been resolved."
                  );
            await ask(this.dialog, {
                title: _t("Offline Orders"),
                body: reason,
            });
            return false;
        }
    }

    /**
     * @param {str} terminalName
     */
    getPendingPaymentLine(terminalName) {
        for (const order of this.models["pos.order"].getAll()) {
            const paymentLine = order.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.use_payment_terminal === terminalName &&
                    !paymentLine.isDone()
            );
            if (paymentLine) {
                return paymentLine;
            }
        }
    }

    get linesToRefund() {
        return this.models["pos.order"].reduce((acc, order) => {
            acc.push(...Object.values(order.uiState.lineToRefund));
            return acc;
        }, []);
    }

    isProductQtyZero(qty) {
        const dp = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit of Measure"
        );
        return floatIsZero(qty, dp.digits);
    }

    disallowLineQuantityChange() {
        return false;
    }

    switchPane() {
        this.mobile_pane = this.mobile_pane === "left" ? "right" : "left";
    }
    switchPaneTicketScreen() {
        this.ticket_screen_mobile_pane =
            this.ticket_screen_mobile_pane === "left" ? "right" : "left";
    }
    async logEmployeeMessage(action, message) {
        await this.data.call(
            "pos.session",
            "log_partner_message",
            [this.session.id, this.user.partner_id.id, action, message],
            {},
            true
        );
    }
    showScreen(name, props = {}, newOrder = false) {
        if (name === "ProductScreen") {
            this.getOrder()?.deselectOrderline();
        }
        this.previousScreen = this.mainScreen.component?.name;
        const component = registry.category("pos_screens").get(name);
        this.mainScreen = { component, props };
        // Save the screen to the order so that it is shown again when the order is selected.
        if (component.storeOnOrder ?? true) {
            this.getOrder()?.setScreenData({ name, props });
        }
        if (newOrder) {
            this.addNewOrder();
        }
    }
    async printReceipt({
        basic = false,
        order = this.getOrder(),
        printBillActionTriggered = false,
    } = {}) {
        await this.printer.print(
            OrderReceipt,
            {
                order,
            },
            { webPrintFallback: true }
        );
        if (!printBillActionTriggered) {
            const nbrPrint = order.nb_print;
            await this.data.write("pos.order", [order.id], { nb_print: nbrPrint + 1 });
        }
        return true;
    }
    getOrderChanges(skipped = false, order = this.getOrder()) {
        return getOrderChanges(order, skipped, this.config.preparationCategories);
    }
    // Now the printer should work in PoS without restaurant
    async sendOrderInPreparation(order, cancelled = false) {
        if (this.config.printerCategories.size) {
            try {
                const orderChange = changesToOrder(
                    order,
                    false,
                    this.config.preparationCategories,
                    cancelled
                );
                this.printChanges(order, orderChange);
            } catch (e) {
                console.info("Failed in printing the changes in the order", e);
            }
        }
    }
    async sendOrderInPreparationUpdateLastChange(o, cancelled = false) {
        this.addPendingOrder([o.id]);
        const uuid = o.uuid;
        const orders = await this.syncAllOrders();
        const order = orders.find((order) => order.uuid === uuid);

        if (order) {
            await this.sendOrderInPreparation(order, cancelled);
            order.updateLastOrderChange();
            this.addPendingOrder([order.id]);
            await this.syncAllOrders();
        }
    }

    async printChanges(order, orderChange) {
        const unsuccedPrints = [];
        const lastChangedLines = order.last_order_preparation_change.lines;
        orderChange.new.sort((a, b) => {
            const sequenceA = a.pos_categ_sequence;
            const sequenceB = b.pos_categ_sequence;
            if (sequenceA === 0 && sequenceB === 0) {
                return a.pos_categ_id - b.pos_categ_id;
            }

            return sequenceA - sequenceB;
        });

        for (const printer of this.unwatched.printers) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids,
                orderChange
            );
            const toPrintArray = this.preparePrintingData(order, changes);
            const diningModeUpdate = orderChange.modeUpdate;
            if (diningModeUpdate || !Object.keys(lastChangedLines).length) {
                // Prepare orderlines based on the dining mode update
                const lines =
                    diningModeUpdate && Object.keys(lastChangedLines).length
                        ? lastChangedLines
                        : order.lines;

                // converting in format we need to show on xml
                const orderlines = Object.entries(lines).map(([key, value]) => ({
                    basic_name: diningModeUpdate ? value.basic_name : value.product_id.name,
                    isCombo: diningModeUpdate ? value.isCombo : value.combo_item_id?.id,
                    quantity: diningModeUpdate ? value.quantity : value.qty,
                    note: value.note,
                    attribute_value_ids: value.attribute_value_ids,
                }));

                // Print detailed receipt
                const printed = await this.printReceipts(
                    order,
                    printer,
                    "New",
                    orderlines,
                    true,
                    diningModeUpdate
                );
                if (!printed) {
                    unsuccedPrints.push("Detailed Receipt");
                }
            } else {
                // Print all receipts related to line changes
                for (const [key, value] of Object.entries(toPrintArray)) {
                    const printed = await this.printReceipts(order, printer, key, value, false);
                    if (!printed) {
                        unsuccedPrints.push(key);
                    }
                }
                // Print Order Note if changed
                if (orderChange.generalNote) {
                    const printed = await this.printReceipts(order, printer, "Message", []);
                    if (!printed) {
                        unsuccedPrints.push("General Message");
                    }
                }
            }
        }

        // printing errors
        if (unsuccedPrints.length) {
            const failedReceipts = unsuccedPrints.join(", ");
            this.dialog.add(AlertDialog, {
                title: _t("Printing failed"),
                body: _t("Failed in printing %s changes of the order", failedReceipts),
            });
        }
    }

    async printReceipts(order, printer, title, lines, fullReceipt = false, diningModeUpdate) {
        const time = order.write_date ? order.write_date?.toFormat("HH:mm") : false;
        const printingChanges = {
            table_name: order.table_id ? order.table_id.table_number : "",
            config_name: order.config_id.name,
            time: order.write_date ? time : "",
            tracking_number: order.tracking_number,
            orderMoode: order.preset_id?.name || "",
            employee_name: order.employee_id?.name || order.user_id?.name,
            order_note: order.internal_note,
            diningModeUpdate: diningModeUpdate,
        };

        const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
            operational_title: title,
            changes: printingChanges,
            changedlines: lines,
            fullReceipt: fullReceipt,
        });
        const result = await printer.printReceipt(receipt);
        return result.successful;
    }

    preparePrintingData(order, changes) {
        const order_modifications = {};
        const pdisChangedLines = order.last_order_preparation_change.lines;

        if (changes["new"].length) {
            order_modifications["New"] = changes["new"];
        }
        if (changes["noteUpdated"].length) {
            order_modifications["Note"] = changes["noteUpdated"];
        }
        // Handle removed lines
        if (changes["cancelled"].length) {
            if (changes["new"].length) {
                order_modifications["Cancelled"] = changes["cancelled"];
            } else {
                const allCancelled = changes["cancelled"].every((line) => {
                    const pdisLine = pdisChangedLines[line.uuid + " - " + line.note];
                    return !pdisLine || pdisLine.quantity <= line.quantity;
                });
                if (
                    allCancelled &&
                    Object.keys(pdisChangedLines).length == changes["cancelled"].length
                ) {
                    order_modifications["Cancel"] = changes["cancelled"];
                } else {
                    order_modifications["Cancelled"] = changes["cancelled"];
                }
            }
        }
        return order_modifications;
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
            noteUpdated: currentOrderChange["noteUpdated"].filter(filterFn),
        };
    }

    closeScreen() {
        this.showOrderScreen(false);
    }

    showOrderScreen(forceEmpty = false) {
        this.addOrderIfEmpty(forceEmpty);
        if (this.mainScreen.component === PaymentScreen) {
            this.getOrder().setScreenData({ name: "PaymentScreen", props: {} });
            this.showScreen("ProductScreen");
            return;
        }
        const { name: screenName } = this.getOrder().getScreenData();
        const props = {};
        if (screenName === "PaymentScreen") {
            props.orderUuid = this.selectedOrderUuid;
        }
        this.showScreen(screenName, props);
    }

    addOrderIfEmpty(forceEmpty) {
        if (!this.getOrder()) {
            return this.addNewOrder();
        }
    }

    connectToProxy() {
        return new Promise((resolve, reject) => {
            this.barcodeReader?.disconnectFromProxy();
            this.loadingSkipButtonIsShown = true;
            this.hardwareProxy.autoConnect({ force_ip: this.config.proxy_ip }).then(
                () => {
                    if (this.config.iface_scan_via_proxy) {
                        this.barcodeReader?.connectToProxy();
                    }
                    resolve();
                },
                (statusText, url) => {
                    // this should reject so that it can be captured when we wait for pos.ready
                    // in the chrome component.
                    // then, if it got really rejected, we can show the error.
                    if (statusText == "error" && window.location.protocol == "https:") {
                        // FIXME POSREF this looks like it's dead code.
                        reject({
                            title: _t("HTTPS connection to IoT Box failed"),
                            body: _t(
                                "Make sure you are using IoT Box v18.12 or higher. Navigate to %s to accept the certificate of your IoT Box.",
                                url
                            ),
                            popup: "alert",
                        });
                    } else {
                        resolve();
                    }
                }
            );
        });
    }
    /**
     * @param {import("@point_of_sale/app/models/res_partner").ResPartner?} partner leave undefined to create a new partner
     */
    async editPartner(partner) {
        const record = await makeActionAwaitable(
            this.action,
            "point_of_sale.res_partner_action_edit_pos",
            {
                props: { resId: partner?.id },
            }
        );
        const newPartner = await this.data.read("res.partner", record.config.resIds);
        return newPartner[0];
    }
    /**
     * @param {import("@point_of_sale/app/models/product_product").ProductProduct?} product leave undefined to create a new product
     */
    async editProduct(product) {
        this.action.doAction(
            product
                ? "point_of_sale.product_template_action_edit_pos"
                : "point_of_sale.product_template_action_add_pos",
            {
                props: {
                    resId: product?.id,
                    onSave: (record) => {
                        this.data.read("product.template", [record.evalContext.id]);
                        this.action.doAction({
                            type: "ir.actions.act_window_close",
                        });
                    },
                },
            }
        );
    }
    async allowProductCreation() {
        return await user.hasGroup("base.group_system");
    }
    async orderDetails(order) {
        this.dialog.add(FormViewDialog, {
            resModel: "pos.order",
            resId: order.id,
            onRecordSaved: async (record) => {
                await this.data.read("pos.order", [record.evalContext.id]);
                await this.data.read(
                    "pos.payment",
                    order.payment_ids.map((p) => p.id)
                );
                this.action.doAction({
                    type: "ir.actions.act_window_close",
                });
            },
        });
    }
    async closePos() {
        this._resetConnectedCashier();
        // If pos is not properly loaded, we just go back to /web without
        // doing anything in the order data.
        if (!this) {
            this.redirectToBackend();
        }

        if (this.session.state === "opening_control") {
            const data = await this.data.call("pos.session", "delete_opening_control_session", [
                this.session.id,
            ]);

            if (data.status === "success") {
                this.redirectToBackend();
            }
        }

        // If there are orders in the db left unsynced, we try to sync.
        const syncSuccess = await this.pushOrdersWithClosingPopup();
        if (syncSuccess) {
            this.redirectToBackend();
        }
    }
    async selectPricelist(pricelist) {
        await this.getOrder().setPricelist(pricelist);
    }
    async selectPreset(preset = false, order = this.getOrder()) {
        if (!preset) {
            const selectionList = this.models["pos.preset"].map((preset) => ({
                id: preset.id,
                label: preset.name,
                isSelected: order.preset_id && preset.id === order.preset_id.id,
                item: preset,
            }));

            preset = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Select preset"),
                list: selectionList,
            });
        }

        if (preset) {
            if (preset.identification === "address" && !order.partner_id) {
                const partner = await this.selectPartner();
                if (!partner) {
                    return;
                }
            }

            order.setPreset(preset);

            if (preset.use_timing && !order.preset_time) {
                await this.syncPresetSlotAvaibility(preset);
                order.preset_time = preset.nextSlot?.datetime || false;
            } else if (!preset.use_timing) {
                order.preset_time = false;
            }
        }
    }
    async syncPresetSlotAvaibility(preset) {
        try {
            const presetAvailabilities = await this.data.call("pos.preset", "get_available_slots", [
                preset.id,
            ]);

            preset.computeAvailabilities(presetAvailabilities);
        } catch {
            // Compute locally if the server is not reachable
            preset.computeAvailabilities();
        }
    }
    async selectPartner() {
        // FIXME, find order to refund when we are in the ticketscreen.
        const currentOrder = this.getOrder();
        if (!currentOrder) {
            return false;
        }
        const currentPartner = currentOrder.getPartner();
        if (currentPartner && currentOrder.getHasRefundLines()) {
            this.dialog.add(AlertDialog, {
                title: _t("Can't change customer"),
                body: _t(
                    "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer.",
                    currentPartner.name
                ),
            });
            return currentPartner;
        }
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: currentPartner,
        });

        if (payload) {
            currentOrder.setPartner(payload);
        } else {
            currentOrder.setPartner(false);
        }

        return payload;
    }
    async editLots(product, packLotLinesToEdit) {
        const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
        let canCreateLots = this.pickingType.use_create_lots || !this.pickingType.use_existing_lots;

        let existingLots = [];
        try {
            existingLots = await this.data.call("pos.order.line", "get_existing_lots", [
                this.company.id,
                this.config.id,
                product.id,
            ]);
            if (!canCreateLots && (!existingLots || existingLots.length === 0)) {
                this.dialog.add(AlertDialog, {
                    title: _t("No existing serial/lot number"),
                    body: _t(
                        "There is no serial/lot number for the selected product, and their creation is not allowed from the Point of Sale app."
                    ),
                });
                return null;
            }
        } catch (ex) {
            console.error("Collecting existing lots failed: ", ex);
            const confirmed = await ask(this.dialog, {
                title: _t("Server communication problem"),
                body: _t(
                    "The existing serial/lot numbers could not be retrieved. \nContinue without checking the validity of serial/lot numbers ?"
                ),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
            });
            if (!confirmed) {
                return null;
            }
            canCreateLots = true;
        }

        const existingLotsName = existingLots.map((l) => l.name);
        const payload = await makeAwaitable(this.dialog, EditListPopup, {
            title: _t("Lot/Serial Number(s) Required"),
            name: product.display_name,
            isSingleItem: isAllowOnlyOneLot,
            array: packLotLinesToEdit,
            options: existingLotsName,
            customInput: canCreateLots,
            uniqueValues: product.tracking === "serial",
        });
        if (payload) {
            // Segregate the old and new packlot lines
            const modifiedPackLotLines = Object.fromEntries(
                payload.filter((item) => item.id).map((item) => [item.id, item.text])
            );
            const newPackLotLines = payload
                .filter((item) => !item.id)
                .map((item) => ({ lot_name: item.text }));

            return { modifiedPackLotLines, newPackLotLines };
        } else {
            return null;
        }
    }

    openOpeningControl() {
        if (this.shouldShowOpeningControl()) {
            this.dialog.add(
                OpeningControlPopup,
                {},
                {
                    onClose: () => {
                        if (
                            this.session.state !== "opened" &&
                            this.mainScreen.component === ProductScreen
                        ) {
                            this.closePos();
                        }
                    },
                }
            );
        }
    }
    shouldShowOpeningControl() {
        return this.session.state == "opening_control";
    }

    /**
     * Close other tabs that contain the same pos session.
     */
    closeOtherTabs() {
        // FIXME POSREF use the bus?
        localStorage["message"] = "";
        localStorage["message"] = JSON.stringify({
            message: "close_tabs",
            session: this.session.id,
        });

        window.addEventListener(
            "storage",
            (event) => {
                if (event.key === "message" && event.newValue) {
                    const msg = JSON.parse(event.newValue);
                    if (msg.message === "close_tabs" && msg.session == this.session.id) {
                        console.info("POS / Session opened in another window. EXITING POS");
                        this.closePos();
                    }
                }
            },
            false
        );
    }

    showBackButton() {
        return (
            this.ui.isSmall &&
            this.numpadMode !== "table" &&
            (this.mainScreen.component !== ProductScreen || this.mobile_pane === "left")
        );
    }
    async onClickBackButton() {
        if (this.mainScreen.component === TicketScreen) {
            if (this.ticket_screen_mobile_pane == "left") {
                this.closeScreen();
            } else {
                this.ticket_screen_mobile_pane = "left";
            }
        } else if (
            this.mobile_pane == "left" ||
            [PaymentScreen, ActionScreen].includes(this.mainScreen.component)
        ) {
            this.mobile_pane = this.mainScreen.component === PaymentScreen ? "left" : "right";
            this.showScreen("ProductScreen");
        }
    }

    showSearchButton() {
        return this.mainScreen.component === ProductScreen && this.mobile_pane === "right";
    }

    doNotAllowRefundAndSales() {
        return false;
    }

    async showQR(payment) {
        let qr;
        try {
            qr = await this.data.call("pos.payment.method", "get_qr_code", [
                [payment.payment_method_id.id],
                payment.amount,
                payment.pos_order_id.name + " " + payment.pos_order_id.tracking_number,
                "",
                this.currency.id,
                payment.pos_order_id.partner_id?.id,
            ]);
        } catch (error) {
            qr = payment.payment_method_id.default_qr;
            if (!qr) {
                let message;
                if (error instanceof ConnectionLostError) {
                    message = _t(
                        "Connection to the server has been lost. Please check your internet connection."
                    );
                } else {
                    message = error.data.message;
                }
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Failure to generate Payment QR Code"),
                    body: message,
                });
                return false;
            }
        }
        return await ask(
            this.env.services.dialog,
            {
                title: payment.name,
                line: payment,
                order: payment.pos_order_id,
                qrCode: qr,
            },
            {},
            QRPopup
        );
    }

    async onTicketButtonClick() {
        if (this.isTicketScreenShown) {
            this.closeScreen();
        } else {
            if (this.config.shouldLoadOrders) {
                try {
                    this.setLoadingOrderState(true);
                    await this.getServerOrders();
                } finally {
                    this.setLoadingOrderState(false);
                    this.showScreen("TicketScreen");
                }
            } else {
                this.showScreen("TicketScreen");
            }
        }
    }

    get isTicketScreenShown() {
        return this.mainScreen.component === TicketScreen;
    }

    redirectToBackend() {
        window.location = "/odoo/action-point_of_sale.action_client_pos_menu";
    }

    getDisplayDeviceIP() {
        return this.config.proxy_ip;
    }

    addMainProductsToDisplay(products) {
        const uniqueProductsMap = new Map();
        for (const product of products) {
            if (product.id in this.mainProductVariant) {
                const mainProduct = this.mainProductVariant[product.id];
                uniqueProductsMap.set(mainProduct.id, mainProduct);
            } else {
                uniqueProductsMap.set(product.id, product);
            }
        }
        return Array.from(uniqueProductsMap.values());
    }

    get productsToDisplay() {
        const searchWord = this.searchProductWord.trim();
        const allProducts = this.models["product.template"].getAll();
        let list = [];

        if (searchWord !== "") {
            list = this.addMainProductsToDisplay(
                this.getProductsBySearchWord(searchWord, allProducts)
            );
        } else if (this.selectedCategory?.id) {
            list = this.selectedCategory.associatedProducts;
        } else {
            list = allProducts;
        }

        if (!list || list.length === 0) {
            return [];
        }

        const excludedProductIds = [
            this.config.tip_product_id?.id,
            ...this.hiddenProductIds,
            ...this.session._pos_special_products_ids,
        ];

        list = list
            .filter(
                (product) => !excludedProductIds.includes(product.id) && product.available_in_pos
            )
            .slice(0, 100);

        return searchWord !== ""
            ? list.sort((a, b) => b.is_favorite - a.is_favorite)
            : list.sort((a, b) => {
                  if (b.is_favorite !== a.is_favorite) {
                      return b.is_favorite - a.is_favorite;
                  }
                  return a.display_name.localeCompare(b.display_name);
              });
    }

    getProductsBySearchWord(searchWord, products) {
        const exactMatches = products.filter((product) => product.exactMatch(searchWord));

        if (exactMatches.length > 0 && searchWord.length > 2) {
            return exactMatches;
        }

        const fuzzyMatches = fuzzyLookup(unaccent(searchWord, false), products, (product) =>
            unaccent(product.searchString, false)
        );

        return Array.from(new Set([...exactMatches, ...fuzzyMatches]));
    }
}

PosStore.prototype.electronic_payment_interfaces = {};

/**
 * Call this function to map your PaymentInterface implementation to
 * the use_payment_terminal field. When the POS loads it will take
 * care of instantiating your interface and setting it on the right
 * payment methods.
 *
 * @param {string} use_payment_terminal - value used in the
 * use_payment_terminal selection field
 *
 * @param {Object} ImplementedPaymentInterface - implemented
 * PaymentInterface
 */
export function register_payment_method(use_payment_terminal, ImplementedPaymentInterface) {
    PosStore.prototype.electronic_payment_interfaces[use_payment_terminal] =
        ImplementedPaymentInterface;
}

export const posService = {
    dependencies: PosStore.serviceDependencies,
    async start(env, deps) {
        return new PosStore({ traps: {}, env, deps }).ready;
    },
};

registry.category("services").add("pos", posService);
