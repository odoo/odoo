/** @odoo-module native */
/* global waitForWebfonts */

import { markRaw, reactive, toRaw } from "@odoo/owl";
import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { ComboConfiguratorPopup } from "@point_of_sale/app/components/popups/combo_configurator_popup/combo_configurator_popup";
import { OpeningControlPopup } from "@point_of_sale/app/components/popups/opening_control_popup/opening_control_popup";
import { PresetSlotsPopup } from "@point_of_sale/app/components/popups/preset_slots_popup/preset_slots_popup";
import { ProductConfiguratorPopup } from "@point_of_sale/app/components/popups/product_configurator_popup/product_configurator_popup";
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { QRPopup } from "@point_of_sale/app/components/popups/qr_code_popup/qr_code_popup";
import { RetryPrintPopup } from "@point_of_sale/app/components/popups/retry_print_popup/retry_print_popup";
import { SelectLotPopup } from "@point_of_sale/app/components/popups/select_lot_popup/select_lot_popup";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import {
    ask,
    makeActionAwaitable,
    makeAwaitable,
} from "@point_of_sale/app/utils/make_awaitable_dialog";
import { EpsonPrinter } from "@point_of_sale/app/utils/printer/epson_printer";
import { HWPrinter } from "@point_of_sale/app/utils/printer/hw_printer";
import { WithLazyGetterTrap } from "@point_of_sale/lazy_getter";
import {
    deduceUrl,
    orderUsageUTCtoLocalUtil,
    random5Chars,
    uuidv4,
} from "@point_of_sale/utils";
import { router as webRouter } from "@web/core/browser/router";
import { makeLogger } from "@web/core/debug/debug_logger";
import { Domain } from "@web/core/domain";
import { formatDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { luxon } from "@web/core/l10n/luxon";
import { ConnectionLostError } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { Mutex } from "@web/core/utils/concurrency";
import { effect } from "@web/core/utils/reactive";
import { renderToElement } from "@web/core/utils/render";
import { debounce } from "@web/core/utils/timing";
import { AlertDialog } from "@web/ui/dialog";
import { FormViewDialog } from "@web/views/view_dialogs";

import { SelectionPopup } from "../components/popups/selection_popup/selection_popup.js";
import { PRODUCT_UNIT } from "../models/decimal_precision.js";
import { computeComboItems } from "../models/utils/compute_combo_items.js";
import { changesToOrder, getOrderChanges } from "../models/utils/order_change.js";
import {
    computeProductAttributesExclusion,
    doHaveConflictWith,
} from "../models/utils/product_attributes.js";
import { PartnerList } from "../screens/partner_list/partner_list.js";
import { ScaleScreen } from "../screens/scale_screen/scale_screen.js";
import {
    cashierHasPriceControlRights,
    getCashier,
    getCashierUserId,
    getConnectedCashier,
    resetCashier,
    resetConnectedCashier,
    setCashier,
    storeConnectedCashier,
} from "../utils/cashier.js";
import { DebugWidget } from "../utils/debug/debug_widget.js";
import DevicesSynchronisation from "../utils/devices_synchronisation.js";
import { initLNA } from "../utils/init_lna.js";
import {
    filterChangeByCategories,
    generateOrderChange,
    generateReceiptsDataToPrint,
    getOrderData,
    getStrNotes,
    prepareReceiptGroupedData,
} from "../utils/order_change_receipts.js";
import OrderPaymentValidation from "../utils/order_payment_validation.js";
import {
    addPendingOrder,
    clearPendingOrder,
    getOrderIdsToDelete,
    getPendingOrder,
    removePendingOrder,
    shouldCreatePendingOrder,
} from "../utils/pending_orders.js";
import {
    computeDefaultPage,
    computeFirstPage,
    consumeBootFlags,
    navigate,
    navigateToFirstPage,
    navigateToOrderScreen,
    showBackButton,
    showSearchButton,
    switchPane,
    switchPaneTicketScreen,
} from "../utils/pos_navigation.js";
import { logPosMessage } from "../utils/pretty_console_log.js";
import {
    areAllProductsSpecial,
    computeProductsToDisplay,
    computeProductToDisplayByCateg,
    getExcludedProductIds,
    getProductsBySearchWord,
    orderProductBySequenceAndFav,
} from "../utils/product_catalog.js";

const { DateTime } = luxon;
export const CONSOLE_COLOR = "#F5B427";
const MAX_LAST_PRINTS = 10;
const log = makeLogger("pos.store");

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
    ];
    constructor({ traps, env, deps }) {
        super({ traps });
        const reactiveSelf = reactive(this);
        reactiveSelf.ready = reactiveSelf.setup(env, deps).then(() => reactiveSelf);
        return reactiveSelf;
    }
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
        },
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
        this.printCountMutex = new Mutex();
        this.router.popStateCallback = this.handleUrlParams.bind(this);

        this.validated_orders_name_server_id_map = {};
        this.numpadMode = "quantity";
        this.mobile_pane = "right";
        this.ticket_screen_mobile_pane = "left";

        this.loadingOrderState = false;
        this.screenState = {
            ticketScreen: {
                syncedPageOrderIds: [],
                totalCount: 0,
            },
            partnerList: {
                offsetBySearch: {},
            },
        };
        this.pendingOrder = {
            write: new Set(),
            delete: new Set(),
            create: new Set(),
        };

        this.hardwareProxy = hardware_proxy;
        this.selectedOrderUuid = null;
        this.selectedPartner = null;
        this.selectedCategory = null;
        this.searchProductWord = "";
        this.scale = pos_scale;

        this.hardwareProxy.pos = this;
        this.syncingOrders = new Set();
        this.syncAllOrdersDebounced = debounce(this.syncAllOrders, 100);
        const endSetup = log.perf("setup");
        log.lifecycle("setup", () => ({
            config: odoo.pos_config_id,
            session: odoo.pos_session_id,
            debug: env.debug,
        }));
        await this.initServerData();

        log.logic("setup: proxy", () => ({ useProxy: this.config.useProxy }));
        if (this.config.useProxy) {
            await this.connectToProxy();
        }
        this.closeOtherTabs();
        endSetup({
            config: this.config.id,
            session: this.session?.id,
            orders: this.models["pos.order"].length,
        });

        if (this.env.debug) {
            registry.category("main_components").add("DebugWidget", {
                Component: DebugWidget,
            });
        }

        window.addEventListener("pos-network-online", () => {
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
        log.lifecycle("navigate", () => ({
            routeName,
            routeParams,
            from: this.router?.state?.current,
        }));
        return navigate(this, routeName, routeParams);
    }

    navigateToFirstPage() {
        return navigateToFirstPage(this);
    }

    navigateToOrderScreen(order) {
        return navigateToOrderScreen(this, order);
    }

    getDefaultPage() {
        return computeDefaultPage(this);
    }

    get firstPage() {
        return computeFirstPage(this);
    }

    bootPage() {
        consumeBootFlags(this);
        return this.firstPage;
    }

    get idleTimeout() {
        return [
            {
                timeout: 300000,
                action: () =>
                    this.router.state.current !== "PaymentScreen" &&
                    this.navigate("SaverScreen"),
            },
            {
                timeout: 120000,
                action: () =>
                    this.router.state.current === "LoginScreen" &&
                    this.navigate("SaverScreen"),
            },
        ];
    }

    async reloadData(fullReload = false) {
        log.lifecycle("reloadData", () => ({ fullReload }));
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
        log.lifecycle("showLoginScreen", () => ({ cashier: this.cashier?.id }));
        this.resetCashier();
        this.navigate("LoginScreen");
        this.dialog.closeAll();
    }

    resetCashier() {
        return resetCashier(this);
    }

    checkPreviousLoggedCashier() {
        const savedCashier = this._getConnectedCashier();
        log.logic("checkPreviousLoggedCashier", () => ({
            found: Boolean(savedCashier),
            cashier: savedCashier?.id,
        }));
        if (savedCashier) {
            this.setCashier(savedCashier);
        }
    }

    setCashier(user) {
        log.lifecycle("setCashier", () => ({ user: user?.id, name: user?.name }));
        return setCashier(this, user);
    }

    _getConnectedCashier() {
        return getConnectedCashier(this);
    }

    _storeConnectedCashier(user) {
        return storeConnectedCashier(this, user);
    }

    _resetConnectedCashier() {
        return resetConnectedCashier(this);
    }

    async initServerData() {
        const endInit = log.perf("initServerData");
        await this.processServerData();
        endInit({ models: Object.keys(this.models).length });

        let searchWasActive = false;
        effect(
            (self) => {
                const active = self.searchProductWord.trim() !== "";
                if (active && !searchWasActive) {
                    self.setSelectedCategory(0);
                }
                searchWasActive = active;
            },
            [this],
        );

        await this.handleUrlParams();
        this.data.connectWebSocket(
            "CLOSING_SESSION",
            this.closingSessionNotification.bind(this),
        );
        const endAfter = log.perf("afterProcessServerData");
        const process = await this.afterProcessServerData();
        endAfter({ selectedOrder: this.selectedOrderUuid });

        log.logic("initServerData: cashier", () => ({
            current: this.router.state.current,
            module_pos_hr: this.config.module_pos_hr,
            autoSetCashier:
                this.router.state.current !== "LoginScreen" &&
                !this.config.module_pos_hr,
        }));
        if (this.router.state.current !== "LoginScreen" && !this.config.module_pos_hr) {
            this.setCashier(this.user);
        }

        const page =
            this.router.state.current === "LoginScreen"
                ? this.bootPage()
                : {
                      page: this.router.state.current,
                      params: this.router.state.params,
                  };
        log.pipeline("initServerData: boot page", () => ({
            fromLogin: this.router.state.current === "LoginScreen",
            page: page.page,
            params: page.params,
        }));
        this.navigate(page.page, page.params);
        return process;
    }

    async closingSessionNotification(data) {
        const ignored =
            data.device_identifier === this.device.identifier ||
            this.session.id !== parseInt(data.session_id);
        log.pipeline("[bus] CLOSING_SESSION", () => ({
            ignored,
            ownDevice: data.device_identifier === this.device.identifier,
            session: data.session_id,
            currentSession: this.session.id,
        }));
        if (ignored) {
            return;
        }

        try {
            const paidOrderNotSynced = this.models["pos.order"].filter(
                (order) => order.state === "paid" && !order.isSynced,
            );
            log.logic("closingSessionNotification: unsynced paid orders", () => ({
                count: paidOrderNotSynced.length,
            }));
            this.addPendingOrder(paidOrderNotSynced.map((o) => o.id));
            await this.syncAllOrders({ throw: true });

            this.dialog.add(AlertDialog, {
                title: _t("Closing Session"),
                body: _t(
                    "The session is being closed by another user. The page will be reloaded.",
                ),
            });
        } catch {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t(
                    "An error occurred while closing the session. Unsynced orders will be available in the next session. The page will be reloaded.",
                ),
            });
        } finally {
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
        const endProcess = log.perf("processServerData");
        this.device = this.data.device;

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
        const deviceSync = new DevicesSynchronisation(
            dynamicModels,
            staticModels,
            this,
        );

        this.deviceSync = deviceSync;
        this.data.deviceSync = deviceSync;
        log.pipeline("processServerData: models", () => ({
            models: models.length,
            dynamic: dynamicModels,
            static: staticModels.length,
            device: this.device?.identifier,
        }));

        const endRead = log.perf("processServerData: readDataFromServer");
        await this.deviceSync.readDataFromServer();
        endRead();

        this.checkPreviousLoggedCashier();

        for (const pm of this.models["pos.payment.method"].getAll()) {
            const PaymentInterface =
                this.electronic_payment_interfaces[pm.use_payment_terminal];
            log.logic("processServerData: payment terminal", () => ({
                method: pm.id,
                terminal: pm.use_payment_terminal,
                bound: Boolean(PaymentInterface),
            }));
            if (PaymentInterface) {
                pm.payment_terminal = new PaymentInterface(this, pm);
            }
        }

        this.unwatched.printers = [];
        for (const relPrinter of this.models["pos.printer"].getAll()) {
            const printer = relPrinter.raw;
            const HWPrinter = this.createPrinter(printer);

            HWPrinter.config = printer;
            this.unwatched.printers.push(HWPrinter);
        }
        this.config.iface_printers = !!this.unwatched.printers.length;
        log.logic("processServerData: printers", () => ({
            printers: this.unwatched.printers.length,
            types: this.unwatched.printers.map((p) => p.config?.printer_type),
        }));

        this.models["product.pricelist.item"].addEventListener("create", () => {
            const order = this.getOrder();
            log.logic("[event] product.pricelist.item create", () => ({
                order: order?.uuid,
                pricelist: order?.pricelist_id?.id,
            }));
            if (!order) {
                return;
            }
            const currentPricelistId = order.pricelist_id?.id;
            order.setPricelist(
                this.models["product.pricelist"].get(currentPricelistId),
            );
        });

        await this.processProductAttributes();
        const endLogo = log.perf("processServerData: cacheReceiptLogo");
        await this.config.cacheReceiptLogo();
        endLogo();
        endProcess({
            products: this.models["product.product"].length,
            partners: this.models["res.partner"].length,
            orders: this.models["pos.order"].length,
        });
    }
    cashMove() {
        this.hardwareProxy.openCashbox(_t("Cash in / out"));
        return makeAwaitable(this.dialog, CashMovePopup);
    }
    async closeSession() {
        log.logic("closeSession", () => ({ session: this.session?.id }));
        await this.pushOrdersWithClosingPopup();
        const info = await this.getClosePosInfo();

        if (info) {
            this.dialog.add(ClosePosPopup, info);
        }
    }
    async processProductAttributes() {
        const endAttributes = log.perf("processProductAttributes");
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

        log.logic("processProductAttributes: variants", () => ({
            products: productIds.size,
            templates: productTmplIds.size,
            fetchSiblings: productIds.size > 0,
        }));
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
                    [error],
                );
            }
        }

        for (const product of this.models["product.product"].filter(
            (p) =>
                !productIds.has(p.id) &&
                p.product_template_variant_value_ids.length > 0,
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
        endAttributes({ templates: Object.keys(productByTmplId).length });
    }

    computeProductAttributesExclusion(excl = false) {
        return computeProductAttributesExclusion(this, excl);
    }

    doHaveConflictWith(value, selectedValues) {
        return doHaveConflictWith(this, value, selectedValues);
    }

    async beforeDeleteOrder(order, { title, body } = {}) {
        log.logic("beforeDeleteOrder", () => ({
            order: order.uuid,
            lines: order.getOrderlines().length,
            askConfirmation: order.getOrderlines().length > 0,
        }));
        if (order.getOrderlines().length > 0) {
            return await ask(this.dialog, {
                title: title || _t("Existing orderlines"),
                body:
                    body ||
                    _t(
                        "%s has a total amount of %s, are you sure you want to delete this order?",
                        order.pos_reference,
                        this.env.utils.formatCurrency(order.priceIncl),
                    ),
            });
        }
        return true;
    }
    async onDeleteOrder(order) {
        const canDelete = await this.beforeDeleteOrder(order);
        log.lifecycle("onDeleteOrder", () => ({ order: order.uuid, canDelete }));
        if (!canDelete) {
            return false;
        }
        const refundedOrderLines = order.lines
            .filter((line) => line.refunded_orderline_id?.order_id)
            .map((line) => ({
                order: line.refunded_orderline_id.order_id,
                uuid: line.refunded_orderline_id.uuid,
            }));

        const orderIsDeleted = await this.removeOrders([order]);
        log.logic("onDeleteOrder: removed", () => ({
            order: order.uuid,
            orderIsDeleted,
            refundedLines: refundedOrderLines.length,
        }));
        if (!orderIsDeleted) {
            return false;
        }
        order.uiState.displayed = false;
        for (const refundedLine of refundedOrderLines) {
            delete refundedLine.order?.uiState?.lineToRefund[refundedLine.uuid];
        }

        await this.afterOrderDeletion();
        return true;
    }
    async afterOrderDeletion() {
        log.logic("afterOrderDeletion", () => ({
            restaurant: this.config.module_pos_restaurant,
            openOrders: this.getOpenOrders().length,
        }));
        if (!this.config.module_pos_restaurant) {
            this.setOrder(this.getOpenOrders().at(-1) || this.addNewOrder());
        }
    }

    async removeOrders(orders, serverIds = [], ignoreChange = false) {
        const endRemove = log.perf("removeOrders");
        log.pipeline("removeOrders", () => ({
            orders: orders.map((o) => o?.uuid),
            serverIds,
            ignoreChange,
        }));
        const ordersToDelete = [];
        const failedOrders = [];
        let serverIdsFailed = false;
        const actionPosOrderCancelCall = async (orderIds) => {
            await this.data.call("pos.order", "action_pos_order_cancel", [orderIds], {
                context: {
                    device_identifier: this.device.identifier,
                },
            });
        };
        for (const order of orders) {
            if (order && !(await this._onBeforeRemoveOrder(order))) {
                return false;
            }
        }
        try {
            for (const order of orders) {
                if (!order) {
                    continue;
                }
                try {
                    if (
                        !ignoreChange &&
                        order.isSynced &&
                        Object.keys(order.last_order_preparation_change).length > 0
                    ) {
                        const orderPresetDate = DateTime.fromISO(order.preset_time);
                        const isSame = DateTime.now().hasSame(orderPresetDate, "day");
                        log.logic("removeOrders: cancel preparation", () => ({
                            order: order.uuid,
                            presetTime: order.preset_time,
                            sendCancel: !order.preset_time || isSame,
                        }));
                        if (!order.preset_time || isSame) {
                            await this.sendOrderInPreparation(order, {
                                cancelled: true,
                                orderDone: true,
                            });
                        }
                    }

                    log.logic("removeOrders: server cancel", () => ({
                        order: order.uuid,
                        id: order.id,
                        isSynced: order.isSynced,
                    }));
                    if (order.isSynced) {
                        await actionPosOrderCancelCall([order.id]);
                    }
                    ordersToDelete.push(order);
                } catch (error) {
                    failedOrders.push(order);
                    log.logic("removeOrders: cancel failed", () => ({
                        order: order.uuid,
                        error: error?.message,
                    }));
                    logPosMessage(
                        "Store",
                        "removeOrders",
                        `Failed to cancel order ${order.uuid}`,
                        CONSOLE_COLOR,
                        [error],
                    );
                }
            }

            if (serverIds.length > 0) {
                try {
                    await actionPosOrderCancelCall([
                        ...new Set(serverIds.filter((id) => typeof id === "number")),
                    ]);
                    for (const id of serverIds) {
                        this.pendingOrder.delete.delete(id);
                    }
                } catch (error) {
                    serverIdsFailed = true;
                    logPosMessage(
                        "Store",
                        "removeOrders",
                        "Failed to cancel server-side order ids",
                        CONSOLE_COLOR,
                        [error],
                    );
                }
            }
        } finally {
            for (const order of ordersToDelete) {
                this.removeOrder(order, false);
                this.removePendingOrder(order);
            }
        }
        endRemove({
            deleted: ordersToDelete.length,
            failed: failedOrders.length,
            serverIdsFailed,
        });

        if (failedOrders.length || serverIdsFailed) {
            const names = failedOrders
                .map((order) => order.getName() || order.pos_reference || order.uuid)
                .join(", ");
            this.dialog.add(AlertDialog, {
                title: _t("Some orders could not be cancelled"),
                body: names
                    ? _t(
                          "These orders are still open and were not cancelled: %s.\nPlease check them and try again.",
                          names,
                      )
                    : _t(
                          "Some orders could not be cancelled. Please check them and try again.",
                      ),
            });
            return false;
        }

        return true;
    }
    /**
     * @param {*} order
     * @returns {boolean}
     */
    async _onBeforeRemoveOrder(order) {
        return true;
    }

    /**
     * @param {Array} domain
     * @param {number} offset
     * @param {number} limit
     * @returns {Promise<Object>}
     */
    async loadNewProducts(domain, offset = 0, limit = 0) {
        const endLoad = log.perf("loadNewProducts");
        log.pipeline("loadNewProducts", () => ({ domain, offset, limit }));
        const result = await this.data.callRelated(
            "product.template",
            "load_product_from_pos",
            [odoo.pos_config_id, domain, offset, limit],
            {},
            false,
        );
        this.productAttributesExclusion = this.computeProductAttributesExclusion(
            result["product.template.attribute.exclusion"],
        );
        endLoad({
            templates: result?.["product.template"]?.length,
            products: result?.["product.product"]?.length,
        });
        return result;
    }

    async handleUrlParams() {
        const orderPathUuid = this.router.state.params.orderUuid;
        if (!orderPathUuid) {
            return;
        }
        const order = this.models["pos.order"].find(
            (order) => order.uuid === orderPathUuid,
        );
        log.logic("handleUrlParams", () => ({
            orderUuid: orderPathUuid,
            inMemory: Boolean(order),
        }));
        if (order) {
            this.setOrder(order);
            return;
        }
        await this.data.loadServerOrders([["uuid", "=", orderPathUuid]]);
        const loadedOrder = this.models["pos.order"].find(
            (order) => order.uuid === orderPathUuid,
        );
        log.logic("handleUrlParams: server lookup", () => ({
            orderUuid: orderPathUuid,
            found: Boolean(loadedOrder),
        }));
        if (loadedOrder) {
            this.setOrder(loadedOrder);
        } else {
            const next = this.getDefaultPage();
            this.router.navigate(next.page, next.params);
        }
    }

    async afterProcessServerData() {
        const pendingOrderIds = this.models["pos.order"]
            .filter(
                (order) =>
                    order.isUnsyncedPaid || (order.isDirty() && !order.finalized),
            )
            .map((order) => order.id);

        log.pipeline("afterProcessServerData: pending", () => ({
            pending: pendingOrderIds,
        }));
        if (pendingOrderIds.length > 0) {
            this.addPendingOrder(pendingOrderIds);
        }

        const openOrders = this.data.models["pos.order"].filter(
            (order) => !order.finalized,
        );
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
        log.logic("afterProcessServerData: selected order", () => ({
            restaurant: this.config.module_pos_restaurant,
            fromUrl: this.router.state.params.orderUuid,
            openOrders: openOrders.length,
            selected: this.selectedOrderUuid,
        }));

        const endRead = log.perf("afterProcessServerData: readDataFromServer");
        await this.deviceSync.readDataFromServer();
        endRead();

        log.logic("afterProcessServerData: epson printer", () => ({
            otherDevices: this.config.other_devices,
            ip: this.config.epson_printer_ip,
        }));
        if (this.config.other_devices && this.config.epson_printer_ip) {
            this.hardwareProxy.printer = new EpsonPrinter({
                ip: this.config.epson_printer_ip,
            });
        }
    }

    get productViewMode() {
        const viewMode =
            this.productListView && this.ui.isSmall ? this.productListView : "grid";
        if (viewMode === "grid") {
            return "flex-column";
        } else {
            return "flex-row-reverse justify-content-between m-1";
        }
    }
    async onProductInfoClick(productTemplate, productProduct = false) {
        const info = await this.getProductInfo(productTemplate, 1, 0, productProduct);
        this.dialog.add(ProductInfoPopup, {
            info: info,
            productTemplate: productTemplate,
        });
    }
    async openConfigurator(pTemplate, opts = {}) {
        log.pipeline("openConfigurator", () => ({
            template: pTemplate.id,
            code: opts.code?.base_code,
            presetVariant: opts.presetVariant?.id,
            line: opts.line?.uuid,
        }));
        const attrById = this.models["product.attribute"].getAllBy("id");
        const attributeLines = pTemplate.attribute_line_ids.filter(
            (attr) => attr.attribute_id?.id in attrById,
        );
        let attributeLinesValues = attributeLines.map(
            (attr) => attr.product_template_value_ids,
        );
        if (opts.code || opts.presetVariant) {
            let product;
            if (opts.code) {
                product = this.models["product.product"].getBy(
                    "barcode",
                    opts.code.base_code,
                );
                if (!product && opts.product) {
                    product = opts.product;
                }
            } else {
                product = opts.presetVariant;
            }

            const attrValueIds = new Set(
                product?.product_template_attribute_value_ids?.map((v) => v.id) || [],
            );

            attributeLinesValues = attributeLinesValues.map((values) =>
                values[0].attribute_id.create_variant === "no_variant"
                    ? values
                    : values.filter((value) => attrValueIds.has(value.id)),
            );
        }
        const needsPopup = attributeLinesValues.some(
            (values) => values.length > 1 || values[0].is_custom,
        );
        log.logic("openConfigurator: popup", () => ({
            template: pTemplate.id,
            attributeLines: attributeLinesValues.map((values) => values.length),
            needsPopup,
        }));
        if (needsPopup) {
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
        if (!currentOrder) {
            return;
        }
        const tipProduct = this.config.tip_product_id;
        let line = currentOrder.lines.find(
            (line) => line.product_id.id === tipProduct.id,
        );
        log.logic("setTip", () => ({
            order: currentOrder.uuid,
            tip,
            existingLine: line?.uuid,
        }));

        if (line) {
            line.setUnitPrice(tip);
        } else {
            line = await this.addLineToCurrentOrder(
                {
                    product_id: tipProduct,
                    price_unit: tip,
                    product_tmpl_id: tipProduct.product_tmpl_id,
                },
                {},
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
        log.logic("addLineToOrder", () => ({
            order: order.uuid,
            product: vals.product_id?.id,
            qty: vals.qty,
            configure,
        }));
        order.assertEditable();

        this.numberBuffer?.capture();

        const options = {
            ...opts,
        };

        if ("price_unit" in vals) {
            merge = false;
        }

        if (typeof vals.product_tmpl_id == "number") {
            vals.product_tmpl_id = this.data.models["product.template"].get(
                vals.product_tmpl_id,
            );
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

        if (order.isSaleDisallowed(values, options) && !opts.force) {
            log.logic("addLineToOrder: sale disallowed", () => ({
                order: order.uuid,
                product: values.product_id?.id,
            }));
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
            configure,
        );
        log.logic("addLineToOrder: configurable", () => ({
            order: order.uuid,
            template: productTemplate.id,
            keepGoing,
        }));
        if (keepGoing === false) {
            return;
        }

        keepGoing = await this.handleComboProduct(values, order, configure);
        log.logic("addLineToOrder: combo", () => ({
            order: order.uuid,
            isCombo: values.product_tmpl_id.isCombo(),
            keepGoing,
            comboLines: values.combo_line_ids?.length,
        }));
        if (keepGoing === false) {
            return;
        }

        const code = opts.code;
        let pack_lot_ids = {};
        log.logic("addLineToOrder: tracking", () => ({
            order: order.uuid,
            tracked: values.product_tmpl_id.isTracked(),
            tracking: values.product_id.tracking,
            configure,
            codeType: code?.type,
        }));
        if (values.product_tmpl_id.isTracked() && (configure || code)) {
            const packLotLinesToEdit =
                (!values.product_tmpl_id.isAllowOnlyOneLot() &&
                    order
                        .getOrderlines()
                        .filter((line) => !line.getDiscount())
                        .find((line) => line.product_id.id === values.product_id.id)
                        ?.getPackLotLinesToEdit()) ||
                [];

            if (code && code.type === "lot") {
                const modifiedPackLotLines = Object.fromEntries(
                    packLotLinesToEdit
                        .filter((item) => item.id)
                        .map((item) => [item.id, item.text]),
                );
                const newPackLotLines = [{ lot_name: code.code }];
                pack_lot_ids = { modifiedPackLotLines, newPackLotLines };
            } else {
                pack_lot_ids = await this.editLots(
                    values.product_id,
                    packLotLinesToEdit,
                );
            }

            log.logic("addLineToOrder: lots", () => ({
                order: order.uuid,
                cancelled: !pack_lot_ids,
                newLots: pack_lot_ids?.newPackLotLines?.length,
                modifiedLots: pack_lot_ids?.modifiedPackLotLines
                    ? Object.keys(pack_lot_ids.modifiedPackLotLines).length
                    : 0,
            }));
            if (!pack_lot_ids) {
                return;
            } else {
                const packLotLine = pack_lot_ids.newPackLotLines;
                values.pack_lot_ids = packLotLine.map((lot) => ["create", lot]);
            }
        }

        if (
            values.product_tmpl_id.to_weight &&
            this.config.iface_electronic_scale &&
            configure
        ) {
            log.logic("addLineToOrder: scale", () => ({
                order: order.uuid,
                scaleAvailable: values.product_tmpl_id.isScaleAvailable,
            }));
            if (values.product_tmpl_id.isScaleAvailable) {
                const decimalAccuracy = this.models["decimal.precision"].getBy(
                    "name",
                    PRODUCT_UNIT,
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
                    values.product_id.getTaxDetails({ overridedValues }).total_included,
                );
                const weight = await this.weighProduct();
                log.logic("addLineToOrder: weighed", () => ({
                    order: order.uuid,
                    weight,
                }));
                if (weight) {
                    values.qty = weight;
                } else if (weight !== null) {
                    return;
                }
            } else {
                await values.product_tmpl_id._onScaleNotAvailable();
            }
        }

        this.handlePriceUnit(values, order, vals.price_unit);

        const line = this.data.models["pos.order.line"].create({
            ...values,
            order_id: order,
        });
        log.lifecycle("addLineToOrder: line created", () => ({
            order: order.uuid,
            line: line.uuid,
            product: line.product_id?.id,
            qty: line.qty,
            priceUnit: line.price_unit,
            priceType: line.price_type,
            merge,
        }));
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
                related_lines,
            );
            related_lines
                .filter((line) => line.price_type !== "manual")
                .forEach((line) => line.setUnitPrice(price));
        }

        if (configure) {
            this.numberBuffer.reset();
        }

        if (values.product_id.tracking === "serial") {
            order.getSelectedOrderline().setPackLotLines({
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

    tryMergeOrderline(order, line, merge, selectedOrderline) {
        selectedOrderline = selectedOrderline || order.getSelectedOrderline();
        let to_merge_orderline;
        if (merge !== false) {
            for (const curLine of order.lines) {
                if (curLine.id !== line.id && curLine.canBeMergedWith(line)) {
                    to_merge_orderline = curLine;
                }
            }
        }

        log.logic("tryMergeOrderline", () => ({
            order: order.uuid,
            line: line.uuid,
            merge,
            into: to_merge_orderline?.uuid,
        }));
        if (to_merge_orderline) {
            to_merge_orderline.merge(line);
            line.delete();
            this.selectOrderLine(order, to_merge_orderline);
        } else if (!selectedOrderline) {
            this.selectOrderLine(order, order.getLastOrderline());
        }
    }

    handlePriceUnit(values, order, price_unit) {
        if (!values.product_tmpl_id.isCombo() && price_unit === undefined) {
            values.price_unit = values.product_id.getPrice(
                order.pricelist_id,
                values.qty,
                values.price_extra,
                false,
                values.product_id,
            );
        }
        log.logic("handlePriceUnit", () => ({
            order: order.uuid,
            product: values.product_id?.id,
            given: price_unit,
            pricelist: order.pricelist_id?.id,
            priceUnit: values.price_unit,
        }));
    }

    async handleComboProduct(values, order, configure = true, { line } = {}) {
        if (values.product_tmpl_id.isCombo() && configure) {
            const payload =
                values?.payload && Object.keys(values?.payload).length
                    ? values.payload
                    : await makeAwaitable(this.dialog, ComboConfiguratorPopup, {
                          productTemplate: values.product_tmpl_id,
                          line: line,
                      });

            log.logic("handleComboProduct: payload", () => ({
                order: order.uuid,
                template: values.product_tmpl_id.id,
                fromValues: Boolean(
                    values?.payload && Object.keys(values.payload).length,
                ),
                cancelled: !payload,
            }));
            if (!payload) {
                return false;
            }

            const [childLineConf, comboExtraLines] = payload;
            const comboPrices = computeComboItems(
                values.product_tmpl_id.product_variant_ids[0],
                childLineConf,
                order.pricelist_id,
                this.data.models["decimal.precision"].getAll(),
                this.data.models["product.template.attribute.value"].getAllBy("id"),
                comboExtraLines,
                this.currency,
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
                        comboItem.attribute_custom_values,
                    ).map(([id, cus]) => [
                        "create",
                        {
                            custom_product_template_attribute_value_id:
                                this.data.models[
                                    "product.template.attribute.value"
                                ].get(id),
                            custom_value: cus,
                        },
                    ]),
                },
            ]);
        }

        return true;
    }

    async handleConfigurableProduct(
        values,
        productTemplate,
        opts = {},
        configure = true,
    ) {
        if (productTemplate.isConfigurable() && configure) {
            const payload =
                values?.payload && Object.keys(values?.payload).length
                    ? values.payload
                    : await this.openConfigurator(productTemplate, {
                          ...opts,
                          product: values?.product_id,
                      });

            if (payload) {
                const attributeValues = this.models["product.template.attribute.value"]
                    .readMany(payload.attribute_value_ids)
                    .filter(
                        (value) => value.attribute_id.create_variant !== "no_variant",
                    )
                    .map((value) => value.id);

                let candidate = productTemplate.product_variant_ids.find((variant) => {
                    const attributeIds =
                        variant.product_template_attribute_value_ids.map(
                            (value) => value.id,
                        );
                    return (
                        attributeValues.every((id) => attributeIds.includes(id)) &&
                        attributeValues.length
                    );
                });

                const isDynamic = productTemplate.attribute_line_ids.some(
                    (line) => line.attribute_id.create_variant === "dynamic",
                );
                log.logic("handleConfigurableProduct: variant", () => ({
                    template: productTemplate.id,
                    attributeValues,
                    candidate: candidate?.id,
                    isDynamic,
                    createVariant: !candidate && isDynamic,
                }));

                if (!candidate && isDynamic) {
                    const result = await this.data.callRelated(
                        "product.template",
                        "create_product_variant_from_pos",
                        [
                            productTemplate.id,
                            payload.attribute_value_ids,
                            this.config.id,
                        ],
                    );
                    candidate = result["product.product"][0];
                }

                Object.assign(values, {
                    attribute_value_ids: payload.attribute_value_ids.map((id) => [
                        "link",
                        this.models["product.template.attribute.value"].get(id),
                    ]),
                    custom_attribute_value_ids: Object.entries(
                        payload.attribute_custom_values,
                    ).map(([id, cus]) => [
                        "create",
                        {
                            custom_product_template_attribute_value_id:
                                this.models["product.template.attribute.value"].get(id),
                            custom_value: cus,
                        },
                    ]),
                    price_extra: values.price_extra + payload.price_extra,
                    qty: payload.qty || values.qty,
                    product_id: candidate || productTemplate.product_variant_ids[0],
                });
            } else {
                log.logic("handleConfigurableProduct: cancelled", () => ({
                    template: productTemplate.id,
                }));
                return false;
            }
        } else if (values.product_id.product_template_variant_value_ids.length > 0) {
            const priceExtra = values.product_id.product_template_variant_value_ids
                .filter((attr) => attr.attribute_id.create_variant !== "always")
                .reduce((acc, attr) => acc + attr.price_extra, 0);
            log.logic("handleConfigurableProduct: variant price extra", () => ({
                product: values.product_id.id,
                priceExtra,
            }));

            values.price_extra += priceExtra;
            if (!values.attribute_value_ids) {
                values.attribute_value_ids = [];
            }
            values.attribute_value_ids = values.attribute_value_ids.concat(
                values.product_id.product_template_attribute_value_ids.map((attr) => [
                    "link",
                    attr,
                ]),
            );
        }
    }

    createPrinter(config) {
        log.lifecycle("createPrinter", () => ({
            type: config.printer_type,
            ip: config.epson_printer_ip,
            proxy: config.proxy_ip,
        }));
        if (config.printer_type === "epson_epos") {
            return new EpsonPrinter({ ip: config.epson_printer_ip });
        }
        const url = deduceUrl(config.proxy_ip || "");
        return new HWPrinter({ url });
    }
    async _loadFonts() {
        return new Promise(function (resolve, reject) {
            waitForWebfonts(["Lato", "Inconsolata"], function () {
                resolve();
            });
            setTimeout(resolve, 5000);
        });
    }

    setSelectedCategory(categoryId) {
        log.logic("setSelectedCategory", () => ({
            categoryId,
            current: this.selectedCategory?.id,
            toggleUp: categoryId === this.selectedCategory?.id,
        }));
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

    removeOrder(order, removeFromServer = true) {
        log.lifecycle("removeOrder", () => ({
            order: order.uuid,
            id: order.id,
            removeFromServer,
            synced: order.isSynced,
        }));
        if (this.config.isShareable || removeFromServer) {
            if (order.isSynced && !order.finalized) {
                log.logic("removeOrder: queue server delete", () => ({
                    order: order.uuid,
                    id: order.id,
                }));
                this.addPendingOrder([order.id], true);
                this.syncAllOrdersDebounced();
            }
        }

        if (!order.isSynced && order.finalized) {
            log.logic("removeOrder: keep unsynced finalized", () => ({
                order: order.uuid,
            }));
            this.addPendingOrder([order.id]);
            return;
        }

        this.device.saveUnusedNumber([order]);
        return this.data.localDeleteCascade(order);
    }

    /**
     * @returns {name: string, id: int, role: string}
     */
    getCashier() {
        return getCashier(this);
    }
    getCashierUserId() {
        return getCashierUserId(this);
    }
    cashierHasPriceControlRights() {
        return cashierHasPriceControlRights(this);
    }

    get cashierIsMinimal() {
        return this.cashier?._role === "minimal";
    }

    get showCashMoveButton() {
        return Boolean(this.config.cash_control && this.config._has_cash_move_perm);
    }
    createNewOrder(data = {}) {
        log.lifecycle("createNewOrder", () => ({
            keys: Object.keys(data),
            orders: this.models["pos.order"].length,
        }));
        const fiscalPosition = this.models["account.fiscal.position"].find(
            (fp) => fp.id === this.config.default_fiscal_position_id?.id,
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

        if (!order.partner_id) {
            order.partner_id = this.getDefaultPartnerId();
        }
        log.lifecycle("createNewOrder: created", () => ({
            order: order.uuid,
            id: order.id,
            reference: order.pos_reference,
            fiscalPosition: fiscalPosition?.id,
            pricelist: order.pricelist_id?.id,
            partner: order.partner_id?.id,
            applyDefaultPreset: this.config.use_presets && !data["preset_id"],
        }));

        if (this.config.use_presets && !data["preset_id"]) {
            Promise.resolve(
                this.selectPreset(this.config.default_preset_id, order),
            ).catch((error) => {
                logPosMessage(
                    "Store",
                    "createNewOrder",
                    "Could not apply the default preset to the new order",
                    CONSOLE_COLOR,
                    [error],
                );
            });
        }

        return order;
    }
    addNewOrder(data = {}) {
        log.lifecycle("addNewOrder", () => ({
            previous: this.selectedOrderUuid,
            keys: Object.keys(data),
        }));
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
        order.tracking_number =
            deviceIdentifier + `${parseInt(number) % 1000}`.padStart(3, "0");
        log.logic("setNextOrderRefs", () => ({
            order: order.uuid,
            device: deviceIdentifier,
            number,
            reference: posReference,
            tracking: order.tracking_number,
        }));
    }

    selectNextOrder() {
        const orders = this.models["pos.order"].filter((order) => !order.finalized);
        log.logic("selectNextOrder", () => ({
            open: orders.length,
            next: orders[0]?.uuid,
        }));
        if (orders.length > 0) {
            this.selectedOrderUuid = orders[0].uuid;
        } else {
            return this.addNewOrder();
        }
    }
    getOrCreateOpenOrder() {
        return (
            this.models["pos.order"].find((o) => o.state === "draft") ||
            this.addNewOrder()
        );
    }
    getDefaultPartnerId() {
        return null;
    }
    getEmptyOrder() {
        const defaultPartnerId = this.getDefaultPartnerId();
        const emptyOrders = this.models["pos.order"].filter(
            (order) =>
                order.isEmpty() &&
                !order.finalized &&
                order.payment_ids.length === 0 &&
                (!order.partner_id || order.partner_id.id === defaultPartnerId) &&
                order.pricelist_id?.id === this.config.pricelist_id?.id &&
                order.fiscal_position_id?.id ===
                    this.config.default_fiscal_position_id?.id,
        );
        log.logic("getEmptyOrder", () => ({
            emptyOrders: emptyOrders.length,
            reuse: emptyOrders[0]?.uuid,
        }));
        if (emptyOrders.length > 0) {
            return emptyOrders[0];
        }
        return this.addNewOrder();
    }

    addPendingOrder(orderIds, remove = false) {
        return addPendingOrder(this, orderIds, remove);
    }

    getPendingOrder() {
        return getPendingOrder(this);
    }

    shouldCreatePendingOrder(order) {
        return shouldCreatePendingOrder(this, order);
    }

    getOrderIdsToDelete() {
        return getOrderIdsToDelete(this);
    }

    removePendingOrder(order) {
        return removePendingOrder(this, order);
    }

    clearPendingOrder() {
        return clearPendingOrder(this);
    }

    getSyncAllOrdersContext(orders, options = {}) {
        return {
            config_id: this.config.id,
            device_identifier: this.device.identifier,
            current_order_uuid: this.getOrder()?.uuid,
            ...(options.context || {}),
        };
    }

    async preSyncAllOrders(orders) {
        for (const order of orders) {
            order.setOrderPrices();
        }
    }

    postSyncAllOrders(orders) {}
    async syncAllOrders(options = {}) {
        return this.pushOrderMutex.exec(() => this._syncAllOrders(options));
    }
    async _syncAllOrders(options = {}) {
        if (this.data.network.offline) {
            log.logic("syncAllOrders: offline", () => ({
                throw: Boolean(options.throw),
            }));
            if (options.throw) {
                throw new ConnectionLostError();
            }

            return new ConnectionLostError();
        }

        const { orderToCreate, orderToUpdate } = this.getPendingOrder();
        const orderIdsToDelete = this.getOrderIdsToDelete();

        const candidates = options.orders || [...orderToCreate, ...orderToUpdate];
        let orders = candidates;
        orders = orders.filter(
            (order) =>
                !this.syncingOrders.has(order.uuid) &&
                (order.isDirty() || options.force),
        );
        log.pipeline("syncAllOrders", () => ({
            toSync: orders.map((o) => o.uuid),
            skipped: candidates.length - orders.length,
            syncing: [...this.syncingOrders],
            toDelete: orderIdsToDelete,
            force: Boolean(options.force),
            explicit: Boolean(options.orders),
        }));
        const endSync = log.perf("syncAllOrders");

        if (orderIdsToDelete.length > 0) {
            try {
                await this.removeOrders([], orderIdsToDelete);
            } catch (error) {
                if (error instanceof ConnectionLostError) {
                    endSync({ connectionLost: true });
                    if (options.throw) {
                        throw error;
                    }
                    return error;
                }
                for (const id of orderIdsToDelete) {
                    this.pendingOrder.delete.delete(id);
                }
                logPosMessage(
                    "Store",
                    "syncAllOrders",
                    "Server rejected the cancellation of deleted orders; dropping the pending cancel ids",
                    CONSOLE_COLOR,
                    [error],
                );
            }
        }

        if (orders.length === 0) {
            endSync({ orders: 0 });
            return;
        }

        let errorOccurred = false;
        let newSession = false;
        const syncedOrders = [];

        for (const order of orders) {
            const context = this.getSyncAllOrdersContext([order], options);
            await this.preSyncAllOrders([order]);
            this.syncingOrders.add(order.uuid);

            const clearActions = [];
            let committed = false;
            const commitClear = () => {
                if (committed) {
                    return;
                }
                committed = true;
                clearActions.forEach((fn) => fn());
            };

            const endOrderSync = log.perf(`syncAllOrders [order:${order.uuid}]`);
            try {
                const serialized = order.serializeForORM({
                    deferClear: true,
                    clearActions,
                });
                log.pipeline("syncAllOrders: sync_from_ui", () => ({
                    order: order.uuid,
                    id: order.id,
                    state: order.state,
                    lines: serialized.lines?.length,
                    payments: serialized.payment_ids?.length,
                    context,
                }));
                const data = await this.data.call(
                    "pos.order",
                    "sync_from_ui",
                    [[serialized]],
                    {
                        context,
                    },
                );
                commitClear();
                const inFlightEdited = [
                    order,
                    ...order.lines,
                    ...(order.payment_ids || []),
                ]
                    .filter((rec) => rec?.isDirty?.() && rec._dirtyFields?.size)
                    .map((rec) => ({
                        rec,
                        values: [...rec._dirtyFields]
                            .filter((fieldName) => {
                                const field = rec.model.fields[fieldName];
                                return (
                                    field &&
                                    !field.relation &&
                                    !field.dummy &&
                                    !["date", "datetime"].includes(field.type) &&
                                    !["id", "uuid"].includes(fieldName)
                                );
                            })
                            .map((fieldName) => [fieldName, rec.raw[fieldName]]),
                    }))
                    .filter(({ values }) => values.length);
                log.logic("syncAllOrders: in-flight edits", () => ({
                    order: order.uuid,
                    edited: inFlightEdited.map(({ rec, values }) => ({
                        record: `${rec.model.name}(${rec.id})`,
                        fields: values.map(([fieldName]) => fieldName),
                    })),
                }));
                const missingRecords = await this.data.missingRecursive(data);
                const newData = this.models.loadConnectedData(missingRecords);
                log.pipeline("syncAllOrders: response loaded", () => ({
                    order: order.uuid,
                    models: Object.fromEntries(
                        Object.entries(newData).map(([model, records]) => [
                            model,
                            records.length,
                        ]),
                    ),
                }));
                for (const { rec, values } of inFlightEdited) {
                    for (const [fieldName, value] of values) {
                        if (rec.raw[fieldName] !== value) {
                            log.logic("syncAllOrders: reapply in-flight edit", () => ({
                                record: `${rec.model.name}(${rec.id})`,
                                field: fieldName,
                            }));
                            rec.update({ [fieldName]: value });
                        }
                    }
                }

                logPosMessage(
                    "Store",
                    "syncAllOrders",
                    `Successfully synced orders (${orders.length})`,
                    CONSOLE_COLOR,
                    [newData],
                );

                for (const line of newData["pos.order.line"] ?? []) {
                    const refundedOrderLine = line.refunded_orderline_id;

                    if (
                        refundedOrderLine &&
                        ["paid", "done"].includes(line.order_id.state)
                    ) {
                        const order = refundedOrderLine.order_id;
                        if (order) {
                            delete order.uiState?.lineToRefund[refundedOrderLine.uuid];
                        }
                    }
                }

                await this.postSyncAllOrders(newData["pos.order"] ?? []);
                this.removePendingOrder(order);
                this.data.localUnsyncedPaidOrderUuids.delete(order.uuid);
                syncedOrders.push(...(newData["pos.order"] ?? []));
                newSession = newSession || data["pos.session"]?.length > 0;
                endOrderSync({ id: order.id, newSession });
            } catch (error) {
                endOrderSync({
                    error: error?.constructor?.name,
                    connectionLost: error instanceof ConnectionLostError,
                });
                if (!(error instanceof ConnectionLostError)) {
                    commitClear();
                }

                if (options.throw) {
                    throw error;
                }

                if (error instanceof ConnectionLostError) {
                    logPosMessage(
                        "Store",
                        "syncAllOrders",
                        "Offline mode active, order will be synced later",
                        CONSOLE_COLOR,
                    );
                } else {
                    errorOccurred = true;
                }
            } finally {
                this.syncingOrders.delete(order.uuid);
            }
        }

        if (errorOccurred) {
            this.deviceSync.readDataFromServer().catch((error) => {
                logPosMessage(
                    "Store",
                    "syncAllOrders",
                    "Could not refresh data after a failed order sync",
                    CONSOLE_COLOR,
                    [error],
                );
            });
        }

        if (newSession) {
            const sessions = this.models["pos.session"].sort((a, b) => a.id - b.id);
            log.lifecycle("syncAllOrders: new session", () => ({
                sessions: sessions.map((s) => s.id),
                current: this.session?.id,
            }));
            if (sessions.length > 1) {
                const sessionToDelete = sessions.slice(0, -1);
                this.models["pos.session"].deleteMany(sessionToDelete);
            }
            this.models["pos.order"]
                .getAll()
                .filter((order) => order.state === "draft")
                .forEach((order) => (order.session_id = this.session));
        }
        endSync({
            orders: orders.length,
            synced: syncedOrders.length,
            errorOccurred,
            newSession,
        });

        return syncedOrders;
    }

    pushSingleOrder(order) {
        return this.syncAllOrders({ orders: [order] });
    }

    async pay() {
        this.numberBuffer.capture();
        const currentOrder = this.getOrder();
        log.logic("pay", () => ({
            order: currentOrder?.uuid,
            canPay: currentOrder?.canPay(),
            lines: currentOrder?.lines?.length,
        }));

        if (!currentOrder?.canPay()) {
            return;
        }

        const missingLots =
            currentOrder.lines.some(
                (line) =>
                    line.getProduct().tracking !== "none" && !line.hasValidProductLot(),
            ) &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots);
        log.logic("pay: lots", () => ({ order: currentOrder.uuid, missingLots }));
        if (missingLots) {
            const confirmed = await ask(this.env.services.dialog, {
                title: _t("Some Serial/Lot Numbers are missing"),
                body: _t(
                    "You are trying to sell products with serial/lot numbers, but some of them are not set.\nWould you like to proceed anyway?",
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
        const config_domain = new Domain([
            [
                "config_id",
                "in",
                [...this.config.raw.trusted_config_ids, this.config.id],
            ],
        ]);
        const endLoad = log.perf("getServerOrders");
        log.pipeline("getServerOrders", () => ({
            configs: [...this.config.raw.trusted_config_ids, this.config.id],
            domain: this.getServerOrdersDomain().toList(),
        }));
        const orders = await this.data.loadServerOrders(
            Domain.and([config_domain, this.getServerOrdersDomain()]).toList(),
        );
        endLoad({ orders: orders?.length });
        return orders;
    }
    getServerOrdersDomain() {
        return new Domain([["state", "=", "draft"]]);
    }
    async getProductInfo(
        productTemplate,
        quantity,
        priceExtra = 0,
        productProduct = false,
    ) {
        const order = this.getOrder();
        const endInfo = log.perf("getProductInfo");
        const productInfo = await this.data.call(
            "product.template",
            "get_product_info_pos",
            [
                [productTemplate?.id],
                productTemplate.getPrice(
                    order.pricelist_id,
                    quantity,
                    priceExtra,
                    false,
                ),
                quantity,
                this.config.id,
                productProduct?.id,
            ],
        );

        const productTaxDetails = productTemplate.getTaxDetails();
        const priceWithoutTax = productTaxDetails.total_excluded;
        const margin = priceWithoutTax - productTemplate.standard_price;
        const orderPriceWithoutTax = order.priceExcl;
        const orderCost = order.getTotalCost();
        const orderMargin = orderPriceWithoutTax - orderCost;
        const orderTaxTotalCurrency = this.env.utils.formatCurrency(
            order.prices.taxDetails.order_sign *
                order.prices.taxDetails.tax_amount_currency,
        );
        const orderPriceWithTaxCurrency = this.env.utils.formatCurrency(
            order.prices.taxDetails.order_sign *
                order.prices.taxDetails.total_amount_currency,
        );
        const taxAmount = this.env.utils.formatCurrency(
            productTaxDetails.taxes_data.reduce(
                (sum, d) => sum + d.tax_amount_currency,
                0,
            ),
        );
        const taxName = productTemplate.taxes_id.map((t) => t.name)?.join(", ");

        const costCurrency = this.env.utils.formatCurrency(
            productTemplate.standard_price,
        );
        const marginCurrency = this.env.utils.formatCurrency(margin);
        const marginPercent = priceWithoutTax
            ? Math.round((margin / priceWithoutTax) * 10000) / 100
            : 0;
        const orderPriceWithoutTaxCurrency =
            this.env.utils.formatCurrency(orderPriceWithoutTax);
        const orderCostCurrency = this.env.utils.formatCurrency(orderCost);
        const orderMarginCurrency = this.env.utils.formatCurrency(orderMargin);
        const orderMarginPercent = orderPriceWithoutTax
            ? Math.round((orderMargin / orderPriceWithoutTax) * 10000) / 100
            : 0;
        endInfo({ template: productTemplate?.id, product: productProduct?.id });
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
        const endInfo = log.perf("getClosePosInfo");
        const info = await this.data.call("pos.session", "get_closing_control_data", [
            [this.session.id],
        ]);
        endInfo({ session: this.session.id, keys: info ? Object.keys(info) : [] });
        return info;
    }
    getOrder() {
        if (!this.selectedOrderUuid) {
            return undefined;
        }

        return this.models["pos.order"].getBy("uuid", this.selectedOrderUuid);
    }
    get selectedOrder() {
        return this.getOrder();
    }

    setOrder(order) {
        log.lifecycle("setOrder", () => ({
            from: this.selectedOrderUuid,
            to: order?.uuid,
        }));
        if (this.getOrder()) {
            this.getOrder().updateSavedQuantity();
        }
        this.selectedOrderUuid = order?.uuid;
    }

    getOpenOrders() {
        return this.models["pos.order"].filter((o) => !o.finalized);
    }

    async pushOrdersWithClosingPopup(opts = {}) {
        log.pipeline("pushOrdersWithClosingPopup", () => ({
            pending: this.getPendingOrder(),
        }));
        try {
            const result = await this.syncAllOrders(opts);
            if (result instanceof ConnectionLostError) {
                throw result;
            }
            return true;
        } catch (error) {
            log.logic("pushOrdersWithClosingPopup: failed", () => ({
                connectionLost: error instanceof ConnectionLostError,
                error: error?.message,
            }));
            logPosMessage(
                "Store",
                "pushOrdersWithClosingPopup",
                "Some orders could not be submitted to the server",
                CONSOLE_COLOR,
                [error],
            );
            const reason = !(error instanceof ConnectionLostError)
                ? _t(
                      "Some orders could not be submitted to " +
                          "the server due to configuration errors. " +
                          "You can exit the Point of Sale, but do " +
                          "not close the session before the issue " +
                          "has been resolved.",
                  )
                : _t(
                      "Some orders could not be submitted to " +
                          "the server due to internet connection issues. " +
                          "You can exit the Point of Sale, but do " +
                          "not close the session before the issue " +
                          "has been resolved.",
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
                    paymentLine.payment_method_id.use_payment_terminal ===
                        terminalName &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "retry",
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
        const ProductUnit = this.models["decimal.precision"].getBy(
            "name",
            PRODUCT_UNIT,
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
        return switchPane(this);
    }
    switchPaneTicketScreen() {
        return switchPaneTicketScreen(this);
    }
    async logEmployeeMessage(action, message) {
        log.pipeline("logEmployeeMessage", () => ({
            action,
            session: this.session.id,
        }));
        await this.data.call(
            "pos.session",
            "log_partner_message",
            [this.session.id, this.user.partner_id.id, action, message],
            {},
            true,
        );
    }
    async printReceipt({
        basic = false,
        order = this.getOrder(),
        printBillActionTriggered = false,
    } = {}) {
        const endPrint = log.perf("printReceipt");
        log.pipeline("printReceipt", () => ({
            order: order?.uuid,
            basic,
            printBillActionTriggered,
            nbPrint: order?.nb_print,
        }));
        const result = await this.printer.print(
            OrderReceipt,
            {
                order,
                basic_receipt: basic,
            },
            this.printOptions,
        );
        if (!printBillActionTriggered) {
            if (result) {
                await this.incrementReceiptPrintCount(order);
            }
        } else if (!order.nb_print) {
            order.nb_print = 0;
        }
        if (result?.warningCode) {
            this.displayPrinterWarning(result, _t("Receipt Printer"));
        }
        endPrint({
            order: order?.uuid,
            printed: Boolean(result),
            warningCode: result?.warningCode,
            nbPrint: order?.nb_print,
        });
        return result;
    }
    /**
     * @param {import("@point_of_sale/app/models/pos_order").PosOrder} order
     * @returns {Promise<number>}
     */
    async incrementReceiptPrintCount(order) {
        return this.printCountMutex.exec(async () => {
            const count = (order.nb_print || 0) + 1;
            log.logic("incrementReceiptPrintCount", () => ({
                order: order.uuid,
                count,
                synced: order.isSynced,
                dirty: order.isDirty(),
            }));
            if (!order.isSynced) {
                order.nb_print = count;
                return count;
            }
            const wasDirty = order.isDirty();
            const records = await this.data.write("pos.order", [order.id], {
                nb_print: count,
            });
            if (!wasDirty) {
                order._markClean();
            }
            const written = records?.find?.((record) => record.id === order.id);
            return written?.nb_print ?? count;
        });
    }
    get printOptions() {
        return { webPrintFallback: true };
    }
    getOrderChanges(order = this.getOrder()) {
        return getOrderChanges(order, this.config.preparationCategories);
    }
    async checkPreparationStateAndSentOrderInPreparation(order, opts = {}) {
        log.pipeline("checkPreparationState", () => ({
            order: order.uuid,
            synced: order.isSynced,
            opts,
        }));
        if (!order.isSynced) {
            return this.sendOrderInPreparation(order, opts);
        }

        let data;
        try {
            data = await this.data.call("pos.order", "get_preparation_change", [
                order.id,
            ]);
        } catch (error) {
            log.logic("checkPreparationState: fetch failed", () => ({
                order: order.uuid,
                connectionLost: error instanceof ConnectionLostError,
            }));
            if (error instanceof ConnectionLostError) {
                return this.sendOrderInPreparation(order, opts);
            }
            throw error;
        }
        const rawchange = data.last_order_preparation_change || "{}";
        const lastChanges = JSON.parse(rawchange);
        const lastServerDate = DateTime.fromSQL(
            lastChanges.metadata?.serverDate,
        ).toUTC();
        const lastLocalDate = DateTime.fromSQL(
            order.last_order_preparation_change?.metadata?.serverDate,
        ).toUTC();

        const outdated =
            lastServerDate.isValid && lastServerDate.ts !== lastLocalDate.ts;
        log.logic("checkPreparationState: outdated", () => ({
            order: order.uuid,
            outdated,
            server: lastServerDate.toISO(),
            local: lastLocalDate.toISO(),
        }));
        if (outdated) {
            this.dialog.add(AlertDialog, {
                title: _t("Order Outdated"),
                body: _t(
                    "The order has been modified on another device. If you have modified existing " +
                        "order lines, check that your changes have not been overwritten.\n\n" +
                        "The order will be sent to the server with the last changes made on this device.",
                ),
            });

            order.last_order_preparation_change = lastChanges;
            await this.syncAllOrders({ orders: [order] });
            return;
        }

        return this.sendOrderInPreparation(order, opts);
    }
    async sendOrderInPreparation(order, opts = {}) {
        let isPrinted = false;
        let changeSetFailed = false;
        const endPrep = log.perf("sendOrderInPreparation");
        log.pipeline("sendOrderInPreparation", () => ({
            order: order.uuid,
            opts,
            printers: this.config.printerCategories.size,
        }));

        if (this.config.printerCategories.size && !opts.byPassPrint) {
            try {
                let reprint = false;
                let changeToRecord = null;
                let orderChange = changesToOrder(
                    order,
                    this.config.printerCategories,
                    opts.cancelled,
                );

                const hasChanges =
                    orderChange.new.length ||
                    orderChange.cancelled.length ||
                    orderChange.noteUpdate.length ||
                    orderChange.internal_note ||
                    orderChange.general_customer_note;

                let shouldPrint = true;
                if (!hasChanges) {
                    if (opts.explicitReprint && order.uiState.lastPrints?.length) {
                        orderChange = [order.uiState.lastPrints.at(-1)];
                        reprint = true;
                    } else {
                        shouldPrint = false;
                    }
                } else {
                    changeToRecord = orderChange;
                    orderChange = [orderChange];
                }

                if (reprint && opts.orderDone) {
                    shouldPrint = false;
                }
                log.logic("sendOrderInPreparation: changes", () => ({
                    order: order.uuid,
                    hasChanges: Boolean(hasChanges),
                    new: changeToRecord?.new?.length ?? 0,
                    cancelled: changeToRecord?.cancelled?.length ?? 0,
                    noteUpdate: changeToRecord?.noteUpdate?.length ?? 0,
                    reprint,
                    shouldPrint,
                }));

                if (shouldPrint) {
                    isPrinted = await this.printChanges(order, orderChange, reprint);
                    if (
                        changeToRecord &&
                        (isPrinted || !this.unwatched.printers?.length)
                    ) {
                        this.recordLastPrint(order, changeToRecord);
                    }
                }
            } catch (e) {
                changeSetFailed = true;
                logPosMessage(
                    "Store",
                    "sendOrderInPreparation",
                    "Failed in printing the changes in the order",
                    CONSOLE_COLOR,
                    [e],
                );
            }
        }
        if (!changeSetFailed) {
            order.updateLastOrderChange();
        }
        if (isPrinted && !this.models["pos.prep.display"]?.length) {
            await this.syncAllOrders({ orders: [order] });
        }
        endPrep({ order: order.uuid, isPrinted, changeSetFailed });
    }
    /**
     * @param {import("@point_of_sale/app/models/pos_order").PosOrder} order
     * @param {Object} change
     */
    recordLastPrint(order, change) {
        const history = order.uiState.lastPrints;
        history.push(change);
        if (history.length > MAX_LAST_PRINTS) {
            history.splice(0, history.length - MAX_LAST_PRINTS);
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
        return getStrNotes(note);
    }

    getOrderData(order, reprint) {
        return getOrderData(this, order, reprint);
    }

    generateOrderChange(order, orderChange, categories, reprint = false) {
        return generateOrderChange(this, order, orderChange, categories, reprint);
    }

    async generateReceiptsDataToPrint(orderData, changes, orderChange) {
        return generateReceiptsDataToPrint(this, orderData, changes, orderChange);
    }

    async printChanges(
        order,
        orderChange,
        reprint = false,
        printers = this.unwatched.printers,
    ) {
        let isPrinted = false;
        const unsuccessfulPrints = [];
        const retryPrinters = new Set();
        const endPrint = log.perf("printChanges");
        log.pipeline("printChanges", () => ({
            order: order.uuid,
            changes: orderChange.length,
            reprint,
            printers: [...printers].map((p) => p.config?.name),
        }));

        for (const printer of printers) {
            for (const change of orderChange) {
                const { orderData, changes } = this.generateOrderChange(
                    order,
                    change,
                    printer.config.product_categories_ids,
                    reprint,
                );
                const receiptsData = await this.generateReceiptsDataToPrint(
                    orderData,
                    changes,
                    change,
                );
                log.pipeline("printChanges: receipts", () => ({
                    order: order.uuid,
                    printer: printer.config?.name,
                    receipts: receiptsData.length,
                }));
                let result;
                for (const data of receiptsData) {
                    result = await this.printOrderChanges(data, printer);
                    log.logic("printChanges: result", () => ({
                        order: order.uuid,
                        printer: printer.config?.name,
                        successful: result.successful,
                        warningCode: result.warningCode,
                    }));
                    if (result.successful) {
                        isPrinted = true;
                    }

                    if (!result.successful) {
                        retryPrinters.add(printer);
                        unsuccessfulPrints.push(
                            printer.config.name + ": " + result.message.body,
                        );
                    } else if (result.warningCode) {
                        this.displayPrinterWarning(result, printer.config.name);
                    }
                }
            }
        }

        endPrint({
            order: order.uuid,
            isPrinted,
            failed: unsuccessfulPrints.length,
            retryPrinters: retryPrinters.size,
        });
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
        return prepareReceiptGroupedData(data);
    }

    async printOrderChanges(data, printer) {
        const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
            data: data,
        });
        return await printer.printReceipt(receipt);
    }

    filterChangeByCategories(categories, currentOrderChange) {
        return filterChangeByCategories(this, categories, currentOrderChange);
    }

    async connectToProxy() {
        const endConnect = log.perf("connectToProxy");
        log.lifecycle("connectToProxy", () => ({
            proxyIp: this.config.proxy_ip,
            scanViaProxy: this.config.iface_scan_via_proxy,
        }));
        this.barcodeReader?.disconnectFromProxy();
        this.loadingSkipButtonIsShown = true;
        await this.hardwareProxy.autoConnect({ force_ip: this.config.proxy_ip });
        if (this.config.iface_scan_via_proxy) {
            this.barcodeReader?.connectToProxy();
        }
        endConnect({ host: this.hardwareProxy.host });
    }
    /**
     * @param {import("@point_of_sale/app/models/res_partner").ResPartner?} partner
     */
    editPartnerContext(partner) {
        return {};
    }
    /**
     * @param {import("@point_of_sale/app/models/res_partner").ResPartner?} partner
     */
    async editPartner(partner) {
        log.pipeline("editPartner", () => ({ partner: partner?.id }));
        const record = await makeActionAwaitable(
            this.action,
            "point_of_sale.res_partner_action_edit_pos",
            {
                props: { resId: partner?.id },
                additionalContext: this.editPartnerContext(partner),
            },
        );
        if (!record) {
            log.lifecycle("editPartner: canceled");
            return;
        }
        const newPartner = await this.data.read("res.partner", record.config.resIds);
        log.lifecycle("editPartner: saved", () => ({
            partner: newPartner[0]?.id,
            resIds: record.config.resIds,
        }));
        return newPartner[0];
    }
    /**
     * @param {import("@point_of_sale/app/models/product_product").ProductProduct?} product
     */
    async editProduct(product) {
        const orderContainsProduct = product && this.orderContainsProduct(product);
        log.pipeline("editProduct", () => ({
            product: product?.id,
            orderContainsProduct,
        }));
        this.action.doAction(
            product
                ? "point_of_sale.product_template_action_edit_pos"
                : "point_of_sale.product_template_action_add_pos",
            {
                props: {
                    resId: product?.id,
                    onSave: (record) => {
                        log.lifecycle("editProduct: saved", () => ({
                            template: record.evalContext.id,
                        }));
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
            },
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

        log.logic("loadSampleData", () => ({ isPosManager, isAdmin }));
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
                log.lifecycle("orderDetails: saved", () => ({
                    id: record.evalContext.id,
                }));
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
        log.lifecycle("closePos", () => ({ session: this.session?.id }));
        webRouter.dropEphemerals();
        this._resetConnectedCashier();
        if (!this.session) {
            this.redirectToBackend();
            return;
        }

        log.logic("closePos", () => ({
            session: this.session.id,
            state: this.session.state,
            removeOpeningControl: this.session.state === "opening_control",
        }));
        if (this.session.state === "opening_control") {
            const data = await this.data.call(
                "pos.session",
                "remove_opening_control_session",
                [this.session.id],
            );
            log.lifecycle("closePos: opening control removed", () => ({
                session: this.session.id,
                status: data.status,
            }));

            if (data.status === "success") {
                this.redirectToBackend();
            } else {
                this.notification.add(
                    _t("The opening-control session could not be deleted."),
                    { type: "danger" },
                );
            }
            return;
        }

        const syncSuccess = await this.pushOrdersWithClosingPopup();
        log.lifecycle("closePos: sync", () => ({
            session: this.session.id,
            syncSuccess,
        }));
        if (syncSuccess) {
            this.redirectToBackend();
        }
    }
    async selectPricelist(pricelist) {
        log.logic("selectPricelist", () => ({
            order: this.getOrder()?.uuid,
            pricelist: pricelist?.id,
        }));
        await this.getOrder().setPricelist(pricelist);
    }
    async openPresetTiming(order = this.getOrder()) {
        const data = await makeAwaitable(this.dialog, PresetSlotsPopup);
        log.logic("openPresetTiming", () => ({
            order: order?.uuid,
            preset: data?.presetId,
            slot: data?.slot?.datetime?.toISO?.(),
            changePreset: data && order.preset_id?.id !== data.presetId,
        }));
        if (data) {
            if (order.preset_id?.id !== data.presetId) {
                await this.selectPreset(
                    this.models["pos.preset"].get(data.presetId),
                    order,
                );
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
        log.logic("selectPreset", () => ({ preset: preset?.id, order: order?.uuid }));
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
            log.logic("selectPreset: chosen", () => ({
                order: order?.uuid,
                preset: preset.id,
                needsPartner: preset.needsPartner,
                identification: preset.identification,
                useTiming: preset.use_timing,
            }));
            if (preset.needsPartner) {
                const partner = order.partner_id || (await this.selectPartner(order));
                if (!partner) {
                    return;
                }
                if (!(partner.street || partner.street2)) {
                    this.notification.add(_t("Customer address is required"), {
                        type: "warning",
                    });
                    await this.editPartner(partner);
                    if (!(partner.street || partner.street2)) {
                        return;
                    }
                }
            }

            order.setPreset(preset);

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
        const endSync = log.perf("syncPresetSlotAvaibility");
        const requests = (this.unwatched.presetSlotRequests ??= new WeakMap());
        // Different component observers can wrap the same record in different proxies.
        const record = toRaw(preset);
        const request = {};
        requests.set(record, request);
        let outcome = "superseded";
        try {
            const result = await this.data.call("pos.preset", "get_available_slots", [
                preset.id,
            ]);
            if (requests.get(record) !== request) {
                return;
            }
            preset.computeAvailabilities(this.orderUsageUTCtoLocal(result.usage_utc));
            outcome = "updated";
        } catch (error) {
            if (requests.get(record) !== request) {
                return;
            }
            outcome = "failed";
            log.logic("preset refresh: retaining known bookings", () => ({
                preset: preset.id,
                error,
            }));
            preset.computeAvailabilities(preset.uiState.serverUsage);
        } finally {
            if (requests.get(record) === request) {
                requests.delete(record);
            }
            endSync({ preset: preset.id, outcome });
        }
    }
    setPartnerToCurrentOrder(partner) {
        this.getOrder()?.setPartner(partner);
    }
    async selectPartner(currentOrder = this.getOrder()) {
        log.logic("selectPartner", () => ({
            order: currentOrder?.uuid,
            partner: currentOrder?.partner_id?.id,
        }));
        if (!currentOrder) {
            return false;
        }
        const currentPartner = currentOrder.getPartner();
        if (currentPartner && currentOrder.getHasRefundLines()) {
            log.logic("selectPartner: locked by refund lines", () => ({
                order: currentOrder.uuid,
                partner: currentPartner.id,
            }));
            this.dialog.add(AlertDialog, {
                title: _t("Can't change customer"),
                body: _t(
                    "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer.",
                    currentPartner.name,
                ),
            });
            return currentPartner;
        }
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: currentPartner,
        });
        log.logic("selectPartner: chosen", () => ({
            order: currentOrder.uuid,
            from: currentPartner?.id,
            to: payload?.id,
        }));

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
        log.logic("editLotsRefund", () => ({
            line: line.uuid,
            product: product.id,
            current: packLotLinesToEdit.length,
            alreadyRefunded: alreadyRefundedLots.length,
            options: options.length,
        }));
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
        let canCreateLots =
            this.pickingType.use_create_lots || !this.pickingType.use_existing_lots;

        let existingLots = [];
        const endLots = log.perf("editLots: get_existing_lots");
        try {
            existingLots = await this.data.call("pos.order.line", "get_existing_lots", [
                this.company.id,
                this.config.id,
                product.id,
            ]);
            endLots({ product: product.id, existing: existingLots?.length });
            if (!canCreateLots && (!existingLots || existingLots.length === 0)) {
                this.dialog.add(AlertDialog, {
                    title: _t("No existing serial/lot number"),
                    body: _t(
                        "There is no serial/lot number for the selected product, and their creation is not allowed from the Point of Sale app.",
                    ),
                });
                return null;
            }
        } catch (ex) {
            endLots({ product: product.id, failed: true });
            logPosMessage(
                "Store",
                "editLots",
                "Collecting existing lots failed",
                CONSOLE_COLOR,
                [ex],
            );
            const confirmed = await ask(this.dialog, {
                title: _t("Server communication problem"),
                body: _t(
                    "The existing serial/lot numbers could not be retrieved. \nContinue without checking the validity of serial/lot numbers ?",
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
                    lot.pos_order_line_id?.order_id?.state === "draft",
            )
            .reduce((acc, lot) => {
                if (!acc[lot.lot_name]) {
                    acc[lot.lot_name] = { total: 0, currentOrderCount: 0 };
                }
                acc[lot.lot_name].total += lot.pos_order_line_id?.qty || 0;

                if (lot.pos_order_line_id?.order_id?.id === this.selectedOrder.id) {
                    acc[lot.lot_name].currentOrderCount +=
                        lot.pos_order_line_id?.qty || 0;
                }
                return acc;
            }, {});

        existingLots = existingLots.filter(
            (lot) => lot.product_qty > (usedLotsQty[lot.name]?.total || 0),
        );

        const isLotNameUsed = (itemValue) => {
            const totalQty =
                existingLots.find((lt) => lt.name === itemValue)?.product_qty || 0;
            const usedQty = usedLotsQty[itemValue]
                ? usedLotsQty[itemValue].total -
                  usedLotsQty[itemValue].currentOrderCount
                : 0;
            return usedQty ? usedQty >= totalQty : false;
        };

        const existingLotsName = existingLots.map((l) => l.name);
        log.logic("editLots", () => ({
            product: product.id,
            tracking: product.tracking,
            isAllowOnlyOneLot,
            canCreateLots,
            available: existingLots.length,
            used: Object.keys(usedLotsQty).length,
            toEdit: packLotLinesToEdit.length,
            autoPick: !packLotLinesToEdit.length && existingLotsName.length === 1,
        }));
        if (!packLotLinesToEdit.length && existingLotsName.length === 1) {
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
            const modifiedPackLotLines = Object.fromEntries(
                payload.filter((item) => item.id).map((item) => [item.id, item.text]),
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
        log.logic("openOpeningControl", () => ({
            session: this.session?.id,
            state: this.session?.state,
            show: this.shouldShowOpeningControl(),
        }));
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
                },
            );
        }
    }
    shouldShowOpeningControl() {
        return this.session.state === "opening_control";
    }

    closeOtherTabs() {
        const storageKey = `pos.tabs.${odoo.pos_config_id}`;
        localStorage[storageKey] = JSON.stringify({
            message: "close_tabs",
            session: this.session.id,
            at: Date.now(),
        });

        window.addEventListener(
            "storage",
            (event) => {
                if (event.key === storageKey && event.newValue) {
                    let msg;
                    try {
                        msg = JSON.parse(event.newValue);
                    } catch {
                        return;
                    }
                    log.logic("[storage] close_tabs", () => ({
                        message: msg.message,
                        session: msg.session,
                        current: this.session.id,
                    }));
                    if (
                        msg.message === "close_tabs" &&
                        msg.session === this.session.id
                    ) {
                        logPosMessage(
                            "Store",
                            "closeOtherTabs",
                            "POS / Session opened in another window. EXITING POS",
                            CONSOLE_COLOR,
                        );
                        this.closePos();
                    }
                }
            },
            false,
        );
    }

    showBackButton() {
        return showBackButton(this);
    }
    async onClickBackButton() {
        this.numberBuffer.capture();
        if (this.router.state.current === "TicketScreen") {
            if (this.ticket_screen_mobile_pane === "left") {
                const next = this.getDefaultPage();
                this.navigate(next.page, next.params);
            } else {
                this.ticket_screen_mobile_pane = "left";
            }
        } else if (
            this.mobile_pane === "left" ||
            ["PaymentScreen", "ActionScreen"].includes(this.router.state.current)
        ) {
            if (this.router.state.current === "ProductScreen") {
                this.getOrder()?.deselectOrderline();
            }

            this.mobile_pane =
                this.router.state.current === "PaymentScreen" ? "left" : "right";
            this.navigate("ProductScreen", {
                orderUuid: this.getOrder().uuid,
            });
        }
    }

    showSearchButton() {
        return showSearchButton(this);
    }

    async showQR(payment) {
        let qr;
        const endQr = log.perf("showQR: get_qr_code");
        log.pipeline("showQR", () => ({
            payment: payment.uuid,
            order: payment.pos_order_id?.uuid,
            method: payment.payment_method_id.id,
            amount: payment.amount,
        }));
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
            log.logic("showQR: generation failed", () => ({
                payment: payment.uuid,
                fallbackQr: Boolean(qr),
                connectionLost: error instanceof ConnectionLostError,
            }));
            if (!qr) {
                let message;
                if (error instanceof ConnectionLostError) {
                    message = _t(
                        "Connection to the server has been lost. Please check your internet connection.",
                    );
                } else {
                    message =
                        error?.data?.message ?? error?.message ?? _t("Unknown error");
                }
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Failure to generate Payment QR Code"),
                    body: message,
                });
                return false;
            }
        }
        endQr({ payment: payment.uuid, qr: Boolean(qr) });
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
            QRPopup,
        ).then((result) => {
            log.logic("showQR: closed", () => ({ payment: payment.uuid, result }));
            payment.qrPaymentData = null;
            return result;
        });
    }

    redirectToBackend() {
        log.lifecycle("redirectToBackend", () => ({ session: this.session?.id }));
        window.location = "/odoo/action-point_of_sale.action_client_pos_menu";
    }

    getExcludedProductIds() {
        return getExcludedProductIds(this);
    }

    areAllProductsSpecial(products) {
        return areAllProductsSpecial(this, products);
    }

    orderProductBySequenceAndFav(products) {
        return orderProductBySequenceAndFav(this, products);
    }

    get productsToDisplay() {
        return computeProductsToDisplay(this);
    }

    get productToDisplayByCateg() {
        return computeProductToDisplayByCateg(this);
    }

    getProductsBySearchWord(searchWord, products) {
        return getProductsBySearchWord(searchWord, products);
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
        this.searchProductWord = "";
        const { page, params } = this.getDefaultPage();
        log.lifecycle("orderDone", () => ({
            order: order.uuid,
            state: order.state,
            nextPage: page,
        }));
        this.navigate(
            page,
            page === "ProductScreen"
                ? { orderUuid: this.getEmptyOrder().uuid }
                : params,
        );
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
            (await this.data.orm.searchCount("pos.session", [
                ["id", "=", this.session.id],
            ])) === 0
        );
    }

    weighProduct() {
        return makeAwaitable(this.env.services.dialog, ScaleScreen);
    }

    async validateOrderFast(paymentMethod) {
        log.pipeline("validateOrderFast", () => ({
            order: this.getOrder().uuid,
            method: paymentMethod?.id,
        }));
        const validation = new OrderPaymentValidation({
            pos: this,
            orderUuid: this.getOrder().uuid,
            fastPaymentMethod: paymentMethod,
        });
        await validation.validateOrder(false);
        log.logic("validateOrderFast: outcome", () => ({
            order: validation.orderUuid,
            state: validation.order?.state,
            rollback: validation.order?.state === "draft",
        }));
        if (validation.order?.state === "draft") {
            validation.rollbackFastPayment();
        }
    }

    async clickSaveOrder() {
        const order = this.getOrder();
        this.addPendingOrder([order.id]);
        const result = await this.syncAllOrders({ orders: [order] });
        log.pipeline("clickSaveOrder", () => ({
            order: order.uuid,
            connectionLost: result instanceof ConnectionLostError,
        }));
        if (result instanceof ConnectionLostError) {
            this.notification.add(
                _t("Order saved locally. It will be sent once you are back online."),
                { type: "warning" },
            );
        } else {
            this.notification.add(_t("Order saved for later"), { type: "success" });
        }
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
 * @param {string} use_payment_terminal
 * @param {Object} ImplementedPaymentInterface
 */
export function register_payment_method(
    use_payment_terminal,
    ImplementedPaymentInterface,
) {
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
