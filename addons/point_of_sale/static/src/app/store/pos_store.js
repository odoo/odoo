/** @odoo-module */
/* global waitForWebfonts */

import { Order } from "@point_of_sale/app/store/models";
import { Mutex } from "@web/core/utils/concurrency";
import { PosDB } from "@point_of_sale/app/store/db";
import { markRaw, reactive } from "@odoo/owl";
import { roundPrecision as round_pr, floatIsZero } from "@web/core/utils/numbers";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { deduceUrl } from "@point_of_sale/utils";
import { Reactive } from "@web/core/utils/reactive";
import { HWPrinter } from "@point_of_sale/app/printer/hw_printer";
import { memoize } from "@web/core/utils/functions";
import { ConnectionLostError } from "@web/core/network/rpc";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { renderToString } from "@web/core/utils/render";
import { batched } from "@web/core/utils/timing";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import { ProductConfiguratorPopup } from "./product_configurator_popup/product_configurator_popup";
import { ComboConfiguratorPopup } from "./combo_configurator_popup/combo_configurator_popup";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";

const { DateTime } = luxon;
import { PartnerList } from "../screens/partner_list/partner_list";
import { ScaleScreen } from "../screens/scale_screen/scale_screen";

/* Returns an array containing all elements of the given
 * array corresponding to the rule function {agg} and without duplicates
 *
 * @template T
 * @template F
 * @param {T[]} array
 * @param {F} function
 * @returns {T[]}
 */
export function uniqueBy(array, agg) {
    const map = new Map();
    for (const item of array) {
        const key = agg(item);
        if (!map.has(key)) {
            map.set(key, item);
        }
    }
    return [...map.values()];
}

/**
 * Gets a product image as a base64 string so that it can be sent to the
 * customer display, as the display won't be able to fetch it, since the image
 * controller requires the client to be logged. This function is memoized on the
 * product id, so that we will only do this once per product.
 *
 * @param {number} productId id of the product
 * @param {string} writeDate the write date of the product, used as a cache
 *  buster in case the product image has been changed
 * @returns {string} the base64 representation of the product's image
 */
// FIXME: this can make a lot of requests to the server in case of a lot of
// products, we should probably load it when it's needed instead of loading it
// for all products at once.
const getProductImage = memoize(function getProductImage(productId, writeDate) {
    return new Promise(function (resolve, reject) {
        const img = new Image();
        img.addEventListener("load", () => {
            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");
            canvas.height = img.height;
            canvas.width = img.width;
            ctx.drawImage(img, 0, 0);
            resolve(canvas.toDataURL("image/jpeg"));
        });
        img.addEventListener("error", reject);
        img.src = `/web/image?model=product.product&field=image_128&id=${productId}&unique=${writeDate}`;
    });
});

export class PosStore extends Reactive {
    hasBigScrollBars = false;
    loadingSkipButtonIsShown = false;
    mainScreen = { name: null, component: null };

    static serviceDependencies = [
        "number_buffer",
        "barcode_reader",
        "hardware_proxy",
        "ui",
        "pos_data",
        "dialog",
        "printer",
    ];
    constructor() {
        super();
        this.ready = this.setup(...arguments).then(() => this);
    }
    // use setup instead of constructor because setup can be patched.
    async setup(
        env,
        { popup, number_buffer, hardware_proxy, barcode_reader, ui, pos_data, dialog, printer }
    ) {
        this.env = env;
        this.popup = popup;
        this.numberBuffer = number_buffer;
        this.barcodeReader = barcode_reader;
        this.ui = ui;
        this.dialog = dialog;
        this.printer = printer;
        this.db = new PosDB(); // a local database used to search trough products and categories & store pending orders
        this.data = pos_data;
        this.unwatched = markRaw({});
        this.pushOrderMutex = new Mutex();
        this.orders = [];

        // Business data; loaded from the server at launch
        this.company_logo = null;
        this.company_logo_base64 = "";
        this.taxes = [];
        this.order_sequence = 1;
        this.printers_category_ids_set = new Set();

        // Object mapping the order's name (which contains the uid) to it's server_id after
        // validation (order paid then sent to the backend).
        this.validated_orders_name_server_id_map = {};

        this.numpadMode = "quantity";
        this.mobile_pane = "right";
        this.ticket_screen_mobile_pane = "left";
        this.productListView = window.localStorage.getItem("productListView") || "grid";

        // Record<orderlineId, { 'qty': number, 'orderline': { qty: number, refundedQty: number, orderUid: string }, 'destinationOrderUid': string }>
        this.toRefundLines = {};
        this.TICKET_SCREEN_STATE = {
            syncedOrders: {
                currentPage: 1,
                cache: {},
                toShow: [],
                nPerPage: 80,
                totalCount: null,
                cacheDate: null,
            },
            ui: {
                selectedOrder: null,
                searchDetails: this.getDefaultSearchDetails(),
                filter: null,
                // maps the order's backendId to it's selected orderline
                selectedOrderlineIds: {},
                highlightHeaderNote: false,
            },
        };

        this.ordersToUpdateSet = new Set(); // used to know which orders need to be sent to the back end when syncing
        this.loadingOrderState = false; // used to prevent orders fetched to be put in the update set during the reactive change

        // these dynamic attributes can be watched for change by other models or widgets
        Object.assign(this, {
            synch: { status: "connected", pending: 0 },
            orders: [],
            selectedOrder: null,
            selectedPartner: null,
            selectedCategoryId: null,
            // FIXME POSREF this piece of state should probably be private to the product screen
            // but it currently needs to be available to the ProductInfo screen for dubious functional reasons
            searchProductWord: "",
        });

        this.ready = new Promise((resolve) => {
            this.markReady = resolve;
        });

        this.hardwareProxy = hardware_proxy;
        // FIXME POSREF: the hardwareProxy needs the pos and the pos needs the hardwareProxy. Maybe
        // the hardware proxy should just be part of the pos service?
        this.hardwareProxy.pos = this;
        await this.initServerData();
        if (this.config.use_proxy) {
            await this.connectToProxy();
        }
        this.closeOtherTabs();
        this.preloadImages();
        this.showScreen("ProductScreen");
    }

    async initServerData() {
        await this.processServerData();
        return await this.afterProcessServerData();
    }

    toggleImages(imageType = "product") {
        if (imageType === "product") {
            this.show_product_images = !this.show_product_images;
        }
        if (imageType === "category") {
            this.show_category_images = !this.show_category_images;
        }
        this.data.call("pos.config", "toggle_images", [
            [this.config.id],
            this.show_product_images ? "yes" : "no",
            this.show_category_images ? "yes" : "no",
        ]);
    }

