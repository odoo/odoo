/* global waitForWebfonts */

import { Mutex } from "@web/core/utils/concurrency";
import { markRaw, reactive } from "@odoo/owl";
import { renderToElement } from "@web/core/utils/render";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    deduceUrl,
    random5Chars,
    uuidv4,
    Counter,
    orderUsageUTCtoLocalUtil,
} from "@point_of_sale/utils";
import { HWPrinter } from "@point_of_sale/app/utils/printer/hw_printer";
import { ConnectionLostError } from "@web/core/network/rpc";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";
import { SelectLotPopup } from "@point_of_sale/app/components/popups/select_lot_popup/select_lot_popup";
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
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { SelectionPopup } from "../components/popups/selection_popup/selection_popup";
import { user } from "@web/core/user";
import { normalize } from "@web/core/l10n/utils";
import { WithLazyGetterTrap } from "@point_of_sale/lazy_getter";
import { debounce } from "@web/core/utils/timing";
import DevicesSynchronisation from "../utils/devices_synchronisation";
import { formatDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { RetryPrintPopup } from "@point_of_sale/app/components/popups/retry_print_popup/retry_print_popup";
import { PresetSlotsPopup } from "@point_of_sale/app/components/popups/preset_slots_popup/preset_slots_popup";
import { DebugWidget } from "../utils/debug/debug_widget";
import { EpsonPrinter } from "@point_of_sale/app/utils/printer/epson_printer";
import OrderPaymentValidation from "../utils/order_payment_validation";
import { logPosMessage } from "../utils/pretty_console_log";
import { initLNA } from "../utils/init_lna";

const { DateTime } = luxon;
export const CONSOLE_COLOR = "#F5B427";

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
        "pos_scale",
        "dialog",
        "notification",
        "printer",
        "action",
        "alert",
        "pos_router",
        "mail.sound_effects",
        "iot_longpolling",
    ];
    constructor({ traps, env, deps }) {
        super({ traps });
        const reactiveSelf = reactive(this);
        reactiveSelf.ready = reactiveSelf.setup(env, deps).then(() => reactiveSelf);
        return reactiveSelf;
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
            pos_scale,
            action,
            pos_router,
            alert,
            iot_longpolling,
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
        this.router = pos_router;
        this.sound = env.services["mail.sound_effects"];
        this.notification = notification;
        this.unwatched = markRaw({});
        this.pushOrderMutex = new Mutex();
        this.router.popStateCallback = this.handleUrlParams.bind(this);

        // Object mapping the order's name (which contains the uuid) to it's server_id after
        // validation (order paid then sent to the backend).
        this.validated_orders_name_server_id_map = {};
        this.numpadMode = "quantity";
        this.mobile_pane = "right";
        this.ticket_screen_mobile_pane = "left";

        this.loadingOrderState = false; // used to prevent orders fetched to be put in the update set during the reactive change
        this.screenState = {
            ticketSCreen: {
                offsetByDomain: {},
                totalCount: 0,
            },
            partnerList: {
                offsetBySearch: {},
            },
        };
        // Handle offline mode
        // All of Set of ids
        this.pendingOrder = {
            write: new Set(),
            delete: new Set(),
            create: new Set(),
        };

        this.hardwareProxy = hardware_proxy;
        this.iotLongpolling = iot_longpolling;
        this.selectedOrderUuid = null;
        this.selectedPartner = null;
        this.selectedCategory = null;
        this.searchProductWord = "";
        this.ready = new Promise((resolve) => {
            this.markReady = resolve;
        });
        this.scale = pos_scale;

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
        this.syncAllOrdersDebounced = debounce(this.syncAllOrders, 100);
        this._searchTriggered = false;

        if (this.env.debug) {
            registry.category("main_components").add("DebugWidget", {
                Component: DebugWidget,
            });
        }

        window.addEventListener("pos-network-online", () => {
            // Sync should be done before websocket connection when going online
            this.syncAllOrdersDebounced();
        });

        this.lnaState = {
            type: "pending",
            message: _t("Checking Local Network Access permission..."),
        };
        initLNA(this.notification, (type, message) => {
            this.lnaState = { type, message };
        });
    }

    navigate(routeName, routeParams = {}) {
        const pageParams = registry.category("pos_pages").get(routeName);
        const component = pageParams.component;

        if (component.storeOnOrder ?? true) {
            this.getOrder()?.setScreenData({ name: routeName, props: routeParams });
        }

        this.router.navigate(routeName, routeParams);
        return true;
    }

    navigateToFirstPage() {
        const page = this.firstPage;
        this.navigate(page.page, page.params);
    }

    navigateToOrderScreen(order) {
        const orderPage = order.getScreenData();
        const page = orderPage?.name || "ProductScreen";
        const params = orderPage?.props || {
            orderUuid: order.uuid,
        };
        this.ticket_screen_mobile_pane = "left";
        this.navigate(page, params);
    }

    get defaultPage() {
        return {
            page: "ProductScreen",
            params: {
                orderUuid: this.openOrder.uuid,
            },
        };
    }

    get firstPage() {
        if (odoo.from_backend) {
            // Remove from_backend params in the URL but keep the rest
            const url = new URL(window.location.href);
            url.searchParams.delete("from_backend");
            window.history.replaceState({}, "", url);

            if (!this.config.module_pos_hr) {
                this.setCashier(this.user);
            }
        } else {
            this.resetCashier();
        }

        return !this.cashier ? { page: "LoginScreen", params: {} } : this.defaultPage;
    }

    get idleTimeout() {
        return [
            {
                timeout: 300000, // 5 minutes
                action: () =>
                    this.router.state.current !== "PaymentScreen" && this.navigate("SaverScreen"),
            },
            {
                timeout: 120000, // 2 minutes
                action: () =>
                    this.router.state.current === "LoginScreen" && this.navigate("SaverScreen"),
            },
        ];
    }

    async reloadData(fullReload = false) {
        const orders = this.models["pos.order"].getAll();
        this.device.saveUnusedNumber(orders);
        await this.data.resetIndexedDB();
        const url = new URL(window.location.href);

        if (fullReload) {
            url.searchParams.set("limited_loading", "0");
        }

        window.location.href = url.href;
    }

    async showLoginScreen() {
        this.resetCashier();
        this.navigate("LoginScreen");
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
        await this.handleUrlParams();
        this.data.connectWebSocket("CLOSING_SESSION", this.closingSessionNotification.bind(this));
        const process = await this.afterProcessServerData();

        if (this.router.state.current !== "LoginScreen" && !this.config.module_pos_hr) {
            this.setCashier(this.user);
        }

        const page =
            this.router.state.current === "LoginScreen"
                ? this.firstPage
                : {
                      page: this.router.state.current,
                      params: this.router.state.params,
                  };
        this.navigate(page.page, page.params);
        return process;
    }

    async closingSessionNotification(data) {
        if (
            data.device_identifier === this.device.identifier ||
            this.session.id !== parseInt(data.session_id)
        ) {
            return;
        }

        try {
            const paidOrderNotSynced = this.models["pos.order"].filter(
                (order) => order.state === "paid" && !order.isSynced
            );
            this.addPendingOrder(paidOrderNotSynced.map((o) => o.id));
            await this.syncAllOrders({ throw: true });

            this.dialog.add(AlertDialog, {
                title: _t("Closing Session"),
                body: _t("The session is being closed by another user. The page will be reloaded."),
            });
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t(
                    "An error occurred while closing the session. Unsynced orders will be available in the next session. The page will be reloaded."
                ),
            });
        } finally {
            // All orders saved on the server should be cancelled by the device that closes
            // the session. If some orders are not cancelled, we need to cancel them here.
            const orders = this.models["pos.order"].filter((o) => o.isSynced);
            for (const order of orders) {
                if (!order.finalized) {
                    order.state = "cancel";
                }
            }
            this.session.state = "closed";
        }

        setTimeout(() => {
            window.location.reload();
        }, 3000);
    }

    get session() {
        return this.data.models["pos.session"].get(odoo.pos_session_id);
    }

    get company() {
        return this.config.company_id;
    }

    async processServerData() {
        // Used to identify the device when several devices are connected to the same POS
        this.device = this.data.device;

        // These fields should be unique for the pos_config
        // and should not change during the session, so we can
        // safely take the first element.this.models
        this.config = this.data.models["pos.config"].getFirst();
        this.user = this.data.models["res.users"].getFirst();
        this.currency = this.config.currency_id;
        this.pickingType = this.data.models["stock.picking.type"].getFirst();
        this.models = this.data.models;
        this.screenState.partnerList.offsetBySearch = {
            "": this.models["res.partner"].length,
        };

        const models = Object.keys(this.models);
        const dynamicModels = this.data.opts.dynamicModels;
        const staticModels = models.filter((model) => !dynamicModels.includes(model));
        const deviceSync = new DevicesSynchronisation(dynamicModels, staticModels, this);

        this.deviceSync = deviceSync;
        this.data.deviceSync = deviceSync;

        await this.deviceSync.readDataFromServer();

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
            const printer = relPrinter.raw;
            const HWPrinter = this.createPrinter(printer);

            HWPrinter.config = printer;
            this.unwatched.printers.push(HWPrinter);
        }
        this.config.iface_printers = !!this.unwatched.printers.length;

        this.models["product.pricelist.item"].addEventListener("create", () => {
            const order = this.getOrder();
            if (!order) {
                return;
            }
            const currentPricelistId = order.pricelist_id?.id;
            order.setPricelist(this.models["product.pricelist"].get(currentPricelistId));
        });

        await this.processProductAttributes();
        await this.config.cacheReceiptLogo();
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
                logPosMessage(
                    "Store",
                    "processProductAttributes",
                    "Error while fetching product variants",
                    CONSOLE_COLOR,
                    [error]
                );
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
            }
        }

        this.productAttributesExclusion = this.computeProductAttributesExclusion();
    }

    computeProductAttributesExclusion(excl = false) {
        const exclusions = this.productAttributesExclusion || new Map();

        const addExclusion = (key, value) => {
            if (!exclusions.has(key)) {
                exclusions.set(key, new Set());
            }
            exclusions.get(key).add(value);
        };

        for (const exclusion of excl ||
            this.models["product.template.attribute.exclusion"].getAll()) {
            const ptavId = exclusion.product_template_attribute_value_id.id;
            for (const { id: valueId } of exclusion.value_ids) {
                addExclusion(ptavId, valueId);
                addExclusion(valueId, ptavId);
            }
        }
        return exclusions;
    }

    doHaveConflictWith(value, selectedValues) {
        const exclusions = this.productAttributesExclusion.get(value.id);
        if (!exclusions) {
            return false;
        }
        const selectedValueIds = new Set(selectedValues.map((v) => v.id));
        for (const exclusionId of exclusions) {
            if (selectedValueIds.has(exclusionId)) {
                return true;
            }
        }
        return false;
    }

    async onDeleteOrder(order) {
        if (order.getOrderlines().length > 0) {
            const confirmed = await ask(this.dialog, {
                title: _t("Existing orderlines"),
                body: _t(
                    "%s has a total amount of %s, are you sure you want to delete this order?",
                    order.pos_reference,
                    this.env.utils.formatCurrency(order.priceIncl)
                ),
            });
            if (!confirmed) {
                return false;
            }
        }
        const refundedOrderLines = order.lines
            .filter((line) => line.refunded_orderline_id?.order_id)
            .map((line) => ({
                order: line.refunded_orderline_id.order_id,
                uuid: line.refunded_orderline_id.uuid,
            }));

        const orderIsDeleted = await this.deleteOrders([order]);
        if (!orderIsDeleted) {
            return false;
        }
        order.uiState.displayed = false;
        // Delete refunded lines linked to the current order
        for (const refundedLine of refundedOrderLines) {
            delete refundedLine.order?.uiState?.lineToRefund[refundedLine.uuid];
        }

        await this.afterOrderDeletion();
        return true;
    }
    async afterOrderDeletion() {
        if (!this.config.module_pos_restaurant) {
            this.setOrder(this.getOpenOrders().at(-1) || this.addNewOrder());
        }
    }

    async deleteOrders(orders, serverIds = [], ignoreChange = false) {
        const ordersToDelete = [];
        const actionPosOrderCancelCall = async (orderIds) => {
            await this.data.call("pos.order", "action_pos_order_cancel", [orderIds], {
                context: {
                    device_identifier: this.device.identifier,
                },
            });
        };
        try {
            for (const order of orders) {
                if (order && (await this._onBeforeDeleteOrder(order))) {
                    if (
                        !ignoreChange &&
                        order.isSynced &&
                        Object.keys(order.last_order_preparation_change).length > 0
                    ) {
                        const orderPresetDate = DateTime.fromISO(order.preset_time);
                        const isSame = DateTime.now().hasSame(orderPresetDate, "day");
                        if (!order.preset_time || isSame) {
                            await this.sendOrderInPreparation(order, {
                                cancelled: true,
                                orderDone: true,
                            });
                        }
                    }

                    if (order.isSynced) {
                        await actionPosOrderCancelCall([order.id]);
                    }
                    ordersToDelete.push(order);
                } else {
                    return false;
                }
            }

            if (serverIds.length > 0) {
                await actionPosOrderCancelCall([
                    ...new Set(serverIds.filter((id) => typeof id === "number")),
                ]);
            }
        } finally {
            // Remove orders locally at the end to avoid reactivity during the async process
            for (const order of ordersToDelete) {
                this.removeOrder(order, false);
                this.removePendingOrder(order);
            }
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

    /**
     * This method is used to load new products from the server.
     * It also load pricelists, attributes and packagings
     * @param {Array} domain
     * @param {number} offset
     * @param {number} limit
     * @returns {Promise<Object>}
     */
    async loadNewProducts(domain, offset = 0, limit = 0) {
        const result = await this.data.callRelated(
            "product.template",
            "load_product_from_pos",
            [odoo.pos_config_id, domain, offset, limit],
            {},
            false
        );
        this.productAttributesExclusion = this.computeProductAttributesExclusion(
            result["product.template.attribute.exclusion"]
        );
        return result;
    }

    async handleUrlParams() {
        const orderPathUuid = this.router.state.params.orderUuid;
        const order = this.models["pos.order"].find((order) => order.uuid === orderPathUuid);
        if (orderPathUuid && !order) {
            await this.data.loadServerOrders([["uuid", "=", orderPathUuid]]);
            const order = this.models["pos.order"].find((order) => order.uuid === orderPathUuid);
            if (order) {
                this.setOrder(order);
            } else {
                const next = this.defaultPage;
                this.router.navigate(next.page, next.params);
            }
        } else {
            this.setOrder(order);
        }
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
        await this.syncAllOrders();

        if (!this.config.module_pos_restaurant) {
            if (this.router.state.params.orderUuid) {
                this.selectedOrderUuid = this.router.state.params.orderUuid;
            } else {
                this.selectedOrderUuid = openOrders.length
                    ? openOrders[openOrders.length - 1].uuid
                    : null;
            }
        }

        this.markReady();
        await this.deviceSync.readDataFromServer();

        if (this.config.other_devices && this.config.epson_printer_ip) {
            this.hardwareProxy.printer = new EpsonPrinter({ ip: this.config.epson_printer_ip });
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
    async onProductInfoClick(productTemplate, productProduct = false) {
        const info = await this.getProductInfo(productTemplate, 1, 0, productProduct);
        this.dialog.add(ProductInfoPopup, { info: info, productTemplate: productTemplate });
    }
    async openConfigurator(pTemplate, opts = {}) {
        const attrById = this.models["product.attribute"].getAllBy("id");
        const attributeLines = pTemplate.attribute_line_ids.filter(
            (attr) => attr.attribute_id?.id in attrById
        );
        let attributeLinesValues = attributeLines.map((attr) => attr.product_template_value_ids);
        if (opts.code || opts.presetVariant) {
            let product;
            if (opts.code) {
                product = this.models["product.product"].getBy("barcode", opts.code.base_code);
            } else {
                product = opts.presetVariant;
            }

            const attrValueIds = new Set(
                product?.product_template_attribute_value_ids?.map((v) => v.id) || []
            );

            attributeLinesValues = attributeLinesValues.map((values) =>
                values[0].attribute_id.create_variant === "no_variant"
                    ? values
                    : values.filter((value) => attrValueIds.has(value.id))
            );
        }
        if (attributeLinesValues.some((values) => values.length > 1 || values[0].is_custom)) {
            return await makeAwaitable(this.dialog, ProductConfiguratorPopup, {
                productTemplate: pTemplate,
                hideAlwaysVariants: opts.hideAlwaysVariants,
                forceVariantValue: opts.forceVariantValue,
                line: opts.line,
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

    async setDiscountFromUI(line, val) {
        for (const comboLine of line.combo_line_ids) {
            comboLine.setDiscount(val);
        }
        line.setDiscount(val);
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
        let order = this.getOrder();
        if (!order) {
            order = this.addNewOrder();
        }
        order.assertEditable();
        return await this.addLineToOrder(vals, order, opts, configure);
    }

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        let merge = true;
        order.assertEditable();

        const options = {
            ...opts,
        };

        if ("price_unit" in vals) {
            merge = false;
        }

        if (typeof vals.product_tmpl_id == "number") {
            vals.product_tmpl_id = this.data.models["product.template"].get(vals.product_tmpl_id);
        }

        const productTemplate = vals.product_tmpl_id;
        const values = {
            price_type: "price_unit" in vals ? "manual" : "original",
            price_extra: 0,
            price_unit: 0,
            order_id: order,
            qty: order.preset_id?.is_return ? -1 : 1,
            tax_ids: productTemplate.taxes_id.map((tax) => ["link", tax]),
            product_id: productTemplate.product_variant_ids[0],
            ...vals,
        };

        // Handle refund constraints
        if (order.isSaleDisallowed(values, options) && !opts.force) {
            this.dialog.add(AlertDialog, {
                title: _t("Oops.."),
                body: _t("Ensure you validate the refund before taking another order."),
            });
            return;
        }

        let keepGoing = await this.handleConfigurableProduct(
            values,
            productTemplate,
            opts,
            configure
        );
        if (keepGoing === false) {
            return;
        }

        keepGoing = await this.handleComboProduct(values, order, configure);
        if (keepGoing === false) {
            return;
        }

        // In the case of a product with tracking enabled, we need to ask the user for the lot/serial number.
        // It will return an instance of pos.pack.operation.lot
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        const code = opts.code;
        let pack_lot_ids = {};
        if (values.product_tmpl_id.isTracked() && (configure || code)) {
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
                const decimalAccuracy = this.models["decimal.precision"].find(
                    (dp) => dp.name === "Product Unit"
                ).digits;

                const overridedValues = {};
                if (order.pricelist_id) {
                    overridedValues.pricelist = order.pricelist_id;
                }
                if (order.fiscal_position_id) {
                    overridedValues.fiscalPosition = order.fiscal_position_id;
                }

                this.scale.setProduct(
                    values.product_id,
                    decimalAccuracy,
                    values.product_id.getTaxDetails({ overridedValues }).total_included
                );
                const weight = await this.weighProduct();
                if (weight) {
                    values.qty = weight;
                } else if (weight !== null) {
                    return;
                }
            } else {
                await values.product_tmpl_id._onScaleNotAvailable();
            }
        }

        // Handle price unit
        this.handlePriceUnit(values, order, vals.price_unit);

        const line = this.data.models["pos.order.line"].create({ ...values, order_id: order });
        line.setOptions(options);
        this.selectOrderLine(order, line);
        if (configure) {
            this.numberBuffer.reset();
        }
        let selectedOrderline = order.getSelectedOrderline();
        if (options.draftPackLotLines && configure) {
            selectedOrderline.setPackLotLines({
                ...options.draftPackLotLines,
                setQuantity: options.quantity === undefined,
            });
        }

        // Merge orderline if needed
        this.tryMergeOrderline(order, line, merge, selectedOrderline);

        selectedOrderline = order.getSelectedOrderline();
        if (values.product_id.tracking === "lot") {
            const productTemplate = values.product_id.product_tmpl_id;
            const related_lines = [];
            const price = productTemplate.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra,
                false,
                values.product_id,
                selectedOrderline,
                related_lines
            );
            related_lines.forEach((line) => line.setUnitPrice(price));
        }

        if (configure) {
            this.numberBuffer.reset();
        }

        if (values.product_id.tracking === "serial") {
            this.selectedOrder.getSelectedOrderline().setPackLotLines({
                modifiedPackLotLines: pack_lot_ids.modifiedPackLotLines ?? [],
                newPackLotLines: pack_lot_ids.newPackLotLines ?? [],
                setQuantity: true,
            });
        }

        if (configure) {
            this.numberBuffer.reset();
        }

        return order.getSelectedOrderline();
    }

    /**
     * Try to merge the orderline with another one in the order.
     * If no orderline can be merged, select the last orderline.
     * If merge is false, do not merge the orderline.
     */
    tryMergeOrderline(order, line, merge, selectedOrderline) {
        selectedOrderline = selectedOrderline || order.getSelectedOrderline();
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
    }

    /**
     * Handle price unit for the order line.
     */
    handlePriceUnit(values, order, price_unit) {
        if (!values.product_tmpl_id.isCombo() && price_unit === undefined) {
            values.price_unit = values.product_id.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra,
                false,
                values.product_id
            );
        }
    }

    // In case of clicking a combo product a popup will be shown to the user
    // It will return the combo prices and the selected products
    // ---
    // This actions cannot be handled inside pos_order.js or pos_order_line.js
    async handleComboProduct(values, order, configure = true, { line } = {}) {
        if (values.product_tmpl_id.isCombo() && configure) {
            const payload =
                values?.payload && Object.keys(values?.payload).length
                    ? values.payload
                    : await makeAwaitable(this.dialog, ComboConfiguratorPopup, {
                          productTemplate: values.product_tmpl_id,
                          line: line,
                      });

            if (!payload) {
                return false;
            }

            // Product template of combo should not have more than 1 variant.
            const [childLineConf, comboExtraLines] = payload;
            const comboPrices = computeComboItems(
                values.product_tmpl_id.product_variant_ids[0],
                childLineConf,
                order.pricelist_id,
                this.data.models["decimal.precision"].getAll(),
                this.data.models["product.template.attribute.value"].getAllBy("id"),
                comboExtraLines,
                this.currency
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
                    price_type: "original",
                    order_id: order,
                    qty: comboItem.qty * values.qty,
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

        return true;
    }

    // In case of configurable product a popup will be shown to the user
    // We assign the payload to the current values object.
    // ---
    // This actions cannot be handled inside pos_order.js or pos_order_line.js
    handleConfigurableProduct = async (values, productTemplate, opts = {}, configure = true) => {
        if (productTemplate.isConfigurable() && configure) {
            const payload =
                values?.payload && Object.keys(values?.payload).length
                    ? values.payload
                    : await this.openConfigurator(productTemplate, opts);

            if (payload) {
                // Find candidate based on instantly created variants.
                const attributeValues = this.models["product.template.attribute.value"]
                    .readMany(payload.attribute_value_ids)
                    .filter((value) => value.attribute_id.create_variant !== "no_variant")
                    .map((value) => value.id);

                let candidate = productTemplate.product_variant_ids.find((variant) => {
                    const attributeIds = variant.product_template_attribute_value_ids.map(
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
                return false;
            }
        } else if (values.product_id.product_template_variant_value_ids.length > 0) {
            // Verify price extra of variant products
            const priceExtra = values.product_id.product_template_variant_value_ids
                .filter((attr) => attr.attribute_id.create_variant !== "always")
                .reduce((acc, attr) => acc + attr.price_extra, 0);

            values.price_extra += priceExtra;
            if (!values.attribute_value_ids) {
                values.attribute_value_ids = [];
            }
            values.attribute_value_ids = values.attribute_value_ids.concat(
                values.product_id.product_template_variant_value_ids.map((attr) => ["link", attr])
            );
        }
    };

    createPrinter(config) {
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter({ ip: config.epson_printer_ip });
        }
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

    /**
     * Remove the order passed in params from the list of orders
     * @param order
     */
    removeOrder(order, removeFromServer = true) {
        if (this.config.isShareable || removeFromServer) {
            if (order.isSynced && !order.finalized) {
                this.addPendingOrder([order.id], true);
                this.syncAllOrdersDebounced();
            }
        }

        if (!order.isSynced && order.finalized) {
            this.addPendingOrder([order.id]);
            return;
        }

        this.device.saveUnusedNumber([order]);
        return this.data.localDeleteCascade(order);
    }

    /**
     * Return the current cashier (in this case, the user)
     * @returns {name: string, id: int, role: string}
     */
    getCashier() {
        return this.user;
    }
    getCashierUserId() {
        return this.user?.id;
    }
    cashierHasPriceControlRights() {
        return !this.config.restrict_price_control || this.getCashier()._role == "manager";
    }
    get showCashMoveButton() {
        return Boolean(this.config.cash_control && this.config._has_cash_move_perm);
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

        this.setNextOrderRefs(order);
        order.setPricelist(this.config.pricelist_id);

        if (this.config.use_presets && !data["preset_id"]) {
            this.selectPreset(this.config.default_preset_id, order);
        }

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
    setNextOrderRefs(order) {
        const deviceIdentifier = this.device.identifier;
        const number = `${this.device.useNext()}`.padStart(6, "0");
        const configId = this.config.id;
        const year2Digits = DateTime.now().year.toString().slice(-2);
        const posReference = `${year2Digits}${deviceIdentifier}-${configId}-${number}`;

        order.pos_reference = posReference;
        order.tracking_number = deviceIdentifier + `${parseInt(number) % 1000}`.padStart(3, "0");
    }

    selectNextOrder() {
        const orders = this.models["pos.order"].filter((order) => !order.finalized);
        if (orders.length > 0) {
            this.selectedOrderUuid = orders[0].uuid;
        } else {
            return this.addNewOrder();
        }
    }
    get openOrder() {
        return this.models["pos.order"].find((o) => o.state === "draft") || this.addNewOrder();
    }
    getEmptyOrder() {
        const emptyOrders = this.models["pos.order"].filter(
            (order) =>
                order.isEmpty() &&
                !order.finalized &&
                order.payment_ids.length === 0 &&
                !order.partner_id &&
                order.pricelist_id?.id === this.config.pricelist_id?.id &&
                order.fiscal_position_id?.id === this.config.default_fiscal_position_id?.id
        );
        if (emptyOrders.length > 0) {
            return emptyOrders[0];
        }
        return this.addNewOrder();
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
        const orderToCreate = this.models["pos.order"]
            .filter(
                (order) =>
                    this.pendingOrder.create.has(order.id) && this.shouldCreatePendingOrder(order)
            )
            .filter(Boolean);
        const orderToUpdate = this.models["pos.order"]
            .readMany(Array.from(this.pendingOrder.write))
            .filter(Boolean);
        const orderToDelete = this.models["pos.order"]
            .readMany(Array.from(this.pendingOrder.delete))
            .filter(Boolean);

        return {
            orderToDelete,
            orderToCreate,
            orderToUpdate,
        };
    }

    shouldCreatePendingOrder(order) {
        return (
            order.lines.length > 0 ||
            order.payment_ids.some((p) => p.payment_method_id.type === "pay_later")
        );
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
            device_identifier: this.device.identifier,
            ...(options.context || {}),
        };
    }

    async preSyncAllOrders(orders) {
        // Prices are computed on the fly on the pos.order and pos.order.line model
        // we need to set them before sending the orders to the backend
        for (const order of orders) {
            order.setOrderPrices();
        }
    }

    postSyncAllOrders(orders) {}
    async syncAllOrders(options = {}) {
        if (this.data.network.offline) {
            if (options.throw) {
                throw new ConnectionLostError();
            }

            return new ConnectionLostError();
        }

        const { orderToCreate, orderToUpdate } = this.getPendingOrder();
        const orderIdsToDelete = this.getOrderIdsToDelete();

        let orders = options.orders || [...orderToCreate, ...orderToUpdate];
        orders = orders.filter(
            (order) => !this.syncingOrders.has(order.uuid) && (order.isDirty() || options.force)
        );

        // Delete orders first
        if (orderIdsToDelete.length > 0) {
            await this.deleteOrders([], orderIdsToDelete);
        }

        // Allow us to force the sync of the orders In the case of
        // pos_restaurant is usefull to get unsynced orders
        // for a specific table
        if (orders.length === 0) {
            return;
        }

        // We are now syncing orders one by one to avoid cancelling all sync
        // when one order fails, this also avoid timeout issues with a lot of orders
        let errorOccurred = false;
        let newSession = false;
        const syncedOrders = [];

        for (const order of orders) {
            const context = this.getSyncAllOrdersContext([order], options);
            await this.preSyncAllOrders([order]);
            this.syncingOrders.add(order.id);

            try {
                const serialized = order.serializeForORM();
                const data = await this.data.call("pos.order", "sync_from_ui", [[serialized]], {
                    context,
                });
                const missingRecords = await this.data.missingRecursive(data);
                const newData = this.models.loadConnectedData(missingRecords);

                logPosMessage(
                    "Store",
                    "syncAllOrders",
                    `Successfully synced orders (${orders.length})`,
                    CONSOLE_COLOR,
                    [newData]
                );

                for (const line of newData["pos.order.line"]) {
                    const refundedOrderLine = line.refunded_orderline_id;

                    if (refundedOrderLine && ["paid", "done"].includes(line.order_id.state)) {
                        const order = refundedOrderLine.order_id;
                        if (order) {
                            delete order.uiState?.lineToRefund[refundedOrderLine.uuid];
                        }
                    }
                }

                await this.postSyncAllOrders(newData["pos.order"]);
                this.removePendingOrder(order);
                syncedOrders.push(...newData["pos.order"]);
                newSession = newSession || data["pos.session"].length > 0;
            } catch (error) {
                if (options.throw) {
                    throw error;
                }

                if (error instanceof ConnectionLostError) {
                    logPosMessage(
                        "Store",
                        "syncAllOrders",
                        "Offline mode active, order will be synced later",
                        CONSOLE_COLOR
                    );
                } else {
                    errorOccurred = true;
                }
            } finally {
                orders.forEach((order) => this.syncingOrders.delete(order.uuid));
            }
        }

        if (errorOccurred) {
            // In that case we assume the order data isn't valid anymore, so we
            // try to read data from server, to be sure to have the latest state
            // the order can be deleted from the server side during the sync_from_ui call
            this.deviceSync.readDataFromServer();
        }

        if (newSession) {
            // Replace the original session by the rescue one. And the rescue one will have
            // a higher id than the original one since it's the last one created.
            const sessions = this.models["pos.session"].sort((a, b) => a.id - b.id);
            if (sessions.length > 1) {
                const sessionToDelete = sessions.slice(0, -1);
                this.models["pos.session"].deleteMany(sessionToDelete);
            }
            this.models["pos.order"]
                .getAll()
                .filter((order) => order.state === "draft")
                .forEach((order) => (order.session_id = this.session));
        }

        return syncedOrders;
    }

    pushSingleOrder(order) {
        return this.pushOrderMutex.exec(() => this.syncAllOrders(order));
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
                this.navigate("PaymentScreen", {
                    orderUuid: this.selectedOrderUuid,
                });
            }
        } else {
            this.mobile_pane = "right";
            this.navigate("PaymentScreen", {
                orderUuid: this.selectedOrderUuid,
            });
        }
    }
    async getServerOrders() {
        await this.syncAllOrders();
        return await this.data.loadServerOrders([
            ["config_id", "in", [...this.config.raw.trusted_config_ids, this.config.id]],
            ["state", "=", "draft"],
        ]);
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

        const productTaxDetails = productTemplate.getTaxDetails();
        const priceWithoutTax = productTaxDetails.total_excluded;
        const margin = priceWithoutTax - productTemplate.standard_price;
        const orderPriceWithoutTax = order.priceExcl;
        const orderCost = order.getTotalCost();
        const orderMargin = orderPriceWithoutTax - orderCost;
        const orderTaxTotalCurrency = this.env.utils.formatCurrency(
            order.prices.taxDetails.order_sign * order.prices.taxDetails.tax_amount_currency
        );
        const orderPriceWithTaxCurrency = this.env.utils.formatCurrency(
            order.prices.taxDetails.order_sign * order.prices.taxDetails.total_amount_currency
        );
        const taxAmount = this.env.utils.formatCurrency(
            productTaxDetails.taxes_data.reduce((sum, d) => sum + d.tax_amount_currency, 0)
        );
        const taxName = productTemplate.taxes_id.map((t) => t.name)?.join(", ");

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
            taxAmount,
            taxName,
            orderPriceWithoutTaxCurrency,
            orderCostCurrency,
            orderMarginCurrency,
            orderMarginPercent,
            orderTaxTotalCurrency,
            orderPriceWithTaxCurrency,
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
    setOrder(order) {
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
            logPosMessage(
                "Store",
                "pushOrdersWithClosingPopup",
                "Some orders could not be submitted to the server",
                CONSOLE_COLOR,
                [error]
            );
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
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "retry"
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
        const ProductUnit = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit"
        );
        return ProductUnit.isZero(qty);
    }

    disallowLineQuantityChange() {
        return false;
    }

    restrictLineDiscountChange() {
        return false;
    }

    restrictLinePriceChange() {
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
    async printReceipt({
        basic = false,
        order = this.getOrder(),
        printBillActionTriggered = false,
    } = {}) {
        const result = await this.printer.print(
            OrderReceipt,
            {
                order,
                basic_receipt: basic,
            },
            this.printOptions
        );
        if (!printBillActionTriggered) {
            if (result) {
                const count = order.nb_print ? order.nb_print + 1 : 1;
                if (order.isSynced) {
                    const wasDirty = order.isDirty();
                    await this.data.write("pos.order", [order.id], { nb_print: count });
                    if (!wasDirty) {
                        order._dirty = false;
                    }
                } else {
                    order.nb_print = count;
                }
            }
        } else if (!order.nb_print) {
            order.nb_print = 0;
        }
        if (result?.warningCode) {
            this.displayPrinterWarning(result, _t("Receipt Printer"));
        }
        return result;
    }
    get printOptions() {
        return { webPrintFallback: true };
    }
    getOrderChanges(order = this.getOrder()) {
        return getOrderChanges(order, this.config.preparationCategories);
    }
    changesToOrder(order, skipped = false, orderPreparationCategories, cancelled = false) {
        return changesToOrder(order, skipped, orderPreparationCategories, cancelled);
    }
    async checkPreparationStateAndSentOrderInPreparation(order, opts = {}) {
        if (!order.isSynced) {
            return this.sendOrderInPreparation(order, opts);
        }

        const data = await this.data.call("pos.order", "get_preparation_change", [order.id]);
        const rawchange = data.last_order_preparation_change || "{}";
        const lastChanges = JSON.parse(rawchange);
        const lastServerDate = DateTime.fromSQL(lastChanges.metadata?.serverDate).toUTC();
        const lastLocalDate = DateTime.fromSQL(
            order.last_order_preparation_change?.metadata?.serverDate
        ).toUTC();

        if (lastServerDate.isValid && lastServerDate.ts != lastLocalDate.ts) {
            this.dialog.add(AlertDialog, {
                title: _t("Order Outdated"),
                body: _t(
                    "The order has been modified on another device. If you have modified existing " +
                        "order lines, check that your changes have not been overwritten.\n\n" +
                        "The order will be sent to the server with the last changes made on this device."
                ),
            });

            // Update before syncing otherwise it will overwrite the last change
            order.last_order_preparation_change = lastChanges;
            await this.syncAllOrders({ orders: [order] });
            return;
        }

        return this.sendOrderInPreparation(order, opts);
    }
    // Now the printer should work in PoS without restaurant
    async sendOrderInPreparation(order, opts = {}) {
        let isPrinted = false;

        if (this.config.printerCategories.size && !opts.byPassPrint) {
            try {
                let reprint = false;
                let orderChange = changesToOrder(
                    order,
                    this.config.printerCategories,
                    opts.cancelled
                );

                const hasChanges =
                    orderChange.new.length ||
                    orderChange.cancelled.length ||
                    orderChange.noteUpdate.length ||
                    orderChange.internal_note ||
                    orderChange.general_customer_note;

                let shouldPrint = true;
                if (!hasChanges) {
                    if (opts.explicitReprint && order.uiState.lastPrints) {
                        orderChange = [order.uiState.lastPrints.at(-1)];
                        reprint = true;
                    } else {
                        shouldPrint = false;
                    }
                } else {
                    order.uiState.lastPrints.push(orderChange);
                    orderChange = [orderChange];
                }

                if (reprint && opts.orderDone) {
                    shouldPrint = false;
                }

                if (shouldPrint) {
                    isPrinted = await this.printChanges(order, orderChange, reprint);
                }
            } catch (e) {
                logPosMessage(
                    "Store",
                    "sendOrderInPreparation",
                    "Failed in printing the changes in the order",
                    CONSOLE_COLOR,
                    [e]
                );
            }
        }
        order.updateLastOrderChange();
        // Ensure that other devices are aware of the changes
        // Otherwise several devices can print the same changes
        // We need to check if a preparation display is configured to avoid unnecessary sync
        if (isPrinted && !this.models["pos.prep.display"]?.length) {
            await this.syncAllOrders({ orders: [order] });
        }
    }
    async sendOrderInPreparationUpdateLastChange(o, opts) {
        if (this.data.network.offline) {
            this.data.network.warningTriggered = false;
            throw new ConnectionLostError();
        }
        await this.checkPreparationStateAndSentOrderInPreparation(o, opts);
    }

    getStrNotes(note) {
        if (!note) {
            return "";
        }
        if (Array.isArray(note)) {
            return note.map((n) => (typeof n === "string" ? n : n.text)).join(", ");
        }
        if (typeof note === "string") {
            try {
                const parsed = JSON.parse(note);
                if (Array.isArray(parsed)) {
                    return parsed.map((n) => (typeof n === "string" ? n : n.text)).join(", ");
                }
                return note;
            } catch (error) {
                logPosMessage(
                    "Store",
                    "getStrNotes",
                    "Error while parsing note, not valid JSON",
                    CONSOLE_COLOR,
                    [error]
                );
                return note;
            }
        }
        return "";
    }

    getOrderData(order, reprint) {
        return {
            reprint: reprint,
            pos_reference: order.getName(),
            config_name: order.config_id?.name || order.config.name,
            time: DateTime.now().toFormat("HH:mm"),
            tracking_number: order.tracking_number,
            preset_time: order.presetDateTime,
            preset_name: order.preset_id?.name || "",
            employee_name: order.employee_id?.name || order.user_id?.name,
            internal_note: this.getStrNotes(order.internal_note),
            general_customer_note: order.general_customer_note,
            changes: {
                title: "",
                data: [],
            },
        };
    }

    generateOrderChange(order, orderChange, categories, reprint = false) {
        const isPartOfCombo = (line) =>
            line.isCombo ||
            line.combo_parent_uuid ||
            this.models["product.product"].get(line.product_id).type == "combo";
        const comboChanges = orderChange.new.filter(isPartOfCombo);
        const normalChanges = orderChange.new.filter((line) => !isPartOfCombo(line));
        normalChanges.sort((a, b) => {
            const sequenceA = a.pos_categ_sequence;
            const sequenceB = b.pos_categ_sequence;
            if (sequenceA === 0 && sequenceB === 0) {
                return a.pos_categ_id - b.pos_categ_id;
            }

            return sequenceA - sequenceB;
        });
        orderChange.new = [...comboChanges, ...normalChanges];

        const orderData = this.getOrderData(order, reprint);

        const changes = this.filterChangeByCategories(categories, orderChange);
        for (const changeItem of [...changes.new, ...changes.cancelled, ...changes.noteUpdate]) {
            changeItem.note = this.getStrNotes(changeItem.note || "[]");
        }
        return { orderData, changes };
    }

    async generateReceiptsDataToPrint(orderData, changes, orderChange) {
        const receiptsData = [];
        if (changes.new.length) {
            const orderDataNew = { ...orderData };
            orderDataNew.changes = {
                title: _t("NEW"),
                data: changes.new,
            };
            receiptsData.push(await this.prepareReceiptGroupedData(orderDataNew));
        }

        if (changes.cancelled.length) {
            const orderDataCancelled = { ...orderData };
            orderDataCancelled.changes = {
                title: _t("CANCELLED"),
                data: changes.cancelled,
            };
            receiptsData.push(await this.prepareReceiptGroupedData(orderDataCancelled));
        }

        if (changes.noteUpdate.length) {
            const orderDataNoteUpdate = { ...orderData };
            const { noteUpdateTitle, printNoteUpdateData = true } = orderChange;
            orderDataNoteUpdate.changes = {
                title: noteUpdateTitle || _t("NOTE UPDATE"),
                data: printNoteUpdateData ? changes.noteUpdate : [],
            };
            receiptsData.push(await this.prepareReceiptGroupedData(orderDataNoteUpdate));
            orderData.changes.noteUpdate = [];
        }

        if (orderChange.internal_note || orderChange.general_customer_note) {
            const orderDataNote = { ...orderData };
            orderDataNote.changes = { title: "", data: [] };
            receiptsData.push(await this.prepareReceiptGroupedData(orderDataNote));
        }
        return receiptsData;
    }

    async printChanges(order, orderChange, reprint = false, printers = this.unwatched.printers) {
        let isPrinted = false;
        const unsuccessfulPrints = [];
        const retryPrinters = new Set();

        for (const printer of printers) {
            for (const change of orderChange) {
                const { orderData, changes } = this.generateOrderChange(
                    order,
                    change,
                    printer.config.product_categories_ids,
                    reprint
                );
                const receiptsData = await this.generateReceiptsDataToPrint(
                    orderData,
                    changes,
                    change
                );
                let result = {};
                for (const data of receiptsData) {
                    result = await this.printOrderChanges(data, printer);
                    if (result.successful) {
                        isPrinted = true;
                    }

                    if (!result.successful) {
                        retryPrinters.add(printer);
                        unsuccessfulPrints.push(printer.config.name + ": " + result.message.body);
                    } else if (result.warningCode) {
                        this.displayPrinterWarning(result, printer.config.name);
                    }
                }
            }
        }

        // printing errors
        if (unsuccessfulPrints.length) {
            const failedReceipts = unsuccessfulPrints.join("\n");
            this.dialog.add(RetryPrintPopup, {
                message: failedReceipts,
                canRetry: true,
                retry: () => {
                    this.printChanges(order, orderChange, reprint, retryPrinters);
                },
            });
        }

        return isPrinted;
    }

    async prepareReceiptGroupedData(data) {
        const dataChanges = data.changes?.data;
        if (dataChanges && dataChanges.some((c) => c.group)) {
            const groupedData = dataChanges.reduce((acc, c) => {
                const { name = "", index = -1 } = c.group || {};
                if (!acc[name]) {
                    acc[name] = { name, index, data: [] };
                }
                acc[name].data.push(c);
                return acc;
            }, {});
            data.changes.groupedData = Object.values(groupedData).sort((a, b) => a.index - b.index);
        }
        return data;
    }

    async printOrderChanges(data, printer) {
        const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
            data: data,
        });
        return await printer.printReceipt(receipt);
    }

    filterChangeByCategories(categories, currentOrderChange) {
        const matchesCategories = (change) => {
            const product = this.models["product.product"].get(change["product_id"]);
            const categoryIds = product.parentPosCategIds;
            for (const categoryId of categoryIds) {
                if (categories.includes(categoryId)) {
                    return true;
                }
            }
            return false;
        };

        const filterChanges = (changes) => {
            // Combo line uuids to have at least one child line in the given categories
            const validComboUuids = new Set(
                changes
                    .filter((change) => change.combo_parent_uuid && matchesCategories(change))
                    .map((change) => change.combo_parent_uuid)
            );
            return changes.filter(
                (change) =>
                    (change.isCombo && validComboUuids.has(change.uuid)) ||
                    (!change.isCombo && matchesCategories(change))
            );
        };

        return {
            new: filterChanges(currentOrderChange["new"]),
            cancelled: filterChanges(currentOrderChange["cancelled"]),
            noteUpdate: filterChanges(currentOrderChange["noteUpdate"]),
        };
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
    editPartnerContext(partner) {
        return {};
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
                additionalContext: this.editPartnerContext(),
            }
        );
        const newPartner = await this.data.read("res.partner", record.config.resIds);
        return newPartner[0];
    }
    /**
     * @param {import("@point_of_sale/app/models/product_product").ProductProduct?} product leave undefined to create a new product
     */
    async editProduct(product) {
        const orderContainsProduct = product && this.orderContainsProduct(product);
        this.action.doAction(
            product
                ? "point_of_sale.product_template_action_edit_pos"
                : "point_of_sale.product_template_action_add_pos",
            {
                props: {
                    resId: product?.id,
                    onSave: (record) => {
                        this.data.read("product.template", [record.evalContext.id]);
                        this.data.searchRead("product.product", [
                            ["product_tmpl_id", "=", record.evalContext.id],
                        ]);
                        this.action.doAction({
                            type: "ir.actions.act_window_close",
                        });
                    },
                },
                additionalContext: {
                    taxes_readonly: orderContainsProduct,
                },
            }
        );
    }
    orderContainsProduct(product) {
        const lines = this.getOpenOrders().flatMap((o) => o.lines);
        return lines.some((l) => l.product_id.product_tmpl_id.id === product.id);
    }
    async loadSampleData() {
        const [isPosManager, isAdmin] = await Promise.all([
            user.hasGroup("point_of_sale.group_pos_manager"),
            user.hasGroup("base.group_system"),
        ]);

        if (!(isPosManager && isAdmin)) {
            this.dialog.add(AlertDialog, {
                title: _t("Access Denied"),
                body: _t("It seems like you don't have enough rights to load data."),
            });
            return;
        }
        await this.data.call("pos.config", "load_demo_data", [[this.config.id]]);
        await this.reloadData(true);
    }
    async allowProductCreation() {
        return await user.checkAccessRight("product.product", "create");
    }
    orderDetailsProps(order) {
        return {
            resModel: "pos.order",
            resId: order.id,
            context: {
                from_frontend: true,
            },
            onRecordSaved: async (record) => {
                await this.data.loadServerOrders([["id", "=", record.evalContext.id]]);
                this.action.doAction({
                    type: "ir.actions.act_window_close",
                });
            },
        };
    }
    async orderDetails(order) {
        this.dialog.add(FormViewDialog, this.orderDetailsProps(order));
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
    async openPresetTiming(order = this.getOrder()) {
        const data = await makeAwaitable(this.dialog, PresetSlotsPopup);
        if (data) {
            if (order.preset_id.id != data.presetId) {
                await this.selectPreset(this.models["pos.preset"].get(data.presetId));
            }

            order.preset_time = data.slot.datetime;
            if (data.slot.datetime > DateTime.now()) {
                this.addPendingOrder([order.id]);
                await this.syncAllOrders({ orders: [order] });
            }
        }
    }
    async handleSelectNamePreset(order) {
        if (!order.partner_id) {
            const partner = await this.selectPartner();
            if (!partner) {
                return;
            }
        }
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
                size: "md",
            });
        }

        if (preset) {
            order.setPreset(preset);

            if (preset.needsPartner) {
                const partner = order.partner_id || (await this.selectPartner(order));
                if (!partner) {
                    return;
                }
                if (!(partner.street || partner.street2)) {
                    this.notification.add(_t("Customer address is required"), { type: "warning" });
                    await this.editPartner(partner);
                    if (!(partner.street || partner.street2)) {
                        return;
                    }
                }
            }

            if (preset.identification === "name") {
                await this.handleSelectNamePreset(order);
            }

            if (preset.use_timing && !order.preset_time) {
                await this.openPresetTiming(order);
                if (!order.preset_time) {
                    await this.syncPresetSlotAvaibility(preset);
                    order.preset_time = preset.nextSlot?.datetime || false;
                }
            } else if (!preset.use_timing) {
                order.preset_time = false;
            }
        }
    }
    orderUsageUTCtoLocal(data) {
        return orderUsageUTCtoLocalUtil(data);
    }
    async syncPresetSlotAvaibility(preset) {
        try {
            const result = await this.data.call("pos.preset", "get_available_slots", [preset.id]);
            const localUsage = this.orderUsageUTCtoLocal(result.usage_utc);
            preset.computeAvailabilities(localUsage);
        } catch {
            // Compute locally if the server is not reachable
            preset.computeAvailabilities();
        }
    }
    // There for override to do something before adding partner to current order from partner list
    setPartnerToCurrentOrder(partner) {
        this.getOrder().setPartner(partner);
    }
    async selectPartner(currentOrder = this.getOrder()) {
        // FIXME, find order to refund when we are in the ticketscreen.
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

        this.setPartnerToCurrentOrder(payload || false);

        return payload;
    }
    async editLotsRefund(line) {
        const product = line.getProduct();
        const packLotLinesToEdit = line.pack_lot_ids.map((p) => ({
            id: p.id,
            text: p.lot_name,
        }));
        const alreadyRefundedLots = line.refunded_orderline_id.refund_orderline_ids
            .filter((item) => !["cancel", "draft"].includes(item.order_id.state))
            .flatMap((item) => item.pack_lot_ids)
            .map((p) => p.lot_name);
        const options = line.refunded_orderline_id.pack_lot_ids
            .map((p) => ({ id: p.id, name: p.lot_name, product_qty: line.qty }))
            .filter((lot) => !alreadyRefundedLots.includes(lot.name));
        const payload = await makeAwaitable(this.dialog, SelectLotPopup, {
            title: _t("Lot/Serial number(s) required for"),
            name: product.display_name,
            isSingleItem: product.isAllowOnlyOneLot(),
            array: packLotLinesToEdit,
            options: options,
            customInput: false,
            uniqueValues: product.tracking === "serial",
            isLotNameUsed: () => false,
        });
        if (payload) {
            const modifiedPackLotLines = {};
            const newPackLotLines = [];
            for (const item of payload) {
                if (item.id) {
                    modifiedPackLotLines[item.id] = item.text;
                } else {
                    newPackLotLines.push({ lot_name: item.text });
                }
            }
            return { modifiedPackLotLines, newPackLotLines };
        } else {
            return null;
        }
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
            logPosMessage("Store", "editLots", "Collecting existing lots failed", CONSOLE_COLOR, [
                ex,
            ]);
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

        const usedLotsQty = this.models["pos.pack.operation.lot"]
            .filter(
                (lot) =>
                    lot.pos_order_line_id?.product_id?.id === product.id &&
                    lot.pos_order_line_id?.order_id?.state === "draft"
            )
            .reduce((acc, lot) => {
                if (!acc[lot.lot_name]) {
                    acc[lot.lot_name] = { total: 0, currentOrderCount: 0 };
                }
                acc[lot.lot_name].total += lot.pos_order_line_id?.qty || 0;

                if (lot.pos_order_line_id?.order_id?.id === this.selectedOrder.id) {
                    acc[lot.lot_name].currentOrderCount += lot.pos_order_line_id?.qty || 0;
                }
                return acc;
            }, {});

        // Remove lot/serial names that are already used in draft orders
        existingLots = existingLots.filter(
            (lot) => lot.product_qty > (usedLotsQty[lot.name]?.total || 0)
        );

        // Check if the input lot/serial name is already used in another order
        const isLotNameUsed = (itemValue) => {
            const totalQty = existingLots.find((lt) => lt.name == itemValue)?.product_qty || 0;
            const usedQty = usedLotsQty[itemValue]
                ? usedLotsQty[itemValue].total - usedLotsQty[itemValue].currentOrderCount
                : 0;
            return usedQty ? usedQty >= totalQty : false;
        };

        const existingLotsName = existingLots.map((l) => l.name);
        if (!packLotLinesToEdit.length && existingLotsName.length === 1) {
            // If there's only one existing lot/serial number, automatically assign it to the order line
            return { newPackLotLines: [{ lot_name: existingLotsName[0] }] };
        }
        const payload = await makeAwaitable(this.dialog, SelectLotPopup, {
            title: _t("Lot/Serial number(s) required for"),
            name: product.display_name,
            isSingleItem: isAllowOnlyOneLot,
            array: packLotLinesToEdit,
            options: existingLots,
            customInput: canCreateLots,
            uniqueValues: product.tracking === "serial",
            isLotNameUsed: isLotNameUsed,
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
                            this.router.state.current === "ProductScreen"
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
                        logPosMessage(
                            "Store",
                            "editLots",
                            "POS / Session opened in another window. EXITING POS",
                            CONSOLE_COLOR
                        );
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
            (this.router.state.current !== "ProductScreen" || this.mobile_pane === "left")
        );
    }
    async onClickBackButton() {
        if (this.router.state.current === "TicketScreen") {
            if (this.ticket_screen_mobile_pane == "left") {
                const next = this.defaultPage;
                this.navigate(next.page, next.params);
            } else {
                this.ticket_screen_mobile_pane = "left";
            }
        } else if (
            this.mobile_pane == "left" ||
            ["PaymentScreen", "ActionScreen"].includes(this.router.state.current)
        ) {
            if (this.router.state.current === "ProductScreen") {
                this.getOrder().deselectOrderline();
            }

            this.mobile_pane = this.router.state.current === "PaymentScreen" ? "left" : "right";
            this.navigate("ProductScreen", {
                orderUuid: this.getOrder().uuid,
            });
        }
    }

    showSearchButton() {
        if (this.router.state.current === "ProductScreen") {
            return this.ui.isSmall ? this.mobile_pane === "right" : true;
        }
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
        payment.qrPaymentData = {
            name: payment.payment_method_id.name,
            amount: this.env.utils.formatCurrency(payment.amount),
            qrCode: qr,
        };
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
        ).then((result) => {
            payment.qrPaymentData = null;
            return result;
        });
    }

    redirectToBackend() {
        window.location = "/odoo/action-point_of_sale.action_client_pos_menu";
    }

    getExcludedProductIds() {
        return [
            this.config.tip_product_id?.product_tmpl_id?.id,
            ...this.config._pos_special_products_ids.map(
                (id) => this.models["product.product"].get(id)?.product_tmpl_id?.id
            ),
        ].filter(Boolean);
    }

    areAllProductsSpecial(products) {
        const specialDisplayProductIds = this.config._pos_special_display_products_ids || [];
        return (
            specialDisplayProductIds.length >= products.length &&
            products.every((product) => specialDisplayProductIds.includes(product.id))
        );
    }

    orderProductBySequenceAndFav(products) {
        const searchWord = this.searchProductWord.trim();
        const isSearchByWord = searchWord !== "";
        return isSearchByWord
            ? products.sort((a, b) => b.is_favorite - a.is_favorite)
            : products.sort((a, b) => {
                  if (b.is_favorite !== a.is_favorite) {
                      return b.is_favorite - a.is_favorite;
                  } else if (a.pos_sequence !== b.pos_sequence) {
                      return a.pos_sequence - b.pos_sequence;
                  }
                  return a.name.localeCompare(b.name);
              });
    }

    get productsToDisplay() {
        const searchWord = this.searchProductWord.trim();
        const allProducts = this.models["product.template"].getAll();
        let list = [];
        const isSearchByWord = searchWord !== "";

        if (isSearchByWord) {
            if (!this._searchTriggered) {
                this.setSelectedCategory(0);
                this._searchTriggered = true;
            }
            list = this.getProductsBySearchWord(
                searchWord,
                this.selectedCategory?.id ? this.selectedCategory.associatedProducts : allProducts
            );
        } else {
            this._searchTriggered = false;
            if (this.selectedCategory?.id) {
                list = this.selectedCategory.associatedProducts;
            } else {
                list = allProducts;
            }
        }

        if (!list || list.length === 0) {
            return [];
        }

        const filteredList = [];
        const excludedProductIds = new Set(this.getExcludedProductIds());
        const availableCateg = new Set(
            (this.config.iface_available_categ_ids || []).map((c) => c.id)
        );

        for (const p of list) {
            if (filteredList.length >= 100) {
                break;
            }

            if (excludedProductIds.has(p.id) || !p.canBeDisplayed) {
                continue;
            }

            if (
                availableCateg.size &&
                !this.config._pos_special_display_products_ids?.includes(p.id) &&
                !p.pos_categ_ids.some((c) => availableCateg.has(c.id))
            ) {
                continue;
            }

            filteredList.push(p);
        }

        if (
            !isSearchByWord &&
            !this.selectedCategory?.id &&
            this.areAllProductsSpecial(filteredList)
        ) {
            return [];
        }

        return this.orderProductBySequenceAndFav(filteredList);
    }

    get productToDisplayByCateg() {
        const sortedProducts = this.productsToDisplay;
        if (!this.config.iface_group_by_categ) {
            return sortedProducts.length ? [["0", sortedProducts]] : [];
        }

        const results = [];
        const searchWord = this.searchProductWord.trim();
        const byCateg = this.models["product.template"].getAllBy("pos_categ_ids");
        const selectedCategoryIds = !this.selectedCategory
            ? this.models["pos.category"].map((c) => c.id)
            : this.selectedCategory.getAllChildren().map((c) => c.id);

        // Sorting in place the categories according to their sequence in the database
        selectedCategoryIds.sort((a, b) => {
            const categA = this.models["pos.category"].get(a);
            const categB = this.models["pos.category"].get(b);

            // All category with a parent will be at the end
            if (categA.parent_id && !categB.parent_id) {
                return 1;
            } else if (!categA.parent_id && categB.parent_id) {
                return -1;
            }

            return categA.sequence - categB.sequence;
        });

        if (!this.selectedCategory) {
            // In case of no category selected, we want to display products without category in
            // a "Without category" category at the end of the list.
            // We use the default sortedProducts order to keep the same order as in the non
            // group by category mode.
            const productWithoutCategory = sortedProducts.filter((p) => !p.pos_categ_ids.length);
            byCateg["0"] = productWithoutCategory;
            selectedCategoryIds.push("0");
        }

        for (const catId of selectedCategoryIds) {
            const products = byCateg[catId] || [];
            const filtered = searchWord
                ? this.getProductsBySearchWord(searchWord, products)
                : products;

            if (filtered.length) {
                // Its advised to not use group by categ with too much products in differents
                // categories, but in case of we end up with too much products, we slice them in
                // group of 100 to avoid freezing the browser tab.
                // We cannot just slice the products to display and keep the same category, because
                // we want to avoid having categories with only few products displayed and others
                // with a lot of products not displayed.
                const sorted = this.orderProductBySequenceAndFav(filtered);
                results.push([catId, sorted.splice(0, 100)]);
            }
        }

        return results;
    }

    getProductsBySearchWord(searchWord, products) {
        const query = normalize(searchWord);
        const matches = [];

        for (const product of products) {
            const searchStr = product.searchString;

            if (searchStr.includes(query)) {
                const normName = product.normalizedName;
                matches.push({
                    product: product,
                    index: normName.indexOf(query),
                    name: normName,
                });
            }
        }

        matches.sort(
            (a, b) =>
                (a.index === -1) - (b.index === -1) ||
                a.index - b.index ||
                (a.name == b.name ? 0 : a.name > b.name ? 1 : -1)
        );

        return matches.map((m) => m.product);
    }
    getPaymentMethodFmtAmount(pm, order) {
        const amount = order.getDefaultAmountDueToPayIn(pm);
        const fmtAmount = this.env.utils.formatCurrency(amount, true);

        if (!this.currency.isPositive(amount) || !this.config.cash_rounding) {
            return;
        }
        if (!this.config.only_round_cash_method || pm.type === "cash") {
            return fmtAmount;
        }
    }
    getDate(date) {
        const todayTs = DateTime.now().startOf("day").ts;
        if (date.toLocal().startOf("day").ts === todayTs) {
            return _t("Today");
        } else {
            return formatDate(date);
        }
    }
    getTime(date) {
        return date.toFormat(localization.timeFormat);
    }

    orderDone(order) {
        order.setScreenData({ name: "" });
        if (!this.config.module_pos_restaurant) {
            this.selectedOrderUuid = this.getEmptyOrder().uuid;
        }
        this.searchProductWord = "";
        const nextPage = this.defaultPage;
        this.navigate(nextPage.page, nextPage.params);
    }

    displayPrinterWarning(printResult, printerName) {
        let notification;
        if (printResult.warningCode === "ROLL_PAPER_HAS_ALMOST_RUN_OUT") {
            notification = _t("%s almost runs out of paper.", printerName);
        }
        if (notification) {
            this.notification.add(notification, {
                type: "warning",
            });
        }
    }

    async isSessionDeleted() {
        return (
            (await this.data.orm.searchCount("pos.session", [["id", "=", this.session.id]])) === 0
        );
    }

    weighProduct() {
        return makeAwaitable(this.env.services.dialog, ScaleScreen);
    }

    async validateOrderFast(paymentMethod) {
        const validation = new OrderPaymentValidation({
            pos: this,
            orderUuid: this.getOrder().uuid,
            fastPaymentMethod: paymentMethod,
        });
        await validation.validateOrder(false);
    }

    clickSaveOrder() {
        this.syncAllOrders({ orders: [this.getOrder()] });
        this.notification.add(_t("Order saved for later"), { type: "success" });
        this.setOrder(this.getEmptyOrder());
        this.mobile_pane = "right";
    }

    get showSaveOrderButton() {
        return this.config.raw.trusted_config_ids.length > 0;
    }

    canEditPayment(order) {
        return order.nb_print === 0;
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