    async processServerData() {
        // These fields should be unique for the pos_config
        // and should not change during the session, so we can
        // safely take the first element.this.models
        this.session = this.data.models["pos.session"].getFirst();
        this.config = this.data.models["pos.config"].getFirst();
        this.company = this.data.models["res.company"].getFirst();
        this.user = this.data.models["res.users"].getFirst();
        this.currency = this.data.models["res.currency"].getFirst();
        this.pickingType = this.data.models["stock.picking.type"].getFirst();

        // Custom data
        this.partner_commercial_fields = this.data.custom.partner_commercial_fields;
        this.server_version = this.data.custom.server_version;
        this.base_url = this.data.custom.base_url;
        this.has_cash_move_perm = this.data.custom.has_cash_move_perm;
        this.has_available_products = this.data.custom.has_available_products;
        this.pos_special_products_ids = this.data.custom.pos_special_products_ids;
        this.open_orders_json = this.data.custom.open_orders;
        this.show_product_images = this.data.custom.show_product_images === "yes";
        this.show_category_images = this.data.custom.show_category_images === "yes";
        this.models = this.data.models;

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
            const HWPrinter = this.create_printer(printer);

            HWPrinter.config = printer;
            this.unwatched.printers.push(HWPrinter);

            for (const id of printer.product_categories_ids) {
                this.printers_category_ids_set.add(id);
            }
        }
        this.config.iface_printers = !!this.unwatched.printers.length;

        // Monitor product pricelist
        this.models["product.product"].addEventListener(
            "create",
            this.computeProductPricelistCache.bind(this)
        );
        this.models["product.pricelist.item"].addEventListener(
            "create",
            this.computeProductPricelistCache.bind(this)
        );

        this.computeProductPricelistCache();
    }

    computeProductPricelistCache(data) {
        // This function is called via the addEventListener callback initiated in the
        // processServerData function when new products or pricelists are loaded into the PoS.
        // It caches the heavy pricelist calculation when there are many products and pricelists.
        const date = DateTime.now();
        let pricelistItems = this.models["product.pricelist.item"].getAll();
        let products = this.models["product.product"].getAll();

        if (data && data.length > 0) {
            if (data[0].model.modelName === "product.product") {
                products = data;
            }

            if (data[0].model.modelName === "product.pricelist.item") {
                pricelistItems = data;
            }
        }

        for (const product of products) {
            const applicableRules = {};

            for (const item of pricelistItems) {
                if (!applicableRules[item.pricelist_id.id]) {
                    applicableRules[item.pricelist_id.id] = [];
                }

                if (!product.isPricelistItemUsable(item, date)) {
                    continue;
                }

                if (item.product_id && product.id === item.product_id.id) {
                    applicableRules[item.pricelist_id.id].push(item);
                } else if (
                    item.raw.product_tmpl_id &&
                    product.raw?.product_tmpl_id === item.raw.product_tmpl_id
                ) {
                    applicableRules[item.pricelist_id.id].push(item);
                } else if (!item.raw.product_tmpl_id && !item.raw.product_id) {
                    applicableRules[item.pricelist_id.id].push(item);
                }
            }

            product.cachedPricelistRules = applicableRules;
        }
    }

    async loadProductPricelist(pricelistIds) {
        if (!pricelistIds || pricelistIds.length === 0) {
            return [];
        }

        const data = await this.data.read("product.pricelist", pricelistIds);
        const pricelistItemsIds = data.map((p) => p.raw.item_ids).flat();

        if (pricelistItemsIds.length) {
            await this.data.read("product.pricelist.item", pricelistItemsIds);
        }

        return data;
    }

    async loadProducts(productIds) {
        if (!productIds || productIds.length === 0) {
            return [];
        }
        const pIds = Array.from(new Set(productIds));
        const product = await this.data.read("product.product", pIds);
        await this._loadMissingPricelistItems(product);
    }

    async afterProcessServerData() {
        await this.load_orders();
        this.set_start_order();
        Object.assign(this.toRefundLines, this.db.load("TO_REFUND_LINES") || {});
        window.addEventListener("beforeunload", () =>
            this.db.save("TO_REFUND_LINES", this.toRefundLines)
        );
        const { start_category, iface_start_categ_id } = this.config;
        this.selectedCategoryId = (start_category && iface_start_categ_id?.[0]) || 0;
        // Push orders in background, do not await
        this.push_orders();
        // This method is to load the demo datas.
        this.load_server_orders();
        this.markReady();
    }

    get productListViewMode() {
        const viewMode = this.productListView && this.ui.isSmall ? this.productListView : "grid";
        if (viewMode === "grid") {
            return "d-grid gap-1";
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
    getProductPriceFormatted(product) {
        const formattedUnitPrice = this.env.utils.formatCurrency(this.getProductPrice(product));

        if (product.to_weight) {
            return `${formattedUnitPrice}/${product.uom_id.name}`;
        } else {
            return formattedUnitPrice;
        }
    }
    async openConfigurator({ product, initQuantity = 1 }) {
        const attrById = this.models["product.attribute"].getAllBy("id");
        const attributes = product.attribute_line_ids.filter(
            (attr) => attr.attribute_id.id in attrById
        );
        return await makeAwaitable(this.dialog, ProductConfiguratorPopup, {
            product: product,
            attributes: attributes,
        });
    }
    getProductPrice(product, p = false) {
        const pricelist = this.getDefaultPricelist();
        const price = p === false ? product.get_price(pricelist, 1) : p;
        const order = this.get_order();
        const taxes = this.get_taxes_after_fp(product.taxes_id, order && order.fiscal_position);
        const currentTaxes = product.taxes_id;
        const priceAfterFp = this.computePriceAfterFp(price, currentTaxes);
        const rounding = this.currency.rounding;
        const allPrices = this.compute_all(taxes, priceAfterFp.price, 1, rounding);

        if (this.config.iface_tax_included === "total") {
            return allPrices.total_included;
        } else {
            return allPrices.total_excluded;
        }
    }
    getDefaultSearchDetails() {
        return {
            fieldName: "RECEIPT_NUMBER",
            searchTerm: "",
        };
    }
    getDefaultPricelist() {
        const current_order = this.get_order();
        if (current_order) {
            return current_order.pricelist;
        }
        return this.config.pricelist_id;
    }
    async getAddProductOptions(product, code) {
        const product_packaging_by_barcode = this.models["product.packaging"].getAllBy("barcode");

        let price_extra = 0.0;
        let draftPackLotLines, packLotLinesToEdit, attribute_value_ids;
        let quantity = 1;
        let comboConfigurator = [];
        let attribute_custom_values = {};

        if (code && product_packaging_by_barcode[code.code]) {
            quantity = product_packaging_by_barcode[code.code].qty;
        }

        if (product.isConfigurable()) {
            const payload = await this.openConfigurator({ product, initQuantity: quantity });
            if (payload) {
                attribute_value_ids = payload.attribute_value_ids;
                attribute_custom_values = payload.attribute_custom_values;
                price_extra += payload.price_extra;
                quantity = payload.quantity;
            } else {
                return;
            }
        }

        if (product.combo_ids.length) {
            // { combo_line_id: {}, configuration: {}}
            const payload = await makeAwaitable(this.env.services.dialog, ComboConfiguratorPopup, {
                product: product,
                keepBehind: true,
            });

            if (!payload) {
                return;
            }

            comboConfigurator = payload;
        }
        // Gather lot information if required.
        if (product.isTracked()) {
            packLotLinesToEdit =
                (!product.isAllowOnlyOneLot() &&
                    this.selectedOrder
                        .get_orderlines()
                        .filter((line) => !line.get_discount())
                        .find((line) => line.product.id === product.id)
                        ?.getPackLotLinesToEdit()) ||
                [];
            // if the lot information exists in the barcode, we don't need to ask it from the user.
            if (code && code.type === "lot") {
                // consider the old and new packlot lines
                const modifiedPackLotLines = Object.fromEntries(
                    packLotLinesToEdit.filter((item) => item.id).map((item) => [item.id, item.text])
                );
                const newPackLotLines = [{ lot_name: code.code }];
                draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
            } else {
                draftPackLotLines = await this.getEditedPackLotLines(
                    product.isAllowOnlyOneLot(),
                    packLotLinesToEdit,
                    product.display_name
                );
            }
            if (!draftPackLotLines) {
                return;
            }
        }

        // Take the weight if necessary.
        if (product.to_weight && this.config.iface_electronic_scale) {
            if (product.isScaleAvailable) {
                const weight = await makeAwaitable(this.env.services.dialog, ScaleScreen, {
                    product,
                });
                if (!weight) {
                    return;
                }
                quantity = weight;
            } else {
                await product._onScaleNotAvailable();
            }
        }

        return {
            draftPackLotLines,
            quantity,
            attribute_custom_values,
            price_extra,
            comboConfigurator,
            attribute_value_ids,
        };
    }

    _loadPosPrinters(printers) {
        this.unwatched.printers = [];
        // list of product categories that belong to one or more order printer
        for (const printerConfig of printers) {
            const printer = this.create_printer(printerConfig);
            printer.config = printerConfig;
            this.unwatched.printers.push(printer);
            for (const cat of printer.product_categories_ids) {
                this.printers_category_ids_set.add(cat.id);
            }
        }
        this.config.iface_printers = !!this.unwatched.printers.length;
    }
    create_printer(config) {
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
    async _loadPictures() {
        this.company_logo = new Image();
        return new Promise((resolve, reject) => {
            this.company_logo.onload = () => {
                const img = this.company_logo;
                let ratio = 1;
                const targetwidth = 300;
                const maxheight = 150;
                if (img.width !== targetwidth) {
                    ratio = targetwidth / img.width;
                }
                if (img.height * ratio > maxheight) {
                    ratio = maxheight / img.height;
                }
                const width = Math.floor(img.width * ratio);
                const height = Math.floor(img.height * ratio);
                const c = document.createElement("canvas");
                c.width = width;
                c.height = height;
                const ctx = c.getContext("2d");
                ctx.drawImage(this.company_logo, 0, 0, width, height);

                this.company_logo_base64 = c.toDataURL();
                resolve();
            };
            this.company_logo.onerror = () => {
                reject();
            };
            this.company_logo.crossOrigin = "anonymous";
            this.company_logo.src = `/web/image?model=res.company&id=${this.company.id}&field=logo`;
        });
    }

    // reload the list of partner, returns as a promise that resolves if there were
    // updated partners, and fails if not
    async load_new_partners() {
        const partnerWriteDate = Object.values(this.models["res.partner"].getAll()[0]._raw).map(
            (p) => p.write_date
        );
        const sortedDates = partnerWriteDate
            .map((dateString) => new Date(dateString))
            .sort((a, b) => b - a);
        const lastDate = sortedDates[0];
        const search_params = { domain: [["write_date", ">", lastDate]] };
        await this.data.searchRead("res.partner", search_params.domain);
    }

    loadOpenOrders(openOrders) {
        // This method is for the demo data
        let isOrderSet = false;
        for (const json of openOrders) {
            if (this.orders.find((el) => el.server_id === json.id)) {
                continue;
            }
            this._createOrder(json);
            if (!isOrderSet) {
                this.selectedOrder = this.orders[this.orders.length - 1];
                isOrderSet = true;
            }
        }
    }

    /**
     * @returns true if the POS app (not only this POS config) has at least one valid product.
     */
    posHasValidProduct() {
        return this.has_available_products;
    }

    setSelectedCategoryId(categoryId) {
        this.selectedCategoryId = categoryId;
    }

    /**
     * Remove the order passed in params from the list of orders
     * @param order
     */
    removeOrder(order, removeFromServer = true) {
        const index = this.orders.findIndex((_item) => order.cid == _item.cid);
        if (index < 0) {
            return index;
        }
        this.orders.splice(index, 1);
        this.db.remove_unpaid_order(order);
        for (const line of order.get_orderlines()) {
            if (line.refunded_orderline_id) {
                delete this.toRefundLines[line.refunded_orderline_id];
            }
        }
        if (this.isOpenOrderShareable() && removeFromServer) {
            if (this.ordersToUpdateSet.has(order)) {
                this.ordersToUpdateSet.delete(order);
            }
            if (order.server_id && !order.finalized) {
                this.setOrderToRemove(order);
            }
        }
    }
    setOrderToRemove(order) {
        this.db.set_order_to_remove_from_server(order);
    }

    /**
     * Return the current cashier (in this case, the user)
     * @returns {name: string, id: int, role: string}
     */
    get_cashier() {
        return this.user;
    }
    get_cashier_user_id() {
        return this.user.id;
    }
    get orderPreparationCategories() {
        if (this.printers_category_ids_set) {
            return new Set([...this.printers_category_ids_set]);
        }
        return new Set();
    }
    cashierHasPriceControlRights() {
        return !this.config.restrict_price_control || this.get_cashier().role == "manager";
    }
    _onReactiveOrderUpdated(order) {
        order.save_to_db();
        if (this.isOpenOrderShareable() && !this.loadingOrderState) {
            this.ordersToUpdateSet.add(order);
        }
    }
    createReactiveOrder(json) {
        const options = { pos: this };
        if (json) {
            options.json = json;
        }
        return this.makeOrderReactive(new Order({ env: this.env }, options));
    }
    makeOrderReactive(order) {
        const batchedCallback = batched(() => {
            this._onReactiveOrderUpdated(order);
        });
        order = reactive(order, batchedCallback);
        order.save_to_db();
        return order;
    }
    // creates a new empty order and sets it as the current order
    add_new_order() {
        if (this.isOpenOrderShareable()) {
            this.sendDraftToServer();
        }
        if (this.selectedOrder) {
            this.selectedOrder.firstDraft = false;
            this.selectedOrder.updateSavedQuantity();
        }
        const order = this.createReactiveOrder();
        this.orders.push(order);
        this.selectedOrder = order;
        return order;
    }
    selectNextOrder() {
        if (this.orders.length > 0) {
            this.selectedOrder = this.orders[0];
        } else {
            this.add_new_order();
        }
    }
    async sendDraftToServer() {
        const ordersUidsToSync = [...this.ordersToUpdateSet].map((order) => order.uid);
        const ordersToSync = this.db.get_unpaid_orders_to_sync(ordersUidsToSync);
        const ordersResponse = await this._save_to_server(ordersToSync, { draft: true });
        const orders = [...this.ordersToUpdateSet].map((order) => order);
        ordersResponse.forEach((orderResponseData) => this._updateOrder(orderResponseData, orders));
        this.ordersToUpdateSet.clear();
    }
    addOrderToUpdateSet() {
        this.ordersToUpdateSet.add(this.selectedOrder);
    }
    // created this hook for modularity
    _updateOrder(ordersResponseData, orders) {
        const order = orders.find((order) => order.name === ordersResponseData.pos_reference);
        if (order) {
            order.server_id = ordersResponseData.id;
            return order;
        }
    }
    /**
     * Load the locally saved unpaid orders for this PoS Config.
     *
     * First load all orders belonging to the current session.
     * Second load all orders belonging to the same config but from other sessions,
     * Only if tho order has orderlines.
     */
    async load_orders() {
        this.loadingOrderState = true;
        var jsons = this.db.get_unpaid_orders();
        await this._loadMissingProducts(jsons);
        await this._loadMissingPartners(jsons);
        var orders = [];

        for (var i = 0; i < jsons.length; i++) {
            var json = jsons[i];
            if (json.pos_session_id === this.session.id) {
                orders.push(this.createReactiveOrder(json));
            }
        }
        for (i = 0; i < jsons.length; i++) {
            json = jsons[i];
            if (
                json.pos_session_id !== this.session.id &&
                (json.lines.length > 0 || json.statement_ids.length > 0)
            ) {
                orders.push(this.createReactiveOrder(json));
            } else if (json.pos_session_id !== this.session.id) {
                this.db.remove_unpaid_order(jsons[i]);
            }
        }

        orders = orders.sort(function (a, b) {
            return a.sequence_number - b.sequence_number;
        });

        if (orders.length) {
            for (const order of orders) {
                this.orders.push(order);
            }
        }
        this.loadingOrderState = false;
    }
    load_server_orders() {
        if (!this.open_orders_json) {
            return;
        }
        this.loadOpenOrders(this.open_orders_json);
    }
    async _loadMissingProducts(orders) {
        const missingProductIds = new Set([]);

        for (const order of orders) {
            for (const line of order.lines) {
                const productId = line[2].product_id;
                if (missingProductIds.has(productId)) {
                    continue;
                }
                if (!this.models["product.product"].get(productId)) {
                    missingProductIds.add(productId);
                }
            }
        }

        await this.loadProducts([...missingProductIds]);
    }
    async _loadMissingPricelistItems(products) {
        if (!products.length) {
            return;
        }

        const product_tmpl_ids = products.map((product) => product.raw.product_tmpl_id);
        const product_ids = products.map((product) => product.id);
        await this.data.callRelated("pos.session", "get_pos_ui_product_pricelist_item_by_product", [
            odoo.pos_session_id,
            product_tmpl_ids,
            product_ids,
        ]);
    }

    // load the partners based on the ids
    async _loadPartners(partnerIds) {
        if (partnerIds.length > 0) {
            await this.data.read("res.partner", partnerIds);
        }
    }
    async _loadMissingPartners(orders) {
        const missingPartnerIds = new Set([]);
        for (const order of orders) {
            const partnerId = order.partner_id;
            if (missingPartnerIds.has(partnerId) || !partnerId) {
                continue;
            }
            const partner = this.models["res.partner"].get(partnerId);
            if (!partner) {
                missingPartnerIds.add(partnerId);
            }
        }
        await this._loadPartners([...missingPartnerIds]);
    }
    setLoadingOrderState(bool) {
        this.loadingOrderState = bool;
    }
    async _removeOrdersFromServer() {
        const removedOrdersIds = this.db.get_ids_to_remove_from_server();
        if (removedOrdersIds.length === 0) {
            return;
        }

        try {
            const removeOrdersResponseData = await this.data.silentCall(
                "pos.order",
                "remove_from_ui",
                [removedOrdersIds]
            );
            this._postRemoveFromServer(removedOrdersIds, removeOrdersResponseData);
        } catch (reason) {
            const error = reason.message;
            if (error.code === 200) {
                // Business Logic Error, not a connection problem
                //if warning do not need to display traceback!!
                if (error.data.exception_type == "warning") {
                    delete error.data.debug;
                }
            }
            // important to throw error here and let the rendering component handle the error
            console.warn("Failed to remove orders:", removedOrdersIds);
            this._postRemoveFromServer(removedOrdersIds);
            throw error;
        }
    }
    _postRemoveFromServer(serverIds, data) {
        this.db.set_ids_removed_from_server(serverIds);
    }
    _replaceOrders(ordersToReplace, newOrdersJsons) {
        ordersToReplace.forEach((order) => {
            // We don't remove the validated orders because we still want to see them in the ticket screen.
            // Orders in 'ReceiptScreen' or 'TipScreen' are validated orders.
            if (this._shouldRemoveOrder(order)) {
                this.removeOrder(order, false);
            }
        });
        let removeSelected = true;
        newOrdersJsons.forEach((json) => {
            const isSelectedOrder = this._createOrder(json);
            if (removeSelected && isSelectedOrder) {
                removeSelected = false;
            }
        });
        if (this._shouldRemoveSelectedOrder(removeSelected)) {
            this._removeSelectedOrder();
        }
    }
    _shouldRemoveOrder(order) {
        return (
            (!this.selectedOrder || this.selectedOrder.uid != order.uid) &&
            order.server_id &&
            !order.finalized
        );
    }
    _shouldRemoveSelectedOrder(removeSelected) {
        return removeSelected && this.selectedOrder.server_id && !this.selectedOrder.finalized;
    }
    _shouldCreateOrder(json) {
        return json.uid != this.selectedOrder.uid;
    }
    _isSelectedOrder(json) {
        return json.uid == this.selectedOrder.uid;
    }
    _createOrder(json) {
        if (this._shouldCreateOrder(json)) {
            const order = this.createReactiveOrder(json);
            this.orders.push(order);
        }
        return this._isSelectedOrder(json);
    }
    _removeSelectedOrder() {
        this.removeOrder(this.selectedOrder, false);
        const orderList = this.get_order_list();
        if (orderList.length != 0) {
            this.set_order(orderList[0]);
        }
    }
    async _syncAllOrdersFromServer() {
        await this._removeOrdersFromServer();
        const ordersJson = await this._getOrdersJson();
        let message = null;
        message = await this._addPricelists(ordersJson);
        let messageFp = null;
        messageFp = await this._addFiscalPositions(ordersJson);
        if (messageFp) {
            if (message) {
                message += "\n" + messageFp;
            } else {
                message = messageFp;
            }
        }
        await this._getMissingProducts(ordersJson);
        const allOrders = [...this.get_order_list()];
        this._replaceOrders(allOrders, ordersJson);
        this.sortOrders();
        return message;
    }
    async _getOrdersJson() {
        return await this.data.call("pos.order", "export_for_ui_shared_order", [], {
            config_id: this.config.id,
        });
    }
    async _addPricelists(ordersJson) {
        const pricelistsToGet = [];
        ordersJson.forEach((order) => {
            let found = false;
            for (const pricelist of this.models["product.pricelist"].getAll()) {
                if (pricelist.id === order.pricelist_id) {
                    found = true;
                    break;
                }
            }
            if (!found && order.pricelist_id) {
                pricelistsToGet.push(order.pricelist_id);
            }
        });
        let message = null;
        if (pricelistsToGet.length > 0) {
            const data = this.loadProductPricelist(pricelistsToGet);
            message = _t(
                "%s pricelist(s) added to the configuration.",
                data["product.pricelist"].map((p) => p.name).join(", ")
            );
        }
        return message;
    }
    async _getPricelistJson(pricelistsToGet) {
        return await this.data.call("pos.session", "get_pos_ui_product_pricelists_by_ids", [
            [odoo.pos_session_id],
            pricelistsToGet,
        ]);
    }
    async _getMissingProducts(ordersJson) {
        const productIds = [];
        for (const order of ordersJson) {
            for (const orderline of order.lines) {
                if (!this.models["product.product"].get(orderline[2].product_id)) {
                    productIds.push(orderline[2].product_id);
                }
            }
        }

        await this.loadProducts(productIds);
    }
    async _addFiscalPositions(ordersJson) {
        const fiscalPositionToGet = [];
        ordersJson.forEach((order) => {
            let found = false;
            for (const fp of this.models["account.fiscal.position"].getAll()) {
                if (fp.id === order.fiscal_position_id) {
                    found = true;
                    break;
                }
            }
            if (!found && order.fiscal_position_id) {
                fiscalPositionToGet.push(order.fiscal_position_id);
            }
        });
        let message = null;
        if (fiscalPositionToGet.length > 0) {
            const data = await this.data.read("account.fiscal.position", fiscalPositionToGet);
            message = _t(
                "%s fiscal position(s) added to the configuration.",
                data.map((p) => p.name).join(", ")
            );
        }
        return message;
    }
    sortOrders() {
        this.orders.sort((a, b) => (a.name > b.name ? 1 : -1));
    }
    async getProductInfo(product, quantity) {
        const order = this.get_order();
        // check back-end method `get_product_info_pos` to see what it returns
        // We do this so it's easier to override the value returned and use it in the component template later
        const productInfo = await this.data.call("product.product", "get_product_info_pos", [
            [product.id],
            product.get_price(order.pricelist, quantity),
            quantity,
            this.config.id,
        ]);

        const priceWithoutTax = productInfo["all_prices"]["price_without_tax"];
        const margin = priceWithoutTax - product.standard_price;
        const orderPriceWithoutTax = order.get_total_without_tax();
        const orderCost = order.get_total_cost();
        const orderMargin = orderPriceWithoutTax - orderCost;

        const costCurrency = this.env.utils.formatCurrency(product.standard_price);
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
    set_start_order() {
        if (this.orders.length && !this.selectedOrder) {
            this.selectedOrder = this.orders[0];
            if (this.isOpenOrderShareable()) {
                this.ordersToUpdateSet.add(this.orders[0]);
            }
        } else {
            this.add_new_order();
        }
    }

    // return the current order
    get_order() {
        return this.selectedOrder;
    }

    // change the current order
    set_order(order, options) {
        if (this.selectedOrder) {
            this.selectedOrder.firstDraft = false;
            this.selectedOrder.updateSavedQuantity();
        }
        this.selectedOrder = order;
    }

    // return the list of unpaid orders
    get_order_list() {
        return this.orders;
    }

    computePriceAfterFp(price, taxes) {
        const order = this.get_order();
        if (order && order.fiscal_position) {
            const mapped_included_taxes = [];
            let new_included_taxes = [];
            taxes.forEach((tax) => {
                const line_taxes = this.get_taxes_after_fp([tax.id], order.fiscal_position);
                if (line_taxes.length && line_taxes[0].price_include) {
                    new_included_taxes = new_included_taxes.concat(line_taxes);
                }
                if (tax.price_include && !line_taxes.includes(tax)) {
                    mapped_included_taxes.push(tax);
                }
            });

            if (mapped_included_taxes.length > 0) {
                if (new_included_taxes.length > 0) {
                    const price_without_taxes = this.compute_all(
                        mapped_included_taxes,
                        price,
                        1,
                        this.currency.rounding,
                        true
                    ).total_excluded;
                    price = this.compute_all(
                        new_included_taxes,
                        price_without_taxes,
                        1,
                        this.currency.rounding,
                        false
                    ).total_included;
                } else {
                    price = this.compute_all(
                        mapped_included_taxes,
                        price,
                        1,
                        this.currency.rounding,
                        true
                    ).total_excluded;
                }
            }
        }
        return typeof price === "object" ? price : { price: price };
    }

    /**
     * Renders the HTML for the customer display and returns it as a string.
     *
     * @returns {string}
     */
    async customerDisplayHTML(closeUI = false) {
        const order = this.get_order();
        if (closeUI || !order) {
            return renderToString("point_of_sale.CustomerFacingDisplayNoOrder", {
                pos: this,
                origin: window.location.origin,
            });
        }

        const orderLines = order.get_orderlines();
        const productImages = Object.fromEntries(
            await Promise.all(
                orderLines.map(async ({ product }) => [
                    product.id,
                    await getProductImage(product.id, product.writeDate),
                ])
            )
        );

        return renderToString("point_of_sale.CustomerFacingDisplayOrder", {
            pos: this,
            formatCurrency: this.env.utils.formatCurrency,
            origin: window.location.origin,
            order,
            productImages,
        });
    }

    // To be used in the context of closing the POS
    // Saves the order locally and try to send it to the backend.
    // If there is an error show a popup
    async push_orders_with_closing_popup(opts = {}) {
        try {
            await this.push_orders(opts);
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

    push_orders(opts = {}) {
        return this.pushOrderMutex.exec(() => this._flush_orders(this.db.get_orders(), opts));
    }

    push_single_order(order) {
        const order_id = this.db.add_order(order.export_as_JSON());
        return this.pushOrderMutex.exec(() => this._flush_orders([this.db.get_order(order_id)]));
    }

    // Send validated orders to the backend.
    // Resolves to the backend ids of the synced orders.
    async _flush_orders(orders, options) {
        try {
            const server_ids = await this._save_to_server(orders, options);
            for (let i = 0; i < server_ids.length; i++) {
                this.validated_orders_name_server_id_map[server_ids[i].pos_reference] =
                    server_ids[i].id;
            }
            return server_ids;
        } catch (error) {
            if (!(error instanceof ConnectionLostError)) {
                for (const order of orders) {
                    const reactiveOrder = this.orders.find((o) => o.uid === order.id);
                    reactiveOrder.finalized = false;
                    this.db.remove_order(reactiveOrder.uid);
                    this.db.save_unpaid_order(reactiveOrder);
                }
            }
            throw error;
        } finally {
            this._after_flush_orders(orders);
        }
    }
    /**
     * Hook method after _flush_orders resolved or rejected.
     * It aims to:
     *   - remove the refund orderlines from toRefundLines
     *   - invalidate cache of refunded synced orders
     */
    _after_flush_orders(orders) {
        const refundedOrderIds = new Set();
        for (const order of orders) {
            for (const line of order.data.lines) {
                const refundDetail = this.toRefundLines[line[2].refunded_orderline_id];
                if (!refundDetail) {
                    continue;
                }
                // Collect the backend id of the refunded orders.
                refundedOrderIds.add(refundDetail.orderline.orderBackendId);
                // Reset the refund detail for the orderline.
                delete this.toRefundLines[refundDetail.orderline.id];
            }
        }
        this._invalidateSyncedOrdersCache([...refundedOrderIds]);
    }
    _invalidateSyncedOrdersCache(ids) {
        for (const id of ids) {
            delete this.TICKET_SCREEN_STATE.syncedOrders.cache[id];
        }
    }

    /**
     * Context to be overriden in other modules/localisations
     * while processing orders in the backend
     */
    _getCreateOrderContext(orders, options) {
        return this.context || {};
    }
    // send an array of orders to the server
    // available options:
    // - timeout: timeout for the rpc call in ms
    // returns a promise that resolves with the list of
    // server generated ids for the sent orders
    async _save_to_server(orders, options) {
        if (!orders || !orders.length) {
            return Promise.resolve([]);
        }
        options = options || {};
        for (const order of orders) {
            order.to_invoice = options.to_invoice || false;
        }

        try {
            const serverIds = await this.data.call(
                "pos.order",
                "create_from_ui",
                [orders, options.draft || false],
                {
                    context: this._getCreateOrderContext(orders, options),
                }
            );

            const orderToRemove = serverIds.map((sid) => sid.pos_reference.split(" ")[1]);
            for (const serverId of serverIds) {
                const order = this.env.services.pos.orders.find(
                    (order) => order.name === serverId.pos_reference
                );

                if (order) {
                    order.server_id = serverId.id;
                }
            }

            for (const order_id of orderToRemove) {
                this.db.remove_order(order_id);
            }

            this.failed = false;
            return serverIds;
        } catch (error) {
            console.warn("Failed to send orders:", orders);
            if (error.code === 200) {
                // Business Logic Error, not a connection problem
                // Hide error if already shown before ...
                if ((!this.failed || options.show_error) && !options.to_invoice) {
                    this.failed = error;
                    throw error;
                }
            }
            throw error;
        }
    }

    // Exports the paid orders (the ones waiting for internet connection)
    export_paid_orders() {
        return JSON.stringify(
            {
                paid_orders: this.db.get_orders(),
                session: this.session.name,
                session_id: this.session.id,
                date: new Date().toUTCString(),
                version: this.server_version.server_version_info,
            },
            null,
            2
        );
    }

    // Exports the unpaid orders (the tabs)
    export_unpaid_orders() {
        return JSON.stringify(
            {
                unpaid_orders: this.db.get_unpaid_orders(),
                session: this.session.name,
                session_id: this.session.id,
                date: new Date().toUTCString(),
                version: this.server_version.server_version_info,
            },
            null,
            2
        );
    }

    // This imports paid or unpaid orders from a json file whose
    // contents are provided as the string str.
    // It returns a report of what could and what could not be
    // imported.
    import_orders(str) {
        var json = JSON.parse(str);
        var report = {
            // Number of paid orders that were imported
            paid: 0,
            // Number of unpaid orders that were imported
            unpaid: 0,
            // Orders that were not imported because they already exist (uid conflict)
            unpaid_skipped_existing: 0,
            // Orders that were not imported because they belong to another session
            unpaid_skipped_session: 0,
            // The list of session ids to which skipped orders belong.
            unpaid_skipped_sessions: [],
        };

        if (json.paid_orders) {
            for (var i = 0; i < json.paid_orders.length; i++) {
                this.db.add_order(json.paid_orders[i].data);
            }
            report.paid = json.paid_orders.length;
            this.push_orders();
        }

        if (json.unpaid_orders) {
            var orders = [];
            var existing = this.get_order_list();
            var existing_uids = {};
            var skipped_sessions = {};

            for (i = 0; i < existing.length; i++) {
                existing_uids[existing[i].uid] = true;
            }

            for (i = 0; i < json.unpaid_orders.length; i++) {
                var order = json.unpaid_orders[i];
                if (order.pos_session_id !== this.session.id) {
                    report.unpaid_skipped_session += 1;
                    skipped_sessions[order.pos_session_id] = true;
                } else if (existing_uids[order.uid]) {
                    report.unpaid_skipped_existing += 1;
                } else {
                    orders.push(this.createReactiveOrder(order));
                }
            }

            orders = orders.sort(function (a, b) {
                return a.sequence_number - b.sequence_number;
            });

            if (orders.length) {
                report.unpaid = orders.length;
                this.orders.push(orders);
            }

            report.unpaid_skipped_sessions = Object.keys(skipped_sessions);
        }

        return report;
    }

    _load_orders() {
        var jsons = this.db.get_unpaid_orders();
        var orders = [];
        var not_loaded_count = 0;

        for (var i = 0; i < jsons.length; i++) {
            var json = jsons[i];
            if (json.pos_session_id === this.session.id) {
                orders.push(this.createReactiveOrder(json));
            } else {
                not_loaded_count += 1;
            }
        }

        if (not_loaded_count) {
            console.info(
                "There are " +
                    not_loaded_count +
                    " locally saved unpaid orders belonging to another session"
            );
        }

        orders = orders.sort(function (a, b) {
            return a.sequence_number - b.sequence_number;
        });

        if (orders.length) {
            this.orders.push(orders);
        }
    }

    /**
     * Mirror JS method of:
     * _compute_amount in addons/account/models/account.py
     */
    _compute_all(tax, base_amount, quantity, price_exclude) {
        if (price_exclude === undefined) {
            var price_include = tax.price_include;
        } else {
            price_include = !price_exclude;
        }
        if (tax.amount_type === "fixed") {
            // Use sign on base_amount and abs on quantity to take into account the sign of the base amount,
            // which includes the sign of the quantity and the sign of the price_unit
            // Amount is the fixed price for the tax, it can be negative
            // Base amount included the sign of the quantity and the sign of the unit price and when
            // a product is returned, it can be done either by changing the sign of quantity or by changing the
            // sign of the price unit.
            // When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
            // a "else" case is needed.
            if (base_amount) {
                return Math.sign(base_amount) * Math.abs(quantity) * tax.amount;
            } else {
                return quantity * tax.amount;
            }
        }
        if (tax.amount_type === "percent" && !price_include) {
            return (base_amount * tax.amount) / 100;
        }
        if (tax.amount_type === "percent" && price_include) {
            return base_amount - base_amount / (1 + tax.amount / 100);
        }
        if (tax.amount_type === "division" && !price_include) {
            return base_amount / (1 - tax.amount / 100) - base_amount;
        }
        if (tax.amount_type === "division" && price_include) {
            return base_amount - base_amount * (tax.amount / 100);
        }
        return false;
    }
    /**
     * @param {Object} tax
     * @param {integer} sign
     * @param {float} factorized_tax_amount
     * @param {float} tax_base_amount
     * @param {float} currency_round
     * @returns {Object}
     */
    _prepare_tax_vals_data(tax, sign, factorized_tax_amount, tax_base_amount, currency_rounding) {
        return {
            id: tax.id,
            name: tax.name,
            amount: sign * factorized_tax_amount,
            base: sign * round_pr(tax_base_amount, currency_rounding),
        };
    }

    /**
     * Mirror JS method of:
     * compute_all in addons/account/models/account.py
     *
     * Read comments in the python side method for more details about each sub-methods.
     */
    compute_all(taxes, price_unit, quantity, currency_rounding, handle_price_include = true) {
        var self = this;

        // 1) Flatten the taxes.

        var _collect_taxes = function (taxes, all_taxes) {
            taxes = [...taxes].sort(function (tax1, tax2) {
                return tax1.sequence - tax2.sequence;
            });
            taxes.forEach((tax) => {
                if (tax.amount_type === "group") {
                    all_taxes = _collect_taxes(tax.children_tax_ids, all_taxes);
                } else {
                    all_taxes.push(tax);
                }
            });
            return all_taxes;
        };
        var collect_taxes = function (taxes) {
            return _collect_taxes(taxes, []);
        };

        taxes = collect_taxes(taxes);
        // 2) Deal with the rounding methods

        const company = this.company;
        var round_tax = company.tax_calculation_rounding_method != "round_globally";

        var initial_currency_rounding = currency_rounding;
        if (!round_tax) {
            currency_rounding = currency_rounding * 0.00001;
        }

        // 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
        var recompute_base = function (base_amount, incl_tax_amounts) {
            let fixed_amount = incl_tax_amounts.fixed_amount;
            let division_amount = 0.0;
            for (const [, tax_factor] of incl_tax_amounts.division_taxes) {
                division_amount += tax_factor;
            }
            let percent_amount = 0.0;
            for (const [, tax_factor] of incl_tax_amounts.percent_taxes) {
                percent_amount += tax_factor;
            }

            if (company.country && company.country.code === "IN") {
                for (const [i, tax_factor] of incl_tax_amounts.percent_taxes) {
                    const tax_amount = round_pr(
                        (base_amount * tax_factor) / (100 + percent_amount),
                        currency_rounding
                    );
                    cached_tax_amounts[i] = tax_amount;
                    fixed_amount += tax_amount;
                }
                percent_amount = 0.0;
            }

            Object.assign(incl_tax_amounts, {
                percent_taxes: [],
                division_taxes: [],
                fixed_amount: 0.0,
            });

            return (
                (((base_amount - fixed_amount) / (1.0 + percent_amount / 100.0)) *
                    (100 - division_amount)) /
                100
            );
        };

        var base = round_pr(price_unit * quantity, initial_currency_rounding);

        var sign = 1;
        if (base < 0) {
            base = -base;
            sign = -1;
        }

        var total_included_checkpoints = {};
        var i = taxes.length - 1;
        var store_included_tax_total = true;

        const incl_tax_amounts = {
            percent_taxes: [],
            division_taxes: [],
            fixed_amount: 0.0,
        };

        var cached_tax_amounts = {};
        if (handle_price_include) {
            taxes.reverse().forEach(function (tax) {
                if (tax.include_base_amount) {
                    base = recompute_base(base, incl_tax_amounts);
                    store_included_tax_total = true;
                }
                if (tax.price_include) {
                    if (tax.amount_type === "percent") {
                        incl_tax_amounts.percent_taxes.push([
                            i,
                            tax.amount * tax.sum_repartition_factor,
                        ]);
                    } else if (tax.amount_type === "division") {
                        incl_tax_amounts.division_taxes.push([
                            i,
                            tax.amount * tax.sum_repartition_factor,
                        ]);
                    } else if (tax.amount_type === "fixed") {
                        incl_tax_amounts.fixed_amount +=
                            Math.abs(quantity) * tax.amount * tax.sum_repartition_factor;
                    } else {
                        var tax_amount = self._compute_all(tax, base, quantity);
                        incl_tax_amounts.fixed_amount += tax_amount;
                        cached_tax_amounts[i] = tax_amount;
                    }
                    if (store_included_tax_total) {
                        total_included_checkpoints[i] = base;
                        store_included_tax_total = false;
                    }
                }
                i -= 1;
            });
        }

        var total_excluded = round_pr(
            recompute_base(base, incl_tax_amounts),
            initial_currency_rounding
        );
        var total_included = total_excluded;

        // 4) Iterate the taxes in the sequence order to fill missing base/amount values.

        base = total_excluded;

        var skip_checkpoint = false;

        var taxes_vals = [];
        i = 0;
        var cumulated_tax_included_amount = 0;
        taxes.reverse().forEach(function (tax) {
            if (tax.price_include || tax.is_base_affected) {
                var tax_base_amount = base;
            } else {
                tax_base_amount = total_excluded;
            }

            if (
                !skip_checkpoint &&
                tax.price_include &&
                total_included_checkpoints[i] !== undefined &&
                tax.sum_repartition_factor != 0
            ) {
                var tax_amount =
                    total_included_checkpoints[i] - (base + cumulated_tax_included_amount);
                cumulated_tax_included_amount = 0;
            } else if (tax.price_include && cached_tax_amounts.hasOwnProperty(i)) {
                var tax_amount = cached_tax_amounts[i];
            } else {
                var tax_amount = self._compute_all(tax, tax_base_amount, quantity, true);
            }

            tax_amount = round_pr(tax_amount, currency_rounding);
            var factorized_tax_amount = round_pr(
                tax_amount * tax.sum_repartition_factor,
                currency_rounding
            );

            if (tax.price_include && total_included_checkpoints[i] === undefined) {
                cumulated_tax_included_amount += factorized_tax_amount;
            }

            taxes_vals.push(
                self._prepare_tax_vals_data(
                    tax,
                    sign,
                    factorized_tax_amount,
                    tax_base_amount,
                    currency_rounding
                )
            );

            if (tax.include_base_amount) {
                base += factorized_tax_amount;
                if (!tax.price_include) {
                    skip_checkpoint = true;
                }
            }

            total_included += factorized_tax_amount;
            i += 1;
        });

        return {
            taxes: taxes_vals,
            total_excluded: sign * round_pr(total_excluded, this.currency.rounding),
            total_included: sign * round_pr(total_included, this.currency.rounding),
        };
    }

    /**
     * Taxes after fiscal position mapping.
     * @param {number[]} taxIds
     * @param {object | falsy} fpos - fiscal position
     * @returns {object[]}
     */
    get_taxes_after_fp(taxes, fpos) {
        if (!fpos) {
            return taxes;
        }
        const mappedTaxes = [];
        for (const tax of taxes) {
            if (tax) {
                const taxMaps = this.models["account.fiscal.position.tax"].filter(
                    (fposTax) =>
                        fposTax.tax_src_id.id === tax.id && fpos.id === fposTax.position_id.id
                );
                if (taxMaps.length) {
                    for (const taxMap of taxMaps) {
                        if (taxMap.tax_dest_id) {
                            const mappedTax = this.models["account.tax"].get(taxMap.tax_dest_id.id);
                            if (mappedTax) {
                                mappedTaxes.push(mappedTax);
                            }
                        }
                    }
                } else {
                    mappedTaxes.push(tax);
                }
            }
        }
        return uniqueBy(mappedTaxes, (tax) => tax.id);
    }

    /**
     * @param {str} terminalName
     */
    getPendingPaymentLine(terminalName) {
        return this.get_order().paymentlines.find(
            (paymentLine) =>
                paymentLine.payment_method.use_payment_terminal === terminalName &&
                !paymentLine.is_done()
        );
    }
    /**
     * TODO: We can probably remove this here and put it somewhere else.
     * And that somewhere else becomes the parent of the proxy.
     * Directly calls the requested service, instead of triggering a
     * 'call_service' event up, which wouldn't work as services have no parent
     *
     * @param {OdooEvent} ev
     */
    _trigger_up(ev) {
        if (ev.is_stopped()) {
            return;
        }
        const payload = ev.data;
        if (ev.name === "call_service") {
            const service = this.env.services[payload.service];
            const result = service[payload.method].apply(service, ev.data.args || []);
            payload.callback(result);
        }
    }

    isProductQtyZero(qty) {
        const dp = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit of Measure"
        );
        return floatIsZero(qty, dp);
    }

    disallowLineQuantityChange() {
        return false;
    }

    getCurrencySymbol() {
        return this.currency ? this.currency.symbol : "$";
    }
    isOpenOrderShareable() {
        return this.config.trusted_config_ids.length > 0;
    }
    switchPane() {
        this.mobile_pane = this.mobile_pane === "left" ? "right" : "left";
    }
    switchPaneTicketScreen() {
        this.ticket_screen_mobile_pane =
            this.ticket_screen_mobile_pane === "left" ? "right" : "left";
    }
    async logEmployeeMessage(action, message) {
        await this.data.call("pos.session", "log_partner_message", [
            this.session.id,
            this.user.partner_id.id,
            action,
            message,
        ]);
    }
    showScreen(name, props) {
        this.previousScreen = this.mainScreen.component?.name;
        const component = registry.category("pos_screens").get(name);
        this.mainScreen = { component, props };
        // Save the screen to the order so that it is shown again when the order is selected.
        if (component.storeOnOrder ?? true) {
            this.get_order()?.set_screen_data({ name, props });
        }
    }
    async printReceipt() {
        const isPrinted = await this.printer.print(
            OrderReceipt,
            {
                data: this.get_order().export_for_printing(),
                formatCurrency: this.env.utils.formatCurrency,
            },
            { webPrintFallback: true }
        );
        if (isPrinted) {
            this.get_order()._printed = true;
        }
    }

    // Now the printer should work in PoS without restaurant
    async sendOrderInPreparation(order, cancelled = false) {
        if (this.printers_category_ids_set.size) {
            try {
                const changes = order.changesToOrder(cancelled);

                if (changes.cancelled.length > 0 || changes.new.length > 0) {
                    const isPrintSuccessful = await order.printChanges(cancelled);
                    if (!isPrintSuccessful) {
                        this.dialog.add(AlertDialog, {
                            title: _t("Printing failed"),
                            body: _t("Failed in printing the changes in the order"),
                        });
                    }
                }
            } catch (e) {
                console.warn("Failed in printing the changes in the order", e);
            }
        }
    }
    async sendOrderInPreparationUpdateLastChange(order, cancelled = false) {
        await this.sendOrderInPreparation(order, cancelled);
        order.updateLastOrderChange();

        //We make sure that the last_order_change is updated in the backend
        order.save_to_db();
        order.pos.ordersToUpdateSet.add(order);
        await order.pos.sendDraftToServer();
    }
    closeScreen() {
        this.addOrderIfEmpty();
        const { name: screenName } = this.get_order().get_screen_data();
        this.showScreen(screenName);
    }

    addOrderIfEmpty() {
        if (!this.get_order()) {
            this.add_new_order();
        }
    }

    connectToProxy() {
        return new Promise((resolve, reject) => {
            this.barcodeReader?.disconnectFromProxy();
            this.loadingSkipButtonIsShown = true;
            this.hardwareProxy.autoconnect({ force_ip: this.config.proxy_ip }).then(
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

    async closePos() {
        const customerDisplayService = this.env.services.customer_display;
        if (customerDisplayService) {
            customerDisplayService.update({ closeUI: true });
        }

        // If pos is not properly loaded, we just go back to /web without
        // doing anything in the order data.
        if (!this || this.db.get_orders().length === 0) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }

        // If there are orders in the db left unsynced, we try to sync.
        const syncSuccess = await this.push_orders_with_closing_popup();
        if (syncSuccess) {
            window.location = '/web#action=point_of_sale.action_client_pos_menu';
        }
    }
    shouldShowNavbarButtons() {
        return true;
    }
    async selectPartner({ missingFields = [] } = {}) {
        // FIXME, find order to refund when we are in the ticketscreen.
        const currentOrder = this.get_order();
        if (!currentOrder) {
            return;
        }
        const currentPartner = currentOrder.get_partner();
        if (currentPartner && currentOrder.getHasRefundLines()) {
            this.dialog.add(AlertDialog, {
                title: _t("Can't change customer"),
                body: _t(
                    "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer.",
                    currentPartner.name
                ),
            });
            return;
        }
        this.dialog.add(PartnerList, {
            partner: currentPartner,
            missingFields,
            getPayload: (newPartner) => currentOrder.set_partner(newPartner),
        });
        return currentPartner;
    }
    // FIXME: POSREF, method exist only to be overrided
    async addProductFromUi(product, options) {
        return this.get_order().add_product(product, options);
    }
    async addProductToCurrentOrder(product, options = {}) {
        if (Number.isInteger(product)) {
            product = this.models["product.product"].get(product);
        }
        this.get_order() || this.add_new_order();

        options = { ...options, ...(await this.getAddProductOptions(product)) };

        if (!Object.keys(options).length) {
            return;
        }

        // Add the product after having the extra information.
        await this.addProductFromUi(product, options);
        this.numberBuffer.reset();
    }

    async getEditedPackLotLines(isAllowOnlyOneLot, packLotLinesToEdit, productName) {
        const payload = await makeAwaitable(this.dialog, EditListPopup, {
            title: _t("Lot/Serial Number(s) Required"),
            name: productName,
            isSingleItem: isAllowOnlyOneLot,
            array: packLotLinesToEdit,
        });
        if (!payload) {
            return;
        }
        // Segregate the old and new packlot lines
        const modifiedPackLotLines = Object.fromEntries(
            payload.filter((item) => item.id).map((item) => [item.id, item.text])
        );
        const newPackLotLines = payload
            .filter((item) => !item.id)
            .map((item) => ({ lot_name: item.text }));

        return { modifiedPackLotLines, newPackLotLines };
    }

    openCashControl() {
        if (this.shouldShowCashControl()) {
            this.dialog.add(
                CashOpeningPopup,
                {},
                {
                    onClose: () => {
                        if (this.session.state !== "opened") {
                            this.closePos();
                        }
                    },
                }
            );
        }
    }
    shouldShowCashControl() {
        return this.config.cash_control && this.session.state == "opening_control";
    }

    preloadImages() {
        for (const product of this.models["product.product"].getAll()) {
            const image = new Image();
            image.src = `/web/image?model=product.product&field=image_128&id=${product.id}&unique=${product.write_date}`;
        }
        for (const category of this.models["pos.category"].getAll()) {
            if (category.id == 0) {
                continue;
            }
            const image = new Image();
            image.src = `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
        }
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
            this.mainScreen.component === PaymentScreen ||
            (this.mainScreen.component === ProductScreen && this.mobile_pane == "left") ||
            this.mainScreen.component === TicketScreen
        );
    }

    doNotAllowRefundAndSales() {
        return false;
    }

    getReceiptHeaderData(order) {
        return {
            company: this.company,
            cashier: this.get_cashier()?.name,
            header: this.config.receipt_header,
        };
    }

    isChildPartner(partner) {
        return partner.parent_name;
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
        return new PosStore(env, deps).ready;
    },
};

registry.category("services").add("pos", posService);
