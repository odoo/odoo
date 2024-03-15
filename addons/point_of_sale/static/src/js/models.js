/** @odoo-module */
/* global waitForWebfonts */

import { PosDB } from "@point_of_sale/js/db";
import { formatFloat } from "@web/views/fields/formatters";
import { uuidv4, batched, deduceUrl } from "@point_of_sale/js/utils";
import { HWPrinter } from "@point_of_sale/app/printer/hw_printer";
// FIXME POSREF - unify use of native parseFloat and web's parseFloat. We probably don't need the native version.
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";
import { formatDate, formatDateTime, serializeDateTime } from "@web/core/l10n/dates";
import {
    roundDecimals as round_di,
    roundPrecision as round_pr,
    floatIsZero,
} from "@web/core/utils/numbers";
import { ErrorPopup } from "./Popups/ErrorPopup";
import { ProductConfiguratorPopup } from "@point_of_sale/js/Popups/ProductConfiguratorPopup";
import { EditListPopup } from "@point_of_sale/js/Popups/EditListPopup";
import { markRaw, reactive } from "@odoo/owl";
import { ConfirmPopup } from "@point_of_sale/js/Popups/ConfirmPopup";
import { sprintf } from "@web/core/utils/strings";
import { Mutex } from "@web/core/utils/concurrency";
import { memoize } from "@web/core/utils/functions";
import { _t } from "@web/core/l10n/translation";
import { renderToString, renderToElement } from "@web/core/utils/render";

const { DateTime } = luxon;

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

/**
 * If optimization is needed, then we should implement this
 * using a Balanced Binary Tree to behave like an Object and an Array.
 * But behaving like Object (indexed by cid) might not be
 * needed. Let's see how it turns out.
 */
class PosCollection extends Array {
    getByCID(cid) {
        return this.find((item) => item.cid == cid);
    }
    add(item) {
        this.push(item);
    }
    remove(item) {
        const index = this.findIndex((_item) => item.cid == _item.cid);
        if (index < 0) {
            return index;
        }
        this.splice(index, 1);
        return index;
    }
    reset() {
        this.length = 0;
    }
    at(index) {
        return this[index];
    }
}

let nextId = 0;
class PosModel {
    /**
     * Create an object with cid. If no cid is in the defaultObj,
     * cid is computed based on its id. Override _getCID if you
     * don't want this default calculation of cid.
     * @param {Object?} defaultObj its props copied to this instance.
     */
    constructor() {
        this.setup(...arguments);
    }
    // To be used by Model patches to patch constructor
    setup(defaultObj) {
        defaultObj = defaultObj || {};
        if (!defaultObj.cid) {
            defaultObj.cid = this._getCID(defaultObj);
        }
        Object.assign(this, defaultObj);
    }
    /**
     * Default cid getter. Used as local identity of this object.
     * @param {Object} obj
     */
    _getCID(obj) {
        if (obj.id) {
            if (typeof obj.id == "string") {
                return obj.id;
            } else if (typeof obj.id == "number") {
                return `c${obj.id}`;
            }
        }
        return `c${nextId++}`;
    }
}

export class PosGlobalState extends PosModel {
    setup() {
        super.setup(...arguments);

        this.db = new PosDB(); // a local database used to search trough products and categories & store pending orders
        this.unwatched = markRaw({});
        this.pushOrderMutex = new Mutex();

        // Business data; loaded from the server at launch
        this.company_logo = null;
        this.company_logo_base64 = "";
        this.currency = null;
        this.company = null;
        this.user = null;
        this.partners = [];
        this.taxes = [];
        this.pos_session = null;
        this.config = null;
        this.units = [];
        this.units_by_id = {};
        this.uom_unit_id = null;
        this.default_pricelist = null;
        this.order_sequence = 1;
        this.printers_category_ids_set = new Set();

        // Object mapping the order's name (which contains the uid) to it's server_id after
        // validation (order paid then sent to the backend).
        this.validated_orders_name_server_id_map = {};

        this.numpadMode = "quantity";

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
                selectedSyncedOrderId: null,
                searchDetails: this.getDefaultSearchDetails(),
                filter: null,
                // maps the order's backendId to it's selected orderline
                selectedOrderlineIds: {},
                highlightHeaderNote: false,
            },
        };

        this.ordersToUpdateSet = new Set(); // used to know which orders need to be sent to the back end when syncing
        this.loadingOrderState = false; // used to prevent orders fetched to be put in the update set during the reactive change
        this.tempScreenIsShown = false;

        // these dynamic attributes can be watched for change by other models or widgets
        Object.assign(this, {
            synch: { status: "connected", pending: 0 },
            orders: new PosCollection(),
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
    }
    getDefaultSearchDetails() {
        return {
            fieldName: "RECEIPT_NUMBER",
            searchTerm: "",
        };
    }
    async load_product_uom_unit() {
        const uom_id = await this.orm.call("ir.model.data", "check_object_reference", [
            "uom",
            "product_uom_unit",
        ]);
        this.uom_unit_id = uom_id[1];
    }

    async after_load_server_data() {
        await this.load_product_uom_unit();
        await this.load_orders();
        this.set_start_order();
        Object.assign(this.toRefundLines, this.db.load("TO_REFUND_LINES") || {});
        window.addEventListener("beforeunload", () =>
            this.db.save("TO_REFUND_LINES", this.toRefundLines)
        );
        const { start_category, iface_start_categ_id } = this.config;
        this.selectedCategoryId = (start_category && iface_start_categ_id?.[0]) || 0;
        this.hasBigScrollBars = this.config.iface_big_scrollbars;
        // Push orders in background, do not await
        this.push_orders();
        this.markReady();
    }

    async load_server_data() {
        const loadedData = await this.orm.silent.call("pos.session", "load_pos_data", [
            [odoo.pos_session_id],
        ]);
        await this._processData(loadedData);
        return this.after_load_server_data();
    }
    async _processData(loadedData) {
        this.version = loadedData["version"];
        this.company = loadedData["res.company"];
        this.dp = loadedData["decimal.precision"];
        this.units = loadedData["uom.uom"];
        this.units_by_id = loadedData["units_by_id"];
        this.states = loadedData["res.country.state"];
        this.countries = loadedData["res.country"];
        this.langs = loadedData["res.lang"];
        this.taxes = loadedData["account.tax"];
        this.taxes_by_id = loadedData["taxes_by_id"];
        this.pos_session = loadedData["pos.session"];
        this._loadPosSession();
        this.config = loadedData["pos.config"];
        this._loadPoSConfig();
        this.bills = loadedData["pos.bill"];
        this.partners = loadedData["res.partner"];
        this.addPartners(this.partners);
        this.picking_type = loadedData["stock.picking.type"];
        this.user = loadedData["res.users"];
        this.pricelists = loadedData["product.pricelist"];
        this.default_pricelist = loadedData["default_pricelist"];
        this.currency = loadedData["res.currency"];
        this.db.add_categories(loadedData["pos.category"]);
        this._loadProductProduct(loadedData["product.product"]);
        this.db.add_packagings(loadedData["product.packaging"]);
        this.attributes_by_ptal_id = loadedData["attributes_by_ptal_id"];
        this.cash_rounding = loadedData["account.cash.rounding"];
        this.payment_methods = loadedData["pos.payment.method"];
        this._loadPosPaymentMethod();
        this.fiscal_positions = loadedData["account.fiscal.position"];
        this.base_url = loadedData["base_url"];
        await this._loadPictures();
        await this._loadPosPrinters(loadedData["pos.printer"]);
    }
    _loadPosSession() {
        // We need to do it here, since only then the local storage has the correct uuid
        this.db.save("pos_session_id", this.pos_session.id);
        const orders = this.db.get_orders();
        const sequences = orders.map((order) => order.data.sequence_number + 1);
        this.pos_session.sequence_number = Math.max(this.pos_session.sequence_number, ...sequences);
        this.pos_session.login_number = odoo.login_number;
    }
    _loadPosPrinters(printers) {
        this.unwatched.printers = [];
        // list of product categories that belong to one or more order printer
        for (const printerConfig of printers) {
            const printer = this.create_printer(printerConfig);
            printer.config = printerConfig;
            this.unwatched.printers.push(printer);
            for (const id of printer.config.product_categories_ids) {
                this.printers_category_ids_set.add(id);
            }
        }
        this.config.iface_printers = !!this.unwatched.printers.length;
    }
    create_printer(config) {
        const url = deduceUrl(config.proxy_ip || "");
        return new HWPrinter({ rpc: this.env.services.rpc, url });
    }
    _loadPoSConfig() {
        this.db.set_uuid(this.config.uuid);
    }
    addPartners(partners) {
        return this.db.add_partners(partners);
    }
    _assignApplicableItems(pricelist, correspondingProduct, pricelistItem) {
        if (!(pricelist.id in correspondingProduct.applicablePricelistItems)) {
            correspondingProduct.applicablePricelistItems[pricelist.id] = [];
        }
        correspondingProduct.applicablePricelistItems[pricelist.id].push(pricelistItem);
    }
    _loadProductProduct(products) {
        const productMap = {};
        const productTemplateMap = {};

        const modelProducts = products.map((product) => {
            product.pos = this;
            product.applicablePricelistItems = {};
            productMap[product.id] = product;
            productTemplateMap[product.product_tmpl_id[0]] = (
                productTemplateMap[product.product_tmpl_id[0]] || []
            ).concat(product);
            return new Product(product);
        });

        for (const pricelist of this.pricelists) {
            for (const pricelistItem of pricelist.items) {
                if (pricelistItem.product_id) {
                    const product_id = pricelistItem.product_id[0];
                    const correspondingProduct = productMap[product_id];
                    if (correspondingProduct) {
                        this._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                    }
                } else if (pricelistItem.product_tmpl_id) {
                    const product_tmpl_id = pricelistItem.product_tmpl_id[0];
                    const correspondingProducts = productTemplateMap[product_tmpl_id];
                    for (const correspondingProduct of correspondingProducts || []) {
                        this._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                    }
                } else {
                    for (const correspondingProduct of products) {
                        this._assignApplicableItems(pricelist, correspondingProduct, pricelistItem);
                    }
                }
            }
        }
        this.db.add_products(modelProducts);
    }
    _loadPosPaymentMethod() {
        // need to do this for pos_iot due to reference, this is a temporary fix
        this.payment_methods_by_id = {};
        for (const pm of this.payment_methods) {
            this.payment_methods_by_id[pm.id] = pm;
            const PaymentInterface = this.electronic_payment_interfaces[pm.use_payment_terminal];
            if (PaymentInterface) {
                pm.payment_terminal = new PaymentInterface(this, pm);
            }
        }
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
    prepare_new_partners_domain() {
        return [["write_date", ">", this.db.get_partner_write_date()]];
    }

    // reload the list of partner, returns as a promise that resolves if there were
    // updated partners, and fails if not
    async load_new_partners() {
        const search_params = { domain: this.prepare_new_partners_domain() };
        // FIXME POSREF TIMEOUT 3000
        const partners = await this.orm.silent.call(
            "pos.session",
            "get_pos_ui_res_partner_by_params",
            [[odoo.pos_session_id], search_params]
        );
        return this.addPartners(partners);
    }

    setSelectedCategoryId(categoryId) {
        this.selectedCategoryId = categoryId;
    }

    /**
     * Remove the order passed in params from the list of orders
     * @param order
     */
    removeOrder(order, removeFromServer = true) {
        this.orders.remove(order);
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
        return this.makeOrderReactive(new Order({}, options));
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
        this.orders.add(order);
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
            if (json.pos_session_id === this.pos_session.id) {
                orders.push(this.createReactiveOrder(json));
            }
        }
        for (i = 0; i < jsons.length; i++) {
            json = jsons[i];
            if (
                json.pos_session_id !== this.pos_session.id &&
                (json.lines.length > 0 || json.statement_ids.length > 0)
            ) {
                orders.push(this.createReactiveOrder(json));
            } else if (json.pos_session_id !== this.pos_session.id) {
                this.db.remove_unpaid_order(jsons[i]);
            }
        }

        orders = orders.sort(function (a, b) {
            return a.sequence_number - b.sequence_number;
        });

        if (orders.length) {
            for (const order of orders) {
                this.orders.add(order);
            }
        }
        this.loadingOrderState = false;
    }
    async _loadMissingProducts(orders) {
        const missingProductIds = new Set([]);
        for (const order of orders) {
            for (const line of order.lines) {
                const productId = line[2].product_id;
                if (missingProductIds.has(productId)) {
                    continue;
                }
                if (!this.db.get_product_by_id(productId)) {
                    missingProductIds.add(productId);
                }
            }
        }
        if(!missingProductIds.size) return;
        const products = await this.orm.call(
            "pos.session",
            "get_pos_ui_product_product_by_params",
            [odoo.pos_session_id, { domain: [["id", "in", [...missingProductIds]]] }]
        );
        await this._loadMissingPricelistItems(products);
        this._loadProductProduct(products);
    }
    async _loadMissingPricelistItems(products) {
        if(!products.length) return;
        const product_tmpl_ids = products.map(product => product.product_tmpl_id[0]);
        const product_ids = products.map(product => product.id);

        const pricelistItems = await this.orm.call(
            'pos.session',
            'get_pos_ui_product_pricelist_item_by_product',
            [odoo.pos_session_id, product_tmpl_ids, product_ids]
        );

        // Merge the loaded pricelist items with the existing pricelists
        // Prioritizing the addition of newly loaded pricelist items to the start of the existing pricelists.
        // This ensures that the order reflects the desired priority of items in the pricelistItems array.
        // E.g. The order in the items should be: [product-pricelist-item, product-template-pricelist-item, category-pricelist-item, global-pricelist-item].
        // for reference check order of the Product Pricelist Item model
        for (const pricelist of this.pricelists) {
            const itemIds = new Set(pricelist.items.map(item => item.id));

            const _pricelistItems = pricelistItems.filter(item => {
                return item.pricelist_id[0] === pricelist.id && !itemIds.has(item.id);
            });
            pricelist.items = [..._pricelistItems, ...pricelist.items];
        }
    }
    // load the partners based on the ids
    async _loadPartners(partnerIds) {
        if (partnerIds.length > 0) {
            // FIXME POSREF TIMEOUT
            const fetchedPartners = await this.orm.silent.call(
                "pos.session",
                "get_pos_ui_res_partner_by_params",
                [[odoo.pos_session_id], { domain: [["id", "in", partnerIds]] }]
            );
            this.addPartners(fetchedPartners);
        }
    }
    async _loadMissingPartners(orders) {
        const missingPartnerIds = new Set([]);
        for (const order of orders) {
            const partnerId = order.partner_id;
            if (missingPartnerIds.has(partnerId)) {
                continue;
            }
            if (partnerId && !this.db.get_partner_by_id(partnerId)) {
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

        this.set_synch("connecting", removedOrdersIds.length);
        try {
            const removeOrdersResponseData = await this.orm.silent.call(
                "pos.order",
                "remove_from_ui",
                [removedOrdersIds]
            );
            this.set_synch("connected");
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
            this.orders.add(order);
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
        return await this.orm.call("pos.order", "get_draft_share_order_ids", [], {
            config_id: this.config.id,
        });
    }
    async _addPricelists(ordersJson) {
        const pricelistsToGet = [];
        ordersJson.forEach((order) => {
            let found = false;
            for (const pricelist of this.pricelists) {
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
            const pricelistsJson = await this._getPricelistJson(pricelistsToGet);
            message = this._addPosPricelists(pricelistsJson);
        }
        return message;
    }
    async _getPricelistJson(pricelistsToGet) {
        return await this.env.services.orm.call(
            "pos.session",
            "get_pos_ui_product_pricelists_by_ids",
            [[odoo.pos_session_id], pricelistsToGet]
        );
    }
    async _getMissingProducts(ordersJson) {
        const productIds = [];
        for (const order of ordersJson) {
            for (const orderline of order.lines) {
                if (!this.db.get_product_by_id(orderline[2].product_id)) {
                    productIds.push(orderline[2].product_id);
                }
            }
        }
        await this._addProducts(productIds, false);
    }
    _addPosPricelists(pricelistsJson) {
        if (!this.config.use_pricelist) {
            this.config.use_pricelist = true;
        }
        this.pricelists.push(...pricelistsJson);
        let message = "";
        const pricelistsNames = pricelistsJson.map((pricelist) => {
            return pricelist.display_name;
        });
        message = sprintf(
            _t("%s fiscal position(s) added to the configuration."),
            pricelistsNames.join(", ")
        );
        return message;
    }
    async _addFiscalPositions(ordersJson) {
        const fiscalPositionToGet = [];
        ordersJson.forEach((order) => {
            let found = false;
            for (const fp of this.fiscal_positions) {
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
            const fiscalPositionJson = await this._getFiscalPositionJson(fiscalPositionToGet);
            message = this._addPosFiscalPosition(fiscalPositionJson);
        }
        return message;
    }
    async _getFiscalPositionJson(fiscalPositionToGet) {
        return await this.env.services.orm.call(
            "pos.session",
            "get_pos_ui_account_fiscal_positions_by_ids",
            [[odoo.pos_session_id], fiscalPositionToGet]
        );
    }
    _addPosFiscalPosition(fiscalPositionJson) {
        this.fiscal_positions.push(...fiscalPositionJson);
        let message = "";
        const fiscalPositionNames = fiscalPositionJson.map((fp) => {
            return fp.display_name;
        });
        message = sprintf(
            _t("%s fiscal position(s) added to the configuration."),
            fiscalPositionNames.join(", ")
        );
        return message;
    }
    sortOrders() {
        this.orders.sort((a, b) => (a.name > b.name ? 1 : -1));
    }
    async getProductInfo(product, quantity) {
        const order = this.get_order();
        // check back-end method `get_product_info_pos` to see what it returns
        // We do this so it's easier to override the value returned and use it in the component template later
        const productInfo = await this.orm.call("product.product", "get_product_info_pos", [
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
        const closingData = await this.orm.call("pos.session", "get_closing_control_data", [
            [this.pos_session.id],
        ]);
        const ordersDetails = closingData.orders_details;
        const paymentsAmount = closingData.payments_amount;
        const payLaterAmount = closingData.pay_later_amount;
        const openingNotes = closingData.opening_notes;
        const defaultCashDetails = closingData.default_cash_details;
        const otherPaymentMethods = closingData.other_payment_methods;
        const isManager = closingData.is_manager;
        const amountAuthorizedDiff = closingData.amount_authorized_diff;
        const cashControl = this.config.cash_control;

        // component state and refs definition
        const state = { notes: "", acceptClosing: false, payments: {} };
        if (cashControl) {
            state.payments[defaultCashDetails.id] = {
                counted: 0,
                difference: -defaultCashDetails.amount,
                number: 0,
            };
        }
        if (otherPaymentMethods.length > 0) {
            otherPaymentMethods.forEach((pm) => {
                if (pm.type === "bank") {
                    state.payments[pm.id] = {
                        counted: this.env.utils.roundCurrency(pm.amount),
                        difference: 0,
                        number: pm.number,
                    };
                }
            });
        }
        return {
            ordersDetails,
            paymentsAmount,
            payLaterAmount,
            openingNotes,
            defaultCashDetails,
            otherPaymentMethods,
            isManager,
            amountAuthorizedDiff,
            state,
            cashControl,
        };
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

    computePriceAfterFp(price, taxes){
        const order = this.get_order();
        if(order && order.fiscal_position) {
            let mapped_included_taxes = [];
            let new_included_taxes = [];
            const self = this;
            _(taxes).each(function(tax) {
                const line_taxes = self.get_taxes_after_fp([tax.id], order.fiscal_position);
                if (line_taxes.length && line_taxes[0].price_include){
                    new_included_taxes = new_included_taxes.concat(line_taxes);
                }
                if(tax.price_include && !_.contains(line_taxes, tax)){
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
                    ).total_excluded
                    return this.compute_all(
                        new_included_taxes,
                        price_without_taxes,
                        1,
                        this.currency.rounding,
                        false
                    ).total_included
                }
                else{
                    return this.compute_all(
                        mapped_included_taxes,
                        price,
                        1,
                        this.currency.rounding,
                        true
                    ).total_excluded;
                }
            }
        }
        return price;
    }

    getTaxesByIds(taxIds) {
        let taxes = [];
        for (let i = 0; i < taxIds.length; i++) {
            if (this.taxes_by_id[taxIds[i]]) {
                taxes.push(this.taxes_by_id[taxIds[i]]);
            }
        }
        return taxes;
    }

    /**
     * Renders the HTML for the customer display and returns it as a string.
     *
     * @returns {string}
     */
    async customerDisplayHTML() {
        const order = this.get_order();
        if (!order) {
            return;
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

        return renderToString("CustomerFacingDisplayOrder", {
            pos: this,
            formatCurrency: this.env.utils.formatCurrency,
            origin: window.location.origin,
            order,
            productImages,
        });
    }
    
    // To be used in the context of closing the POS
    // Saves the order locally and try to send it to the backend.
    // If there is an error show a popup and ask to continue the closing or not
    async push_orders_with_closing_popup (order, opts) {
        try {
            await this.push_orders(order, opts);
            return Promise.resolve(true);
        } catch (error) {
            console.warn(error);
            const reason = this.failed
                ? _t(
                      'Some orders could not be submitted to ' +
                          'the server due to configuration errors. ' +
                          'You can exit the Point of Sale, but do ' +
                          'not close the session before the issue ' +
                          'has been resolved.'
                  )
                : _t(
                      'Some orders could not be submitted to ' +
                          'the server due to internet connection issues. ' +
                          'You can exit the Point of Sale, but do ' +
                          'not close the session before the issue ' +
                          'has been resolved.'
                  );
            const { confirmed } = await this.env.services.popup.add(ConfirmPopup, {
                title: _t('Offline Orders'),
                body: reason,
                confirmText: _t('Close anyway'),
                cancelText: _t('Do not close'),
            });
            return Promise.resolve(confirmed);
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
    _flush_orders(orders, options) {
        var self = this;

        return this._save_to_server(orders, options)
            .then(function (server_ids) {
                for (let i = 0; i < server_ids.length; i++) {
                    self.validated_orders_name_server_id_map[server_ids[i].pos_reference] =
                        server_ids[i].id;
                }
                return server_ids;
        })
        .catch(function(error) {
            if (self._isRPCError(error)) {
                if (orders.length > 1) {
                    return self._flush_orders_retry(orders, options);
                } else {
                    self.set_synch('error');
                    throw error;
                }
            } else {
                self.set_synch('disconnected');
                throw error;
            }
        })
        .finally(function() {
            self._after_flush_orders(orders);
        });
    }
    // Attempts to send the orders to the server one by one if an RPC error is encountered.
    async _flush_orders_retry(orders, options) {

        let successfulOrders = 0;
        let lastError;
        let serverIds = [];

        for (let order of orders) {
            try {
                let server_ids = await this._save_to_server([order], options);
                successfulOrders++;
                this.validated_orders_name_server_id_map[server_ids[0].pos_reference] = server_ids[0].id;
                serverIds.push(server_ids[0]);
            } catch (err) {
                lastError = err;
            }
        }

        if (successfulOrders === orders.length) {
            this.set_synch('connected');
            return serverIds;
        }
        if (this._isRPCError(lastError)) {
            this.set_synch('error');
        } else {
            this.set_synch('disconnected');
        }
        throw lastError;
    }
    _isRPCError(err) {
        return err.message && err.message.name === 'RPC_ERROR';
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
    set_synch(status, pending) {
        if (["connected", "connecting", "error", "disconnected"].indexOf(status) === -1) {
            console.error(status, " is not a known connection state.");
        }
        pending =
            pending || this.db.get_orders().length + this.db.get_ids_to_remove_from_server().length;
        this.synch = { status, pending };
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
        this.set_synch("connecting", orders.length);
        options = options || {};

        // Keep the order ids that are about to be sent to the
        // backend. In between create_from_ui and the success callback
        // new orders may have been added to it.
        var order_ids_to_sync = orders.map((o) => o.id);

        for (const order of orders) {
            order.to_invoice = options.to_invoice || false;
        }
        // we try to send the order. silent prevents a spinner if it takes too long. (unless we are sending an invoice,
        // then we want to notify the user that we are waiting on something )
        const orm = options.to_invoice ? this.orm : this.orm.silent;

        try {
            // FIXME POSREF timeout
            // const timeout = typeof options.timeout === "number" ? options.timeout : 30000 * orders.length;
            const serverIds = await orm.call("pos.order", "create_from_ui", [
                orders,
                options.draft || false,
            ]);

            for (const serverId of serverIds) {
                const order = this.env.services.pos.globalState.orders.find(
                    (order) => order.name === serverId.pos_reference
                );

                if (order) {
                    order.server_id = serverId.id;
                }
            }

            for (const order_id of order_ids_to_sync) {
                this.db.remove_order(order_id);
            }

            this.failed = false;
            this.set_synch("connected");
            return serverIds;
        } catch (error) {
            console.warn("Failed to send orders:", orders);
            if (error.code === 200) {
                // Business Logic Error, not a connection problem
                // Hide error if already shown before ...
                if ((!this.failed || options.show_error) && !options.to_invoice) {
                    this.failed = error;
                    this.set_synch("error");
                    throw error;
                }
            }
            this.set_synch("disconnected");
            throw error;
        }
    }

    // Exports the paid orders (the ones waiting for internet connection)
    export_paid_orders() {
        return JSON.stringify(
            {
                paid_orders: this.db.get_orders(),
                session: this.pos_session.name,
                session_id: this.pos_session.id,
                date: new Date().toUTCString(),
                version: this.version.server_version_info,
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
                session: this.pos_session.name,
                session_id: this.pos_session.id,
                date: new Date().toUTCString(),
                version: this.version.server_version_info,
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
                if (order.pos_session_id !== this.pos_session.id) {
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
                this.orders.add(orders);
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
            if (json.pos_session_id === this.pos_session.id) {
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
            this.orders.add(orders);
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
            _(taxes).each(function (tax) {
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
        var round_tax = company.tax_calculation_rounding_method != 'round_globally';

        var initial_currency_rounding = currency_rounding;
        if (!round_tax) {
            currency_rounding = currency_rounding * 0.00001;
        }

        // 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
        var recompute_base = function(base_amount, incl_tax_amounts){
            let fixed_amount = incl_tax_amounts.fixed_amount;
            let division_amount = 0.0;
            for(const [, tax_factor] of incl_tax_amounts.division_taxes){
                division_amount += tax_factor;
            }
            let percent_amount = 0.0;
            for(const [, tax_factor] of incl_tax_amounts.percent_taxes){
                percent_amount += tax_factor;
            }

            if(company.country && company.country.code === "IN"){
                let total_tax_amount = 0.0;
                for(const [i, tax_factor] of incl_tax_amounts.percent_taxes){
                    const tax_amount = round_pr(base_amount * tax_factor / (100 + percent_amount), currency_rounding);
                    total_tax_amount += tax_amount;
                    cached_tax_amounts[i] = tax_amount;
                    fixed_amount += tax_amount;
                }
                for(const [i,] of incl_tax_amounts.percent_taxes){
                    cached_base_amounts[i] = base - total_tax_amount;
                }
                percent_amount = 0.0;
            }

            Object.assign(incl_tax_amounts, {
                percent_taxes: [],
                division_taxes: [],
                fixed_amount: 0.0,
            });

            return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100;
        }

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
        }

        var cached_tax_amounts = {};
        var cached_base_amounts = {};
        let is_base_affected = true;
        if (handle_price_include){
            _(taxes.reverse()).each(function(tax){
                if(tax.include_base_amount && is_base_affected){
                    base = recompute_base(base, incl_tax_amounts);
                    store_included_tax_total = true;
                }
                if(tax.price_include){
                    if(tax.amount_type === 'percent')
                        incl_tax_amounts.percent_taxes.push([i, tax.amount * tax.sum_repartition_factor]);
                    else if(tax.amount_type === 'division')
                        incl_tax_amounts.division_taxes.push([i, tax.amount * tax.sum_repartition_factor]);
                    else if(tax.amount_type === 'fixed')
                        incl_tax_amounts.fixed_amount += Math.abs(quantity) * tax.amount * tax.sum_repartition_factor;
                    else{
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
                is_base_affected = tax.is_base_affected;
            });
        }

        var total_excluded = round_pr(recompute_base(base, incl_tax_amounts), initial_currency_rounding);
        var total_included = total_excluded;

        // 4) Iterate the taxes in the sequence order to fill missing base/amount values.

        base = total_excluded;

        var skip_checkpoint = false;

        var taxes_vals = [];
        i = 0;
        var cumulated_tax_included_amount = 0;
        _(taxes.reverse()).each(function(tax) {
            if(tax.price_include && i in cached_base_amounts) {
                var tax_base_amount = cached_base_amounts[i];
            } else if(tax.price_include || tax.is_base_affected) {
                var tax_base_amount = base;
            } else {
                tax_base_amount = total_excluded;
            }

            if(tax.price_include && cached_tax_amounts.hasOwnProperty(i)){
                var tax_amount = cached_tax_amounts[i];
            }else if(!skip_checkpoint && tax.price_include && total_included_checkpoints[i] !== undefined){
                var tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount);
                cumulated_tax_included_amount = 0;
            }else{
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

            taxes_vals.push({
                id: tax.id,
                name: tax.name,
                amount: sign * factorized_tax_amount,
                base: sign * round_pr(tax_base_amount, currency_rounding),
            });

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
    get_taxes_after_fp(taxIds, fpos) {
        if (!fpos) {
            return taxIds.map((taxId) => this.taxes_by_id[taxId]);
        }
        const mappedTaxes = [];
        for (const taxId of taxIds) {
            const tax = this.taxes_by_id[taxId];
            if (tax) {
                const taxMaps = Object.values(fpos.fiscal_position_taxes_by_id).filter(
                    (fposTax) => fposTax.tax_src_id[0] === tax.id
                );
                if (taxMaps.length) {
                    for (const taxMap of taxMaps) {
                        if (taxMap.tax_dest_id) {
                            const mappedTax = this.taxes_by_id[taxMap.tax_dest_id[0]];
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
            let args = payload.args || [];
            if (payload.service === "ajax" && payload.method === "rpc") {
                // ajax service uses an extra 'target' argument for rpc
                args = args.concat(ev.target);
            }
            const service = this.env.services[payload.service];
            const result = service[payload.method].apply(service, args);
            payload.callback(result);
        }
    }

    isProductQtyZero(qty) {
        return floatIsZero(qty, this.dp["Product Unit of Measure"]);
    }

    disallowLineQuantityChange() {
        return false;
    }

    getCurrencySymbol() {
        return this.currency ? this.currency.symbol : "$";
    }
    /**
     * Make the products corresponding to the given ids to be available_in_pos and
     * fetch them to be added on the loaded products.
     */
    async _addProducts(ids, setAvailable = true) {
        if (setAvailable) {
            await this.orm.write("product.product", ids, { available_in_pos: true });
        }
        const product = await this.orm.call("pos.session", "get_pos_ui_product_product_by_params", [
            odoo.pos_session_id,
            { domain: [["id", "in", ids]] },
        ]);
        await this._loadMissingPricelistItems(product);
        this._loadProductProduct(product);
    }
    isOpenOrderShareable() {
        return this.config.trusted_config_ids.length > 0;
    }
    doNotAllowRefundAndSales() {
        return false;
    }
}
PosGlobalState.prototype.electronic_payment_interfaces = {};

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
    PosGlobalState.prototype.electronic_payment_interfaces[use_payment_terminal] =
        ImplementedPaymentInterface;
}

export class Product extends PosModel {
    constructor(obj) {
        super(obj);
        this.parent_category_ids = [];
        let category = this.categ.parent;
        while (category) {
            this.parent_category_ids.push(category.id);
            category = category.parent;
        }
    }
    isAllowOnlyOneLot() {
        const productUnit = this.get_unit();
        return this.tracking === "lot" || !productUnit || !productUnit.is_pos_groupable;
    }
    get_unit() {
        var unit_id = this.uom_id;
        if (!unit_id) {
            return undefined;
        }
        unit_id = unit_id[0];
        if (!this.pos) {
            return undefined;
        }
        return this.pos.units_by_id[unit_id];
    }
    async _onScaleNotAvailable() {}
    get isScaleAvailable() {
        return true;
    }
    async getAddProductOptions(code) {
        let price_extra = 0.0;
        let draftPackLotLines, weight, description, packLotLinesToEdit;

        if (this.attribute_line_ids.some((id) => id in this.pos.attributes_by_ptal_id)) {
            let { confirmed, payload } = await this._openProductConfiguratorPopup();

            if (confirmed) {
                description = payload.selected_attributes.join(", ");
                price_extra += payload.price_extra;
            } else {
                return;
            }
        }
        // Gather lot information if required.
        if (
            ["serial", "lot"].includes(this.tracking) &&
            (this.pos.picking_type.use_create_lots || this.pos.picking_type.use_existing_lots)
        ) {
            const isAllowOnlyOneLot = this.isAllowOnlyOneLot();
            if (isAllowOnlyOneLot) {
                packLotLinesToEdit = [];
            } else {
                const orderline = this.pos.selectedOrder
                    .get_orderlines()
                    .filter((line) => !line.get_discount())
                    .find((line) => line.product.id === this.id);
                if (orderline) {
                    packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                } else {
                    packLotLinesToEdit = [];
                }
            }
            // if the lot information exists in the barcode, we don't need to ask it from the user.
            if (code && code.type === 'lot') {
                // consider the old and new packlot lines
                const modifiedPackLotLines = Object.fromEntries(
                    packLotLinesToEdit.filter(item => item.id).map(item => [item.id, item.text])
                );
                const newPackLotLines = [
                    { lot_name: code.code },
                ];
                draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
            } else {
                const { confirmed, payload } = await this.pos.env.services.popup.add(EditListPopup, {
                    title: this.pos.env._t("Lot/Serial Number(s) Required"),
                    name: this.display_name,
                    isSingleItem: isAllowOnlyOneLot,
                    array: packLotLinesToEdit,
                });
                if (confirmed) {
                    // Segregate the old and new packlot lines
                    const modifiedPackLotLines = Object.fromEntries(
                        payload.newArray.filter((item) => item.id).map((item) => [item.id, item.text])
                    );
                    const newPackLotLines = payload.newArray
                        .filter((item) => !item.id)
                        .map((item) => ({ lot_name: item.text }));

                    draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                } else {
                    // We don't proceed on adding product.
                    return;
                }
            }

        }

        // Take the weight if necessary.
        if (this.to_weight && this.pos.config.iface_electronic_scale) {
            // Show the ScaleScreen to weigh the product.
            if (this.isScaleAvailable) {
                const product = this;
                const { confirmed, payload } = await this.pos.env.services.pos.showTempScreen(
                    "ScaleScreen",
                    {
                        product,
                    }
                );
                if (confirmed) {
                    weight = payload.weight;
                } else {
                    // do not add the product;
                    return;
                }
            } else {
                await this._onScaleNotAvailable();
            }
        }

        if (code && this.pos.db.product_packaging_by_barcode[code.code]) {
            weight = this.pos.db.product_packaging_by_barcode[code.code].qty;
        }

        return { draftPackLotLines, quantity: weight, description, price_extra };
    }
    async _openProductConfiguratorPopup() {
        const attributes = this.attribute_line_ids
            .map((id) => this.pos.attributes_by_ptal_id[id])
            .filter((attr) => attr !== undefined);

        // avoid opening the popup when each attribute has only one available option.
        if (_.some(attributes, (attribute) => attribute.values.length > 1 || _.some(attribute.values, (value) => value.is_custom))) {
            return await this.pos.env.services.popup.add(
                ProductConfiguratorPopup,
                {
                    product: this,
                    attributes: attributes,
                }
            );
        };

        let selected_attributes = [];
        let price_extra = 0.0;

        attributes.forEach((attribute) => {
            selected_attributes.push(attribute.values[0].name);
            price_extra += attribute.values[0].price_extra;
        });

        return {
            confirmed: true,
            payload: {
                selected_attributes,
                price_extra,
            }
        };
    }
    isPricelistItemUsable(item, date) {
        const categories = this.parent_category_ids.concat(this.categ.id);
        return (
            (!item.categ_id || categories.includes(item.categ_id[0])) &&
            (!item.date_start || moment.utc(item.date_start).isSameOrBefore(date)) &&
            (!item.date_end || moment.utc(item.date_end).isSameOrAfter(date))
        );
    }
    // Port of _get_product_price on product.pricelist.
    //
    // Anything related to UOM can be ignored, the POS will always use
    // the default UOM set on the product and the user cannot change
    // it.
    //
    // Pricelist items do not have to be sorted. All
    // product.pricelist.item records are loaded with a search_read
    // and were automatically sorted based on their _order by the
    // ORM. After that they are added in this order to the pricelists.
    get_price(pricelist, quantity, price_extra = 0, recurring = false) {
        var date = moment();

        // In case of nested pricelists, it is necessary that all pricelists are made available in
        // the POS. Display a basic alert to the user in the case where there is a pricelist item
        // but we can't load the base pricelist to get the price when calling this method again.
        // As this method is also call without pricelist available in the POS, we can't just check
        // the absence of pricelist.
        if (recurring && !pricelist) {
            alert(
                _t(
                    "An error occurred when loading product prices. " +
                        "Make sure all pricelists are available in the POS."
                )
            );
        }

        const rules = !pricelist
            ? []
            : (this.applicablePricelistItems[pricelist.id] || []).filter((item) =>
                  this.isPricelistItemUsable(item, date)
              );

        let price = this.lst_price + (price_extra || 0);
        const rule = rules.find((rule) => !rule.min_quantity || quantity >= rule.min_quantity);
        if (!rule) {
            return price;
        }

        if (rule.base === "pricelist") {
            const base_pricelist = this.pos.pricelists.find(
                (pricelist) => pricelist.id === rule.base_pricelist_id[0]
            );
            if (base_pricelist) {
                price = this.get_price(base_pricelist, quantity, 0, true);
            }
        } else if (rule.base === "standard_price") {
            price = this.standard_price;
        }

        if (rule.compute_price === "fixed") {
            price = rule.fixed_price;
        } else if (rule.compute_price === "percentage") {
            price = price - price * (rule.percent_price / 100);
        } else {
            var price_limit = price;
            price -= price * (rule.price_discount / 100);
            if (rule.price_round) {
                price = round_pr(price, rule.price_round);
            }
            if (rule.price_surcharge) {
                price += rule.price_surcharge;
            }
            if (rule.price_min_margin) {
                price = Math.max(price, price_limit + rule.price_min_margin);
            }
            if (rule.price_max_margin) {
                price = Math.min(price, price_limit + rule.price_max_margin);
            }
        }

        // This return value has to be rounded with round_di before
        // being used further. Note that this cannot happen here,
        // because it would cause inconsistencies with the backend for
        // pricelist that have base == 'pricelist'.
        return price;
    }
    get_display_price(pricelist, quantity) {
        const order = this.pos.get_order();
        const taxes = this.pos.get_taxes_after_fp(
            this.taxes_id, 
            order && order.fiscal_position
        );
        const currentTaxes = this.pos.getTaxesByIds(this.taxes_id);
        const priceAfterFp = this.pos.computePriceAfterFp(
            this.get_price(pricelist, quantity), 
            currentTaxes
        );
        const allPrices = this.pos.compute_all(
            taxes,
            priceAfterFp,
            1,
            this.pos.currency.rounding
        );
        if (this.pos.config.iface_tax_included === 'total') {
            return allPrices.total_included;
        } else {
            return allPrices.total_excluded;
        }
    }
}

var orderline_id = 1;

// An orderline represent one element of the content of a customer's shopping cart.
// An orderline contains a product, its quantity, its price, discount. etc.
// An Order contains zero or more Orderlines.
export class Orderline extends PosModel {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.pos = options.pos;
        this.order = options.order;
        this.price_manually_set = options.price_manually_set || false;
        this.uuid = this.uuid || uuidv4();

        this.price_automatically_set = options.price_automatically_set || false;
        if (options.json) {
            try {
                this.init_from_JSON(options.json);
            } catch {
                console.error(
                    "ERROR: attempting to recover product ID",
                    options.json.product_id[0],
                    "not available in the point of sale. Correct the product or clean the browser cache."
                );
            }
            return;
        }
        this.product = options.product;
        this.tax_ids = options.tax_ids;
        this.set_product_lot(this.product);
        this.set_quantity(1);
        this.discount = 0;
        this.note = "";
        this.hasChange = false;
        this.skipChange = false;
        this.discountStr = "0";
        this.selected = false;
        this.description = "";
        this.price_extra = 0;
        this.full_product_name = options.description || "";
        this.id = orderline_id++;
        this.customerNote = this.customerNote || "";
        this.saved_quantity = 0;

        if (options.price) {
            this.set_unit_price(options.price);
        } else {
            this.set_unit_price(this.product.get_price(this.order.pricelist, this.get_quantity()));
        }
    }
    init_from_JSON(json) {
        this.product = this.pos.db.get_product_by_id(json.product_id);
        this.set_product_lot(this.product);
        this.price = json.price_unit;
        this.price_manually_set = json.price_manually_set;
        this.price_automatically_set = json.price_automatically_set;
        this.set_discount(json.discount);
        this.set_quantity(json.qty, "do not recompute unit price");
        this.set_description(json.description);
        this.set_price_extra(json.price_extra);
        this.set_full_product_name(json.full_product_name);
        this.id = json.id ? json.id : orderline_id++;
        orderline_id = Math.max(this.id + 1, orderline_id);
        var pack_lot_lines = json.pack_lot_ids;
        for (var i = 0; i < pack_lot_lines.length; i++) {
            var packlotline = pack_lot_lines[i][2];
            var pack_lot_line = new Packlotline({}, { json: { ...packlotline, order_line: this } });
            this.pack_lot_lines.add(pack_lot_line);
        }
        this.tax_ids = json.tax_ids && json.tax_ids.length !== 0 ? json.tax_ids[0][2] : undefined;
        this.set_customer_note(json.customer_note);
        this.refunded_qty = json.refunded_qty;
        this.refunded_orderline_id = json.refunded_orderline_id;
        this.saved_quantity = json.qty;
        this.uuid = json.uuid;
        this.skipChange = json.skip_change;
    }
    clone() {
        var orderline = new Orderline(
            {},
            {
                pos: this.pos,
                order: this.order,
                product: this.product,
                price: this.price,
            }
        );
        orderline.order = null;
        orderline.quantity = this.quantity;
        orderline.quantityStr = this.quantityStr;
        orderline.discount = this.discount;
        orderline.price = this.price;
        orderline.selected = false;
        orderline.price_manually_set = this.price_manually_set;
        orderline.price_automatically_set = this.price_automatically_set;
        orderline.customerNote = this.customerNote;
        return orderline;
    }
    getPackLotLinesToEdit(isAllowOnlyOneLot) {
        const currentPackLotLines = this.pack_lot_lines;
        let nExtraLines = Math.abs(this.quantity) - currentPackLotLines.length;
        nExtraLines = Math.ceil(nExtraLines);
        nExtraLines = nExtraLines > 0 ? nExtraLines : 1;
        const tempLines = currentPackLotLines
            .map((lotLine) => ({
                id: lotLine.cid,
                text: lotLine.lot_name,
            }))
            .concat(
                Array.from(Array(nExtraLines)).map((_) => ({
                    text: "",
                }))
            );
        return isAllowOnlyOneLot ? [tempLines[0]] : tempLines;
    }
    /**
     * @param { modifiedPackLotLines, newPackLotLines }
     *    @param {Object} modifiedPackLotLines key-value pair of String (the cid) & String (the new lot_name)
     *    @param {Array} newPackLotLines array of { lot_name: String }
     */
    setPackLotLines({ modifiedPackLotLines, newPackLotLines , setQuantity = true }) {
        // Set the new values for modified lot lines.
        const lotLinesToRemove = [];
        for (const lotLine of this.pack_lot_lines) {
            const modifiedLotName = modifiedPackLotLines[lotLine.cid];
            if (modifiedLotName) {
                lotLine.lot_name = modifiedLotName;
            } else {
                // We should not call lotLine.remove() here because
                // we don't want to mutate the array while looping thru it.
                lotLinesToRemove.push(lotLine);
            }
        }

        // Remove those that needed to be removed.
        for (const lotLine of lotLinesToRemove) {
            this.pack_lot_lines.remove(lotLine);
        }

        // Create new pack lot lines.
        let newPackLotLine;
        for (const newLotLine of newPackLotLines) {
            newPackLotLine = new Packlotline({}, { order_line: this });
            newPackLotLine.lot_name = newLotLine.lot_name;
            this.pack_lot_lines.add(newPackLotLine);
        }

        // Set the quantity of the line based on number of pack lots.
        if (!this.product.to_weight && setQuantity) {
            this.set_quantity_by_lot();
        }
    }
    set_product_lot(product) {
        this.has_product_lot = product.tracking !== "none";
        this.pack_lot_lines = this.has_product_lot && new PosCollection();
    }
    getNote() {
        return this.note;
    }
    setNote(note) {
        this.note = note;
    }
    toggleSkipChange() {
        if (this.hasChange || this.skipChange) {
            this.skipChange = !this.skipChange;
        }
    }
    setHasChange(isChange) {
        this.hasChange = isChange;
    }
    // sets a discount [0,100]%
    set_discount(discount) {
        var parsed_discount =
            typeof discount === "number"
                ? discount
                : isNaN(parseFloat(discount))
                ? 0
                : oParseFloat("" + discount);
        var disc = Math.min(Math.max(parsed_discount || 0, 0), 100);
        this.discount = disc;
        this.discountStr = "" + disc;
    }
    // returns the discount [0,100]%
    get_discount() {
        return this.discount;
    }
    get_discount_str() {
        return this.discountStr;
    }
    set_description(description) {
        this.description = description || "";
    }
    set_price_extra(price_extra) {
        this.price_extra = parseFloat(price_extra) || 0.0;
    }
    set_full_product_name(full_product_name) {
        this.full_product_name = full_product_name || "";
    }
    get_price_extra() {
        return this.price_extra;
    }
    updateSavedQuantity() {
        this.saved_quantity = this.quantity;
    }
    // sets the quantity of the product. The quantity will be rounded according to the
    // product's unity of measure properties. Quantities greater than zero will not get
    // rounded to zero
    // Return true if successfully set the quantity, otherwise, return false.
    set_quantity(quantity, keep_price) {
        this.order.assert_editable();
        if (quantity === "remove") {
            if (this.refunded_orderline_id in this.pos.toRefundLines) {
                delete this.pos.toRefundLines[this.refunded_orderline_id];
            }
            this.order.remove_orderline(this);
            return true;
        } else {
            var quant =
                typeof quantity === "number"
                    ? quantity
                    : oParseFloat("" + (quantity ? quantity : 0));
            if (this.refunded_orderline_id in this.pos.toRefundLines) {
                const toRefundDetail = this.pos.toRefundLines[this.refunded_orderline_id];
                const maxQtyToRefund =
                    toRefundDetail.orderline.qty - toRefundDetail.orderline.refundedQty;
                if (quant > 0) {
                    this.pos.env.services.popup.add(ErrorPopup, {
                        title: _t("Positive quantity not allowed"),
                        body: _t(
                            "Only a negative quantity is allowed for this refund line. Click on +/- to modify the quantity to be refunded."
                        ),
                    });
                    return false;
                } else if (quant == 0) {
                    toRefundDetail.qty = 0;
                } else if (-quant <= maxQtyToRefund) {
                    toRefundDetail.qty = -quant;
                } else {
                    this.pos.env.services.popup.add(ErrorPopup, {
                        title: _t("Greater than allowed"),
                        body: sprintf(
                            _t(
                                "The requested quantity to be refunded is higher than the refundable quantity of %s."
                            ),
                            this.pos.env.utils.formatProductQty(maxQtyToRefund)
                        ),
                    });
                    return false;
                }
            }
            var unit = this.get_unit();
            if (unit) {
                if (unit.rounding) {
                    var decimals = this.pos.dp["Product Unit of Measure"];
                    var rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
                    this.quantity = round_pr(quant, rounding);
                    this.quantityStr = formatFloat(this.quantity, {
                        digits: [69, decimals],
                    });
                } else {
                    this.quantity = round_pr(quant, 1);
                    this.quantityStr = this.quantity.toFixed(0);
                }
            } else {
                this.quantity = quant;
                this.quantityStr = "" + this.quantity;
            }
        }

        // just like in sale.order changing the quantity will recompute the unit price
        if (!keep_price && !(this.price_manually_set || this.price_automatically_set)) {
            this.set_unit_price(
                this.product.get_price(
                    this.order.pricelist,
                    this.get_quantity(),
                    this.get_price_extra()
                )
            );
            this.order.fix_tax_included_price(this);
        }
        return true;
    }
    // return the quantity of product
    get_quantity() {
        return this.quantity;
    }
    get_quantity_str() {
        return this.quantityStr;
    }
    get_quantity_str_with_unit() {
        var unit = this.get_unit();
        if (unit && !unit.is_pos_groupable) {
            return this.quantityStr + " " + unit.name;
        } else {
            return this.quantityStr;
        }
    }

    get_lot_lines() {
        return this.pack_lot_lines && this.pack_lot_lines;
    }

    get_required_number_of_lots() {
        var lots_required = 1;

        if (this.product.tracking == "serial") {
            lots_required = Math.abs(this.quantity);
        }

        return lots_required;
    }

    get_valid_lots() {
        return this.pack_lot_lines.filter((item) => {
            return item.lot_name;
        });
    }

    set_quantity_by_lot() {
        var valid_lots_quantity = this.get_valid_lots().length;
        if (this.quantity < 0) {
            valid_lots_quantity = -valid_lots_quantity;
        }
        this.set_quantity(valid_lots_quantity);
    }

    has_valid_product_lot() {
        if (!this.has_product_lot) {
            return true;
        }
        var valid_product_lot = this.get_valid_lots();
        return this.get_required_number_of_lots() === valid_product_lot.length;
    }

    // return the unit of measure of the product
    get_unit() {
        return this.product.get_unit();
    }
    // return the product of this orderline
    get_product() {
        return this.product;
    }
    get_full_product_name() {
        if (this.full_product_name) {
            return this.full_product_name;
        }
        var full_name = this.product.display_name;
        if (this.description) {
            full_name += ` (${this.description})`;
        }
        return full_name;
    }
    // selects or deselects this orderline
    set_selected(selected) {
        this.selected = selected;
        // this trigger also triggers the change event of the collection.
    }
    // returns true if this orderline is selected
    is_selected() {
        return this.selected;
    }
    // when we add an new orderline we want to merge it with the last line to see reduce the number of items
    // in the orderline. This returns true if it makes sense to merge the two
    can_be_merged_with(orderline) {
        var price = parseFloat(
            round_di(this.price || 0, this.pos.dp["Product Price"]).toFixed(
                this.pos.dp["Product Price"]
            )
        );
        var order_line_price = orderline
            .get_product()
            .get_price(orderline.order.pricelist, this.get_quantity());
        order_line_price = round_di(
            orderline.compute_fixed_price(order_line_price),
            this.pos.currency.decimal_places
        );
        // only orderlines of the same product can be merged
        return (
            !this.skipChange &&
            orderline.getNote() === this.getNote() &&
            this.get_product().id === orderline.get_product().id &&
            this.get_unit() &&
            this.get_unit().is_pos_groupable &&
            // don't merge discounted orderlines
            this.get_discount() === 0 &&
            floatIsZero(
                price - order_line_price - orderline.get_price_extra(),
                this.pos.currency.decimal_places
            ) &&
            !(
                this.product.tracking === "lot" &&
                (this.pos.picking_type.use_create_lots || this.pos.picking_type.use_existing_lots)
            ) &&
            this.description === orderline.description &&
            orderline.get_customer_note() === this.get_customer_note() &&
            !this.refunded_orderline_id
        );
    }
    merge(orderline) {
        this.order.assert_editable();
        this.set_quantity(this.get_quantity() + orderline.get_quantity());
    }
    export_as_JSON() {
        var pack_lot_ids = [];
        if (this.has_product_lot) {
            this.pack_lot_lines.forEach((item) => {
                return pack_lot_ids.push([0, 0, item.export_as_JSON()]);
            });
        }
        return {
            uuid: this.uuid,
            skip_change: this.skipChange,
            qty: this.get_quantity(),
            price_unit: this.get_unit_price(),
            price_subtotal: this.get_price_without_tax(),
            price_subtotal_incl: this.get_price_with_tax(),
            discount: this.get_discount(),
            product_id: this.get_product().id,
            tax_ids: [[6, false, this.get_applicable_taxes().map((tax) => tax.id)]],
            id: this.id,
            pack_lot_ids: pack_lot_ids,
            description: this.description,
            full_product_name: this.get_full_product_name(),
            price_extra: this.get_price_extra(),
            customer_note: this.get_customer_note(),
            refunded_orderline_id: this.refunded_orderline_id,
            price_manually_set: this.price_manually_set,
            price_automatically_set: this.price_automatically_set,
        };
    }
    //used to create a json of the ticket, to be sent to the printer
    export_for_printing() {
        return {
            id: this.id,
            quantity: this.get_quantity(),
            unit_name: this.get_unit().name,
            is_in_unit: this.get_unit().id == this.pos.uom_unit_id,
            price: this.get_unit_display_price(),
            discount: this.get_discount(),
            product_name: this.get_product().display_name,
            product_name_wrapped: this.generate_wrapped_product_name(),
            price_lst: this.get_taxed_lst_unit_price(),
            fixed_lst_price: this.get_fixed_lst_price(),
            price_manually_set: this.price_manually_set,
            price_automatically_set: this.price_automatically_set,
            display_discount_policy: this.display_discount_policy(),
            price_display_one: this.get_display_price_one(),
            price_display: this.get_display_price(),
            price_with_tax: this.get_price_with_tax(),
            price_without_tax: this.get_price_without_tax(),
            price_with_tax_before_discount: this.get_price_with_tax_before_discount(),
            tax: this.get_tax(),
            product_description: this.get_product().description,
            product_description_sale: this.get_product().description_sale,
            pack_lot_lines: this.get_lot_lines(),
            customer_note: this.get_customer_note(),
            taxed_lst_unit_price: this.get_taxed_lst_unit_price(),
            unitDisplayPriceBeforeDiscount: this.getUnitDisplayPriceBeforeDiscount(),
        };
    }
    generate_wrapped_product_name() {
        var MAX_LENGTH = 24; // 40 * line ratio of .6
        var wrapped = [];
        var name = this.get_full_product_name();
        var current_line = "";

        while (name.length > 0) {
            var space_index = name.indexOf(" ");

            if (space_index === -1) {
                space_index = name.length;
            }

            if (current_line.length + space_index > MAX_LENGTH) {
                if (current_line.length) {
                    wrapped.push(current_line);
                }
                current_line = "";
            }

            current_line += name.slice(0, space_index + 1);
            name = name.slice(space_index + 1);
        }

        if (current_line.length) {
            wrapped.push(current_line);
        }

        return wrapped;
    }
    // changes the base price of the product for this orderline
    set_unit_price(price) {
        this.order.assert_editable();
        var parsed_price = !isNaN(price)
            ? price
            : isNaN(parseFloat(price))
            ? 0
            : oParseFloat("" + price);
        this.price = round_di(parsed_price || 0, this.pos.dp["Product Price"]);
    }
    get_unit_price() {
        var digits = this.pos.dp["Product Price"];
        // round and truncate to mimic _symbol_set behavior
        return parseFloat(round_di(this.price || 0, digits).toFixed(digits));
    }
    get_unit_display_price() {
        if (this.pos.config.iface_tax_included === "total") {
            return this.get_all_prices(1).priceWithTax;
        } else {
            return this.get_all_prices(1).priceWithoutTax;
        }
    }
    getUnitDisplayPriceBeforeDiscount(){
        if (this.pos.config.iface_tax_included === 'total') {
            return this.get_all_prices(1).priceWithTaxBeforeDiscount;
        } else {
            return this.get_all_prices(1).priceWithoutTaxBeforeDiscount;
        }
    }
    get_base_price() {
        var rounding = this.pos.currency.rounding;
        return round_pr(
            this.get_unit_price() * this.get_quantity() * (1 - this.get_discount() / 100),
            rounding
        );
    }
    get_display_price_one() {
        var rounding = this.pos.currency.rounding;
        var price_unit = this.get_unit_price();
        if (this.pos.config.iface_tax_included !== "total") {
            return round_pr(price_unit * (1.0 - this.get_discount() / 100.0), rounding);
        } else {
            var product = this.get_product();
            var taxes_ids = this.tax_ids || product.taxes_id;
            var product_taxes = this.pos.get_taxes_after_fp(taxes_ids, this.order.fiscal_position);
            var all_taxes = this.compute_all(
                product_taxes,
                price_unit,
                1,
                this.pos.currency.rounding
            );

            return round_pr(all_taxes.total_included * (1 - this.get_discount() / 100), rounding);
        }
    }
    get_display_price() {
        if (this.pos.config.iface_tax_included === "total") {
            return this.get_price_with_tax();
        } else {
            return this.get_price_without_tax();
        }
    }
    get_taxed_lst_unit_price(){
        const lstPrice = this.compute_fixed_price(this.get_lst_price());
        const product =  this.get_product();
        const taxesIds = product.taxes_id;
        const productTaxes = this.pos.get_taxes_after_fp(taxesIds, this.order.fiscal_position);
        const unitPrices =  this.compute_all(productTaxes, lstPrice, 1, this.pos.currency.rounding);
        if (this.pos.config.iface_tax_included === 'total') {
            return unitPrices.total_included;
        } else {
            return unitPrices.total_excluded;
        }
    }
    get_price_without_tax() {
        return this.get_all_prices().priceWithoutTax;
    }
    get_price_with_tax() {
        return this.get_all_prices().priceWithTax;
    }
    get_price_with_tax_before_discount() {
        return this.get_all_prices().priceWithTaxBeforeDiscount;
    }
    get_tax() {
        return this.get_all_prices().tax;
    }
    get_applicable_taxes() {
        var i;
        // Shenaningans because we need
        // to keep the taxes ordering.
        var ptaxes_ids = this.tax_ids || this.get_product().taxes_id;
        var ptaxes_set = {};
        for (i = 0; i < ptaxes_ids.length; i++) {
            ptaxes_set[ptaxes_ids[i]] = true;
        }
        var taxes = [];
        for (i = 0; i < this.pos.taxes.length; i++) {
            if (ptaxes_set[this.pos.taxes[i].id]) {
                taxes.push(this.pos.taxes[i]);
            }
        }
        return taxes;
    }
    get_tax_details() {
        return this.get_all_prices().taxDetails;
    }
    get_taxes() {
        var taxes_ids = this.tax_ids || this.get_product().taxes_id;
        return this.pos.getTaxesByIds(taxes_ids);
    }
    /**
     * Calculate the amount of taxes of a specific Orderline, that are included in the price.
     * @returns {Number} the total amount of price included taxes
     */
    get_total_taxes_included_in_price() {
        const productTaxes = this._getProductTaxesAfterFiscalPosition();
        const taxDetails = this.get_tax_details();
        return productTaxes
            .filter(tax => tax.price_include)
            .reduce((sum, tax) => sum + taxDetails[tax.id],
            0
        );
    }
    _map_tax_fiscal_position(tax, order = false) {
        return this.pos._map_tax_fiscal_position(tax, order);
    }
    /**
     * Mirror JS method of:
     * _compute_amount in addons/account/models/account.py
     */
    _compute_all(tax, base_amount, quantity, price_exclude) {
        return this.pos._compute_all(tax, base_amount, quantity, price_exclude);
    }
    /**
     * Mirror JS method of:
     * compute_all in addons/account/models/account.py
     *
     * Read comments in the python side method for more details about each sub-methods.
     */
    compute_all(taxes, price_unit, quantity, currency_rounding, handle_price_include = true) {
        return this.pos.compute_all(
            taxes,
            price_unit,
            quantity,
            currency_rounding,
            handle_price_include
        );
    }
    /**
     * Calculates the taxes for a product, and converts the taxes based on the fiscal position of the order.
     *
     * @returns {Object} The calculated product taxes after filtering and fiscal position conversion.
     */
    _getProductTaxesAfterFiscalPosition() {
        const product = this.get_product();
        let taxesIds = this.tax_ids || product.taxes_id;
        taxesIds = _.filter(taxesIds, t => t in this.pos.taxes_by_id);
        return this.pos.get_taxes_after_fp(taxesIds, this.order.fiscal_position);
    }
    get_all_prices(qty = this.get_quantity()) {
        var price_unit = this.get_unit_price() * (1.0 - this.get_discount() / 100.0);
        var taxtotal = 0;

        var product = this.get_product();
        var taxes_ids = this.tax_ids || product.taxes_id;
        taxes_ids = taxes_ids.filter((t) => t in this.pos.taxes_by_id);
        var taxdetail = {};
        var product_taxes = this.pos.get_taxes_after_fp(taxes_ids, this.order.fiscal_position);

        var all_taxes = this.compute_all(
            product_taxes,
            price_unit,
            qty,
            this.pos.currency.rounding
        );
        var all_taxes_before_discount = this.compute_all(
            product_taxes,
            this.get_unit_price(),
            qty,
            this.pos.currency.rounding
        );
        _(all_taxes.taxes).each(function (tax) {
            taxtotal += tax.amount;
            taxdetail[tax.id] = tax.amount;
        });

        return {
            priceWithTax: all_taxes.total_included,
            priceWithoutTax: all_taxes.total_excluded,
            priceWithTaxBeforeDiscount: all_taxes_before_discount.total_included,
            priceWithoutTaxBeforeDiscount: all_taxes_before_discount.total_excluded,
            tax: taxtotal,
            taxDetails: taxdetail,
        };
    }
    display_discount_policy() {
        return this.order.pricelist ? this.order.pricelist.discount_policy : "with_discount";
    }
    compute_fixed_price (price) {
        return this.pos.computePriceAfterFp(price, this.get_taxes());
    }
    get_fixed_lst_price() {
        return this.compute_fixed_price(this.get_lst_price());
    }
    get_lst_price() {
        return this.product.get_price(this.pos.default_pricelist, 1, this.price_extra);
    }
    set_lst_price(price) {
        this.order.assert_editable();
        this.product.lst_price = round_di(parseFloat(price) || 0, this.pos.dp["Product Price"]);
    }
    is_last_line() {
        var order = this.pos.get_order();
        var orderlines = order.orderlines;
        var last_id = orderlines[orderlines.length - 1].cid;
        var selectedLine = order ? order.selected_orderline : null;

        return !selectedLine ? false : last_id === selectedLine.cid;
    }
    set_customer_note(note) {
        this.customerNote = note;
    }
    get_customer_note() {
        return this.customerNote;
    }
    get_total_cost() {
        return this.product.standard_price * this.quantity;
    }
    /**
     * Checks if the current line is a tip from a customer.
     * @returns Boolean
     */
    isTipLine() {
        const tipProduct = this.pos.config.tip_product_id;
        return tipProduct && this.product.id === tipProduct[0];
    }
}

export class Packlotline extends PosModel {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.lot_name = null;
        this.order_line = options.order_line;
        if (options.json) {
            this.init_from_JSON(options.json);
            return;
        }
    }

    init_from_JSON(json) {
        this.order_line = json.order_line;
        this.set_lot_name(json.lot_name);
    }

    set_lot_name(name) {
        this.lot_name = String(name || "").trim() || null;
    }

    get_lot_name() {
        return this.lot_name;
    }

    export_as_JSON() {
        return {
            lot_name: this.get_lot_name(),
        };
    }
}

// Every Paymentline contains a cashregister and an amount of money.
export class Payment extends PosModel {
    setup(obj, options) {
        super.setup(...arguments);
        this.pos = options.pos;
        this.order = options.order;
        this.amount = 0;
        this.selected = false;
        this.cashier_receipt = "";
        this.ticket = "";
        this.payment_status = "";
        this.card_type = "";
        this.cardholder_name = "";
        this.transaction_id = "";

        if (options.json) {
            this.init_from_JSON(options.json);
            return;
        }
        this.payment_method = options.payment_method;
        if (this.payment_method === undefined) {
            throw new Error(_t("Please configure a payment method in your POS."));
        }
        this.name = this.payment_method.name;
    }
    init_from_JSON(json) {
        this.amount = json.amount;
        this.payment_method = this.pos.payment_methods_by_id[json.payment_method_id];
        this.can_be_reversed = json.can_be_reversed;
        this.name = this.payment_method.name;
        this.payment_status = json.payment_status;
        this.ticket = json.ticket;
        this.card_type = json.card_type;
        this.cardholder_name = json.cardholder_name;
        this.transaction_id = json.transaction_id;
        this.is_change = json.is_change;
    }
    //sets the amount of money on this payment line
    set_amount(value) {
        this.order.assert_editable();
        this.amount = round_di(parseFloat(value) || 0, this.pos.currency.decimal_places);
    }
    // returns the amount of money on this paymentline
    get_amount() {
        return this.amount;
    }
    get_amount_str() {
        return formatFloat(this.amount, {
            digits: [69, this.pos.currency.decimal_places],
        });
    }
    set_selected(selected) {
        if (this.selected !== selected) {
            this.selected = selected;
        }
    }
    /**
     * returns {string} payment status.
     */
    get_payment_status() {
        return this.payment_status;
    }

    /**
     * Set the new payment status.
     *
     * @param {string} value - new status.
     */
    set_payment_status(value) {
        this.payment_status = value;
    }

    /**
     * Check if paymentline is done.
     * Paymentline is done if there is no payment status or the payment status is done.
     */
    is_done() {
        return this.get_payment_status()
            ? this.get_payment_status() === "done" || this.get_payment_status() === "reversed"
            : true;
    }

    /**
     * Set info to be printed on the cashier receipt. value should
     * be compatible with both the QWeb and ESC/POS receipts.
     *
     * @param {string} value - receipt info
     */
    set_cashier_receipt(value) {
        this.cashier_receipt = value;
    }

    /**
     * Set additional info to be printed on the receipts. value should
     * be compatible with both the QWeb and ESC/POS receipts.
     *
     * @param {string} value - receipt info
     */
    set_receipt_info(value) {
        this.ticket += value;
    }

    // returns the associated cashregister
    //exports as JSON for server communication
    export_as_JSON() {
        return {
            name: serializeDateTime(DateTime.local()),
            payment_method_id: this.payment_method.id,
            amount: this.get_amount(),
            payment_status: this.payment_status,
            can_be_reversed: this.can_be_reversed,
            ticket: this.ticket,
            card_type: this.card_type,
            cardholder_name: this.cardholder_name,
            transaction_id: this.transaction_id,
        };
    }
    //exports as JSON for receipt printing
    export_for_printing() {
        return {
            cid: this.cid,
            amount: this.get_amount(),
            name: this.name,
            ticket: this.ticket,
        };
    }
    // If payment status is a non-empty string, then it is an electronic payment.
    // TODO: There has to be a less confusing way to distinguish simple payments
    // from electronic transactions. Perhaps use a flag?
    is_electronic() {
        return Boolean(this.get_payment_status());
    }
}

// An order more or less represents the content of a customer's shopping cart (the OrderLines)
// plus the associated payment information (the Paymentlines)
// there is always an active ('selected') order in the Pos, a new one is created
// automaticaly once an order is completed and sent to the server.
export class Order extends PosModel {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        var self = this;
        options = options || {};

        this.locked = false;
        this.pos = options.pos;
        this.selected_orderline = undefined;
        this.selected_paymentline = undefined;
        this.screen_data = {}; // see Gui
        this.temporary = options.temporary || false;
        this.creation_date = new Date();
        this.to_invoice = false;
        this.orderlines = new PosCollection();
        this.paymentlines = new PosCollection();
        this.pos_session_id = this.pos.pos_session.id;
        this.cashier = this.pos.get_cashier();
        this.finalized = false; // if true, cannot be modified.
        this.shippingDate = null;
        this.firstDraft = true;

        this.partner = null;

        this.uiState = {
            ReceiptScreen: {
                inputEmail: "",
                // if null: not yet tried to send
                // if false/true: tried sending email
                emailSuccessful: null,
                emailNotice: "",
            },
            // TODO: This should be in pos_restaurant.
            TipScreen: {
                inputTipAmount: "",
            },
        };

        if (options.json) {
            this.init_from_JSON(options.json);
        } else {
            this.set_pricelist(this.pos.default_pricelist);
            this.sequence_number = this.pos.pos_session.sequence_number++;
            this.access_token = uuidv4(); // unique uuid used to identify the authenticity of the request from the QR code.
            this.ticketCode = this._generateTicketCode(); // 5-digits alphanum code shown on the receipt
            this.uid = this.generate_unique_id();
            this.name = sprintf(_t("Order %s"), this.uid);
            this.validation_date = undefined;
            this.fiscal_position = this.pos.fiscal_positions.find(function (fp) {
                return fp.id === self.pos.config.default_fiscal_position_id[0];
            });
        }

        this.lastOrderPrepaChange = this.lastOrderPrepaChange || {};
    }
    save_to_db() {
        if (!this.temporary && !this.locked && !this.finalized) {
            this.assert_editable();
            this.pos.db.save_unpaid_order(this);
        }
    }
    /**
     * Initialize PoS order from a JSON string.
     *
     * If the order was created in another session, the sequence number should be changed so it doesn't conflict
     * with orders in the current session.
     * Else, the sequence number of the session should follow on the sequence number of the loaded order.
     *
     * @param {object} json JSON representing one PoS order.
     */
    init_from_JSON(json) {
        let partner;
        if (json.state && ["done", "invoiced", "paid"].includes(json.state)) {
            this.sequence_number = json.sequence_number;
        } else if (json.pos_session_id !== this.pos.pos_session.id) {
            this.sequence_number = this.pos.pos_session.sequence_number++;
        } else {
            this.sequence_number = json.sequence_number;
            this.pos.pos_session.sequence_number = Math.max(
                this.sequence_number + 1,
                this.pos.pos_session.sequence_number
            );
        }
        this.session_id = this.pos.pos_session.id;
        this.uid = json.uid;
        this.name = sprintf(_t("Order %s"), this.uid);
        this.validation_date = json.creation_date;
        this.server_id = json.server_id ? json.server_id : false;
        this.user_id = json.user_id;
        this.firstDraft = false;

        if (json.fiscal_position_id) {
            var fiscal_position = this.pos.fiscal_positions.find(function (fp) {
                return fp.id === json.fiscal_position_id;
            });

            if (fiscal_position) {
                this.fiscal_position = fiscal_position;
            } else {
                this.fiscal_position_not_found = true;
                console.error('ERROR: trying to load a fiscal position not available in the pos');
            }
        }

        if (json.pricelist_id) {
            this.pricelist = this.pos.pricelists.find(function (pricelist) {
                return pricelist.id === json.pricelist_id;
            });
        } else {
            this.pricelist = this.pos.default_pricelist;
        }

        if (json.partner_id) {
            partner = this.pos.db.get_partner_by_id(json.partner_id);
            if (!partner) {
                console.error("ERROR: trying to load a partner not available in the pos");
            }
        } else {
            partner = null;
        }
        this.partner = partner;

        this.temporary = false; // FIXME
        this.to_invoice = false; // FIXME
        this.shippingDate = json.shipping_date;

        var orderlines = json.lines;
        for (var i = 0; i < orderlines.length; i++) {
            var orderline = orderlines[i][2];
            if (orderline.product_id && this.pos.db.get_product_by_id(orderline.product_id)) {
                this.add_orderline(
                    new Orderline({}, { pos: this.pos, order: this, json: orderline })
                );
            }
        }

        var paymentlines = json.statement_ids;
        for (i = 0; i < paymentlines.length; i++) {
            var paymentline = paymentlines[i][2];
            var newpaymentline = new Payment({}, { pos: this.pos, order: this, json: paymentline });
            this.paymentlines.add(newpaymentline);

            if (i === paymentlines.length - 1) {
                this.select_paymentline(newpaymentline);
            }
        }

        // Tag this order as 'locked' if it is already paid.
        this.locked = ["paid", "done", "invoiced"].includes(json.state);
        this.state = json.state;
        this.amount_return = json.amount_return;
        this.account_move = json.account_move;
        this.backendId = json.id;
        this.is_tipped = json.is_tipped || false;
        this.tip_amount = json.tip_amount || 0;
        this.access_token = json.access_token || "";
        this.ticketCode = json.ticket_code || "";
        this.lastOrderPrepaChange =
            json.last_order_preparation_change && JSON.parse(json.last_order_preparation_change);
    }
    export_as_JSON() {
        var orderLines, paymentLines;
        orderLines = [];
        this.orderlines.forEach((item) => {
            return orderLines.push([0, 0, item.export_as_JSON()]);
        });
        paymentLines = [];
        this.paymentlines.forEach((item) => {
            return paymentLines.push([0, 0, item.export_as_JSON()]);
        });
        var json = {
            name: this.get_name(),
            amount_paid: this.get_total_paid() - this.get_change(),
            amount_total: this.get_total_with_tax(),
            amount_tax: this.get_total_tax(),
            amount_return: this.get_change(),
            lines: orderLines,
            statement_ids: paymentLines,
            pos_session_id: this.pos_session_id,
            pricelist_id: this.pricelist ? this.pricelist.id : false,
            partner_id: this.get_partner() ? this.get_partner().id : false,
            user_id: this.pos.user.id,
            uid: this.uid,
            sequence_number: this.sequence_number,
            creation_date: this.validation_date || this.creation_date, // todo: rename creation_date in master
            fiscal_position_id: this.fiscal_position ? this.fiscal_position.id : false,
            server_id: this.server_id ? this.server_id : false,
            to_invoice: this.to_invoice ? this.to_invoice : false,
            shipping_date: this.shippingDate ? this.shippingDate : false,
            is_tipped: this.is_tipped || false,
            tip_amount: this.tip_amount || 0,
            access_token: this.access_token || "",
            last_order_preparation_change: JSON.stringify(this.lastOrderPrepaChange),
            ticket_code: this.ticketCode || "",
        };
        if (!this.is_paid && this.user_id) {
            json.user_id = this.user_id;
        }
        return json;
    }
    _exportShippingDateForPrinting() {
        const shippingDate = DateTime.fromJSDate(new Date(this.shippingDate));
        return formatDate(shippingDate);
    }
    export_for_printing() {
        var orderlines = [];

        this.orderlines.forEach(function (orderline) {
            orderlines.push(orderline.export_for_printing());
        });

        // If order is locked (paid), the 'change' is saved as negative payment,
        // and is flagged with is_change = true. A receipt that is printed first
        // time doesn't show this negative payment so we filter it out.
        var paymentlines = this.paymentlines
            .filter(function (paymentline) {
                return !paymentline.is_change;
            })
            .map(function (paymentline) {
                return paymentline.export_for_printing();
            });
        const partner = this.partner;
        const cashier = this.cashier;
        const company = this.pos.company;
        const date = new Date();

        var receipt = {
            orderlines: orderlines,
            paymentlines: paymentlines,
            subtotal: this.get_subtotal(),
            total_with_tax: this.get_total_with_tax(),
            total_rounded: this.get_total_with_tax() + this.get_rounding_applied(),
            total_without_tax: this.get_total_without_tax(),
            total_tax: this.get_total_tax(),
            total_paid: this.get_total_paid(),
            total_discount: this.get_total_discount(),
            rounding_applied: this.get_rounding_applied(),
            tax_details: this.get_tax_details(),
            change: this.locked ? this.amount_return : this.get_change(),
            name: this.get_name(),
            partner: partner ? partner : null,
            invoice_id: null, //TODO
            cashier: cashier ? cashier.name : null,
            precision: {
                price: 2,
                money: 2,
                quantity: 3,
            },
            date: {
                year: date.getFullYear(),
                month: date.getMonth(),
                date: date.getDate(), // day of the month
                day: date.getDay(), // day of the week
                hour: date.getHours(),
                minute: date.getMinutes(),
                isostring: date.toISOString(),
                localestring: this.formatted_validation_date,
                validation_date: this.validation_date,
            },
            company: {
                email: company.email,
                website: company.website,
                company_registry: company.company_registry,
                contact_address: company.partner_id[1],
                vat: company.vat,
                vat_label: (company.country && company.country.vat_label) || _t("Tax ID"),
                name: company.name,
                phone: company.phone,
                logo: this.pos.company_logo_base64,
            },
            currency: this.pos.currency,
            pos_qr_code: this.finalized && this._get_qr_code_data(),
            ticket_code: this.pos.company.point_of_sale_ticket_unique_code
                ? (this.finalized && this.ticketCode)
                : false,
            base_url: this.pos.base_url,
        };

        const isHeaderOrFooter = this.pos.config.is_header_or_footer;
        receipt.header = (isHeaderOrFooter && this.pos.config.receipt_header) || "";
        receipt.footer = (isHeaderOrFooter && this.pos.config.receipt_footer) || "";

        if (!receipt.date.localestring && (!this.state || this.state == "draft")) {
            receipt.date.localestring = formatDateTime(DateTime.local());
        }

        return receipt;
    }
    async printChanges() {
        const orderChange = this.changesToOrder;
        let isPrintSuccessful = true;
        const d = new Date();
        let hours = "" + d.getHours();
        hours = hours.length < 2 ? "0" + hours : hours;
        let minutes = "" + d.getMinutes();
        minutes = minutes.length < 2 ? "0" + minutes : minutes;
        for (const printer of this.pos.unwatched.printers) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids,
                orderChange
            );
            if (changes["new"].length > 0 || changes["cancelled"].length > 0) {
                const printingChanges = {
                    new: changes["new"],
                    cancelled: changes["cancelled"],
                    table_name: this.pos.config.module_pos_restaurant
                        ? this.getTable().name
                        : false,
                    floor_name: this.pos.config.module_pos_restaurant
                        ? this.getTable().floor.name
                        : false,
                    name: this.name || "unknown order",
                    time: {
                        hours,
                        minutes,
                    },
                };
                const receipt = renderToElement("OrderChangeReceipt", { changes: printingChanges });
                const result = await printer.printReceipt(receipt);
                if (!result.successful) {
                    isPrintSuccessful = false;
                }
            }
        }

        return isPrintSuccessful;
    }
    _getPrintingCategoriesChanges(categories) {
        const currentOrderChange = this.changesToOrder;
        return {
            new: currentOrderChange["new"].filter((change) =>
                this.pos.db.is_product_in_category(categories, change["product_id"])
            ),
            cancelled: currentOrderChange["cancelled"].filter((change) =>
                this.pos.db.is_product_in_category(categories, change["product_id"])
            ),
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
        this.orderlines.forEach((line) => {
            if (!line.skipChange) {
                const note = line.getNote();
                const lineKey = `${line.uuid} - ${note}`;
                orderlineIdx.push(lineKey);

                if (this.lastOrderPrepaChange[lineKey]) {
                    this.lastOrderPrepaChange[lineKey]["quantity"] = line.get_quantity();
                } else {
                    this.lastOrderPrepaChange[lineKey] = {
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
        for (const lineKey in this.lastOrderPrepaChange) {
            if (!this.getOrderedLine(lineKey)) {
                delete this.lastOrderPrepaChange[lineKey];
            }
        }
    }

    /**
     * @returns {{ [productKey: string]: { product_id: number, name: string, note: string, quantity: number } }}
     * This function recalculates the information to be sent to the preparation tools,
     * it uses the variable lastOrderPrepaChange which contains the last changes sent
     * to perform this calculation.
     */
    getOrderChanges() {
        const prepaCategoryIds = this.pos.orderPreparationCategories;
        const oldChanges = this.lastOrderPrepaChange;
        const changes = {};

        if (!prepaCategoryIds.size) {
            return {};
        }

        // Compares the orderlines of the order with the last ones sent.
        // When one of them has changed, we add the change.
        for (const orderlineIdx in this.orderlines) {
            const orderline = this.orderlines[orderlineIdx];

            if (orderline.skipChange) {
                continue;
            }

            const product = orderline.get_product();
            const note = orderline.getNote();
            const productKey = `${product.id} - ${orderline.get_full_product_name()} - ${note}`;
            const lineKey = `${orderline.uuid} - ${note}`;

            if (prepaCategoryIds.has(product.pos_categ_id[0])) {
                const quantity = orderline.get_quantity();
                const quantityDiff = oldChanges[lineKey]
                    ? quantity - oldChanges[lineKey].quantity
                    : quantity;

                if (quantityDiff) {
                    changes[productKey] = {
                        name: orderline.get_full_product_name(),
                        product_id: product.id,
                        quantity: quantityDiff,
                        note: note,
                    };
                    orderline.setHasChange(true);
                } else {
                    orderline.setHasChange(false);
                }
            } else {
                orderline.setHasChange(false);
            }
        }

        // Checks whether an orderline has been deleted from the order since it
        // was last sent to the preparation tools. If so we add this to the changes.
        for (const [lineKey, lineResume] of Object.entries(this.lastOrderPrepaChange)) {
            if (!this.getOrderedLine(lineKey)) {
                const productKey = `${lineResume["product_id"]} - ${lineResume["name"]} - ${lineResume["note"]}`;
                if (!changes[productKey]) {
                    changes[productKey] = {
                        product_id: lineResume["product_id"],
                        name: lineResume["name"],
                        note: lineResume["note"],
                        quantity: -lineResume["quantity"],
                    };
                } else {
                    changes[productKey]["quantity"] -= lineResume["quantity"];
                }
            }
        }

        return changes;
    }
    // This function transforms the data generated by getOrderChanges into the old
    // pattern used by the printer and the display preparation. This old pattern comes from
    // the time when this logic was in pos_restaurant.
    get changesToOrder() {
        const toAdd = [];
        const toRemove = [];
        const changes = Object.values(this.getOrderChanges());

        for (const lineChange of changes) {
            if (lineChange["quantity"] > 0) {
                toAdd.push(lineChange);
            } else if (lineChange["quantity"] < 0) {
                lineChange["quantity"] *= -1; // we change the sign because that's how it is
                toRemove.push(lineChange);
            }
        }

        return { new: toAdd, cancelled: toRemove };
    }
    getOrderedLine(lineKey) {
        return this.orderlines.find(
            (line) =>
                line.uuid === this.lastOrderPrepaChange[lineKey]["line_uuid"] &&
                line.note === this.lastOrderPrepaChange[lineKey]["note"]
        );
    }
    hasSkippedChanges() {
        return this.orderlines.find((orderline) => orderline.skipChange) ? true : false;
    }
    hasChangesToPrint() {
        return Object.keys(this.getOrderChanges()).length ? true : false;
    }
    async pay() {
        if (
            this.orderlines.some(
                (line) => line.get_product().tracking !== "none" && !line.has_valid_product_lot()
            ) &&
            (this.pos.picking_type.use_create_lots || this.pos.picking_type.use_existing_lots)
        ) {
            const { confirmed } = await this.pos.env.services.popup.add(ConfirmPopup, {
                title: _t("Some Serial/Lot Numbers are missing"),
                body: _t(
                    "You are trying to sell products with serial/lot numbers, but some of them are not set.\nWould you like to proceed anyway?"
                ),
                confirmText: _t("Yes"),
                cancelText: _t("No"),
            });
            if (confirmed) {
                this.pos.env.services.pos.showScreen("PaymentScreen");
            }
        } else {
            this.pos.env.services.pos.showScreen("PaymentScreen");
        }
    }
    is_empty() {
        return this.orderlines.length === 0;
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
            zero_pad(this.pos.pos_session.id, 5) +
            "-" +
            zero_pad(this.pos.pos_session.login_number, 3) +
            "-" +
            zero_pad(this.sequence_number, 4)
        );
    }
    updateSavedQuantity() {
        this.orderlines.forEach((line) => line.updateSavedQuantity());
    }
    get_name() {
        return this.name;
    }
    assert_editable() {
        if (this.finalized) {
            throw new Error("Finalized Order cannot be modified");
        }
    }
    /* ---- Order Lines --- */
    add_orderline(line) {
        this.assert_editable();
        if (line.order) {
            line.order.remove_orderline(line);
        }
        line.order = this;
        this.orderlines.add(line);
        this.select_orderline(this.get_last_orderline());
    }
    get_orderline(id) {
        var orderlines = this.orderlines;
        for (var i = 0; i < orderlines.length; i++) {
            if (orderlines[i].id === id) {
                return orderlines[i];
            }
        }
        return null;
    }
    get_orderlines() {
        return this.orderlines;
    }
    /**
     * Groups the orderlines of the specific order according to the taxes applied to them. The orderlines that have
     * the exact same combination of taxes are grouped together.
     *
     * @returns {tax_ids: Orderlines[]} contains pairs of tax_ids (in csv format) and arrays of Orderlines
     * with the corresponding tax_ids.
     * e.g. {
     *  '1,2': [Orderline_A, Orderline_B],
     *  '3': [Orderline_C],
     * }
     */
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
            (tax_id) => this.pos.taxes_by_id[tax_id].price_include
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
        const orderlines = this.orderlines;
        return this.orderlines.at(orderlines.length - 1);
    }
    get_tip() {
        var tip_product = this.pos.db.get_product_by_id(this.pos.config.tip_product_id[0]);
        var lines = this.get_orderlines();
        if (!tip_product) {
            return 0;
        } else {
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].get_product() === tip_product) {
                    return lines[i].get_unit_price();
                }
            }
            return 0;
        }
    }

    initialize_validation_date() {
        this.validation_date = new Date();
        this.formatted_validation_date = formatDateTime(DateTime.fromJSDate(this.validation_date));
    }

    set_tip(tip) {
        var tip_product = this.pos.db.get_product_by_id(this.pos.config.tip_product_id[0]);
        var lines = this.get_orderlines();
        if (tip_product) {
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].get_product() === tip_product) {
                    lines[i].set_unit_price(tip);
                    lines[i].set_lst_price(tip);
                    lines[i].price_automatically_set = true;
                    lines[i].order.tip_amount = tip;
                    return;
                }
            }
            return this.add_product(tip_product, {
                is_tip: true,
                quantity: 1,
                price: tip,
                lst_price: tip,
                extras: { price_automatically_set: true },
            });
        }
    }
    set_fiscal_position(fiscal_position) {
        this.fiscal_position = fiscal_position;
    }
    set_pricelist(pricelist) {
        var self = this;
        this.pricelist = pricelist;

        var lines_to_recompute = this.get_orderlines().filter(
            (line) => !(line.price_manually_set || line.price_automatically_set)
        );
        lines_to_recompute.forEach((line) => {
            line.set_unit_price(
                line.product.get_price(self.pricelist, line.get_quantity(), line.get_price_extra())
            );
            self.fix_tax_included_price(line);
        });
    }
    remove_orderline(line) {
        this.assert_editable();
        this.orderlines.remove(line);
        this.select_orderline(this.get_last_orderline());
    }

    isFirstDraft() {
        return this.firstDraft;
    }

    fix_tax_included_price(line) {
        line.set_unit_price(line.compute_fixed_price(line.price));
    }

    _isRefundOrder() {
        if (this.orderlines.length > 0 && this.orderlines[0].refunded_orderline_id) {
            return true;
        }
        return false;
    }

    add_product(product, options) {
        if(this.pos.doNotAllowRefundAndSales() && this._isRefundOrder() && (!options.quantity || options.quantity > 0)) {
            this.pos.env.services.popup.add(ErrorPopup, {
                title: _t('Refund and Sales not allowed'),
                body: _t('It is not allowed to mix refunds and sales')
            });
            return;
        }
        if (this._printed) {
            // when adding product with a barcode while being in receipt screen
            this.pos.removeOrder(this);
            return this.pos.add_new_order().add_product(product, options);
        }
        this.assert_editable();
        options = options || {};
        var line = new Orderline({}, { pos: this.pos, order: this, product: product });
        this.fix_tax_included_price(line);

        this.set_orderline_options(line, options);

        var to_merge_orderline;
        for (var i = 0; i < this.orderlines.length; i++) {
            if (this.orderlines.at(i).can_be_merged_with(line) && options.merge !== false) {
                to_merge_orderline = this.orderlines.at(i);
            }
        }
        if (to_merge_orderline) {
            to_merge_orderline.merge(line);
            this.select_orderline(to_merge_orderline);
        } else {
            this.add_orderline(line);
            this.select_orderline(this.get_last_orderline());
        }

        if (options.draftPackLotLines) {
            this.selected_orderline.setPackLotLines({ ...options.draftPackLotLines, setQuantity: options.quantity === undefined });
        }
    }
    set_orderline_options(orderline, options) {
        if (options.quantity !== undefined) {
            orderline.set_quantity(options.quantity);
        }

        if (options.price_extra !== undefined) {
            orderline.price_extra = options.price_extra;
            orderline.set_unit_price(
                orderline.product.get_price(
                    this.pricelist,
                    orderline.get_quantity(),
                    options.price_extra
                )
            );
            this.fix_tax_included_price(orderline);
        }

        if (options.price !== undefined) {
            orderline.set_unit_price(options.price);
            this.fix_tax_included_price(orderline);
        }

        if (options.lst_price !== undefined) {
            orderline.set_lst_price(options.lst_price);
        }

        if (options.discount !== undefined) {
            orderline.set_discount(options.discount);
        }

        if (options.description !== undefined) {
            orderline.description += options.description;
        }

        if (options.extras !== undefined) {
            for (var prop in options.extras) {
                orderline[prop] = options.extras[prop];
            }
        }
        if (options.is_tip) {
            this.is_tipped = true;
            this.tip_amount = options.price;
        }
        if (options.refunded_orderline_id) {
            orderline.refunded_orderline_id = options.refunded_orderline_id;
        }
        if (options.tax_ids) {
            orderline.tax_ids = options.tax_ids;
        }
    }
    get_selected_orderline() {
        return this.selected_orderline;
    }
    select_orderline(line) {
        if (line) {
            if (line !== this.selected_orderline) {
                // if line (new line to select) is not the same as the old
                // selected_orderline, then we set the old line to false,
                // and set the new line to true. Also, set the new line as
                // the selected_orderline.
                if (this.selected_orderline) {
                    this.selected_orderline.set_selected(false);
                }
                this.selected_orderline = line;
                this.selected_orderline.set_selected(true);
            }
        } else {
            this.selected_orderline = undefined;
        }
        this.pos.numpadMode = "quantity";
    }
    deselect_orderline() {
        if (this.selected_orderline) {
            this.selected_orderline.set_selected(false);
            this.selected_orderline = undefined;
        }
    }

    /* ---- Payment Lines --- */
    add_paymentline(payment_method) {
        this.assert_editable();
        if (this.electronic_payment_in_progress()) {
            return false;
        } else {
            var newPaymentline = new Payment(
                {},
                { order: this, payment_method: payment_method, pos: this.pos }
            );
            this.paymentlines.add(newPaymentline);
            this.select_paymentline(newPaymentline);
            if (this.pos.config.cash_rounding) {
                this.selected_paymentline.set_amount(0);
            }
            newPaymentline.set_amount(this.get_due());

            if (payment_method.payment_terminal) {
                newPaymentline.set_payment_status("pending");
            }
            return newPaymentline;
        }
    }
    get_paymentlines() {
        return this.paymentlines;
    }
    /**
     * Retrieve the paymentline with the specified cid
     *
     * @param {String} cid
     */
    get_paymentline(cid) {
        var lines = this.get_paymentlines();
        return lines.find(function (line) {
            return line.cid === cid;
        });
    }
    remove_paymentline(line) {
        this.assert_editable();
        if (this.selected_paymentline === line) {
            this.select_paymentline(undefined);
        }
        this.paymentlines.remove(line);
    }
    clean_empty_paymentlines() {
        var lines = this.paymentlines;
        var empty = [];
        for (var i = 0; i < lines.length; i++) {
            if (!lines[i].get_amount()) {
                empty.push(lines[i]);
            }
        }
        for (i = 0; i < empty.length; i++) {
            this.remove_paymentline(empty[i]);
        }
    }
    select_paymentline(line) {
        if (line !== this.selected_paymentline) {
            if (this.selected_paymentline) {
                this.selected_paymentline.set_selected(false);
            }
            this.selected_paymentline = line;
            if (this.selected_paymentline) {
                this.selected_paymentline.set_selected(true);
            }
        }
    }
    electronic_payment_in_progress() {
        return this.get_paymentlines().some(function (pl) {
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
        var lines = this.get_paymentlines();
        var line = lines.find(function (line) {
            var status = line.get_payment_status();
            return (
                status && !["done", "reversed", "reversing", "pending", "retry"].includes(status)
            );
        });
        if (line) {
            line.set_payment_status("waitingCancel");
            line.payment_method.payment_terminal
                .send_payment_cancel(this, line.cid)
                .finally(function () {
                    line.set_payment_status("retry");
                });
        }
    }
    /* ---- Payment Status --- */
    get_subtotal() {
        return round_pr(
            this.orderlines.reduce(function (sum, orderLine) {
                return sum + orderLine.get_display_price();
            }, 0),
            this.pos.currency.rounding
        );
    }
    get_total_with_tax() {
        return this.get_total_without_tax() + this.get_total_tax();
    }
    get_total_without_tax() {
        return round_pr(
            this.orderlines.reduce(function (sum, orderLine) {
                return sum + orderLine.get_price_without_tax();
            }, 0),
            this.pos.currency.rounding
        );
    }
    _get_ignored_product_ids_total_discount() {
        return [];
    }
    _reduce_total_discount_callback(sum, orderLine){
        let discountUnitPrice = orderLine.getUnitDisplayPriceBeforeDiscount() * (orderLine.get_discount()/100);
        if (orderLine.display_discount_policy() === 'without_discount'){
            discountUnitPrice += orderLine.get_taxed_lst_unit_price() - orderLine.getUnitDisplayPriceBeforeDiscount();
        }
        return sum + discountUnitPrice * orderLine.get_quantity();
    }
    get_total_discount() {
        const ignored_product_ids = this._get_ignored_product_ids_total_discount();
        return round_pr(
            this.orderlines.reduce((sum, orderLine) => {
                if (!ignored_product_ids.includes(orderLine.product.id)) {
                    sum +=
                        orderLine.getUnitDisplayPriceBeforeDiscount() *
                        (orderLine.get_discount() / 100) *
                        orderLine.get_quantity();
                    if (orderLine.display_discount_policy() === "without_discount") {
                        sum +=
                            (orderLine.get_taxed_lst_unit_price() - orderLine.getUnitDisplayPriceBeforeDiscount()) *
                            orderLine.get_quantity();
                    }
                }
                return sum;
            }, 0),
            this.pos.currency.rounding
        );
    }
    get_total_tax() {
        if (this.pos.company.tax_calculation_rounding_method === "round_globally") {
            // As always, we need:
            // 1. For each tax, sum their amount across all order lines
            // 2. Round that result
            // 3. Sum all those rounded amounts
            var groupTaxes = {};
            this.orderlines.forEach(function (line) {
                var taxDetails = line.get_tax_details();
                var taxIds = Object.keys(taxDetails);
                for (var t = 0; t < taxIds.length; t++) {
                    var taxId = taxIds[t];
                    if (!(taxId in groupTaxes)) {
                        groupTaxes[taxId] = 0;
                    }
                    groupTaxes[taxId] += taxDetails[taxId];
                }
            });

            var sum = 0;
            var taxIds = Object.keys(groupTaxes);
            for (var j = 0; j < taxIds.length; j++) {
                var taxAmount = groupTaxes[taxIds[j]];
                sum += round_pr(taxAmount, this.pos.currency.rounding);
            }
            return sum;
        } else {
            return round_pr(
                this.orderlines.reduce(function (sum, orderLine) {
                    return sum + orderLine.get_tax();
                }, 0),
                this.pos.currency.rounding
            );
        }
    }
    get_total_paid() {
        return round_pr(
            this.paymentlines.reduce(function (sum, paymentLine) {
                if (paymentLine.is_done()) {
                    sum += paymentLine.get_amount();
                }
                return sum;
            }, 0),
            this.pos.currency.rounding
        );
    }
    get_tax_details() {
        var details = {};
        var fulldetails = [];

        this.orderlines.forEach(function (line) {
            var ldetails = line.get_tax_details();
            for (var id in ldetails) {
                if (Object.hasOwnProperty.call(ldetails, id)) {
                    details[id] = (details[id] || 0) + ldetails[id];
                }
            }
        });

        for (var id in details) {
            if (Object.hasOwnProperty.call(details, id)) {
                fulldetails.push({
                    amount: details[id],
                    tax: this.pos.taxes_by_id[id],
                    name: this.pos.taxes_by_id[id].name,
                });
            }
        }

        return fulldetails;
    }
    // Returns a total only for the orderlines with products belonging to the category
    get_total_for_category_with_tax(categ_id) {
        var total = 0;
        var self = this;

        if (categ_id instanceof Array) {
            for (var i = 0; i < categ_id.length; i++) {
                total += this.get_total_for_category_with_tax(categ_id[i]);
            }
            return total;
        }

        this.orderlines.forEach(function (line) {
            if (self.pos.db.category_contains(categ_id, line.product.id)) {
                total += line.get_price_with_tax();
            }
        });

        return total;
    }
    get_total_for_taxes(tax_id) {
        var total = 0;

        if (!(tax_id instanceof Array)) {
            tax_id = [tax_id];
        }

        var tax_set = {};

        for (var i = 0; i < tax_id.length; i++) {
            tax_set[tax_id[i]] = true;
        }

        this.orderlines.forEach((line) => {
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
            var lines = this.paymentlines;
            for (var i = 0; i < lines.length; i++) {
                change += lines[i].get_amount();
                if (lines[i] === paymentline) {
                    break;
                }
            }
        }
        return round_pr(Math.max(0, change), this.pos.currency.rounding);
    }
    get_due(paymentline) {
        if (!paymentline) {
            var due =
                this.get_total_with_tax() - this.get_total_paid() + this.get_rounding_applied();
        } else {
            due = this.get_total_with_tax();
            var lines = this.paymentlines;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i] === paymentline) {
                    break;
                } else {
                    due -= lines[i].get_amount();
                }
            }
        }
        return round_pr(due, this.pos.currency.rounding);
    }
    get_rounding_applied() {
        if (this.pos.config.cash_rounding) {
            const only_cash = this.pos.config.only_round_cash_method;
            const paymentlines = this.get_paymentlines();
            const last_line = paymentlines ? paymentlines[paymentlines.length - 1] : false;
            const last_line_is_cash = last_line
                ? last_line.payment_method.is_cash_count == true
                : false;
            if (!only_cash || (only_cash && last_line_is_cash)) {
                var rounding_method = this.pos.cash_rounding[0].rounding_method;
                var remaining = this.get_total_with_tax() - this.get_total_paid();
                var sign = this.get_total_with_tax() > 0 ? 1.0 : -1.0;
                if (
                    (
                        (this.get_total_with_tax() < 0 && remaining > 0) ||
                        (this.get_total_with_tax() > 0 && remaining < 0)
                    ) &&
                    rounding_method !== "HALF-UP"
                ) {
                    rounding_method = rounding_method === "UP" ? "DOWN" : "UP";
                }

                remaining *= sign;
                var total = round_pr(remaining, this.pos.cash_rounding[0].rounding);
                var rounding_applied = total - remaining;

                // because floor and ceil doesn't include decimals in calculation, we reuse the value of the half-up and adapt it.
                if (floatIsZero(rounding_applied, this.pos.currency.decimal_places)) {
                    // https://xkcd.com/217/
                    return 0;
                } else if (
                    Math.abs(this.get_total_with_tax()) < this.pos.cash_rounding[0].rounding
                ) {
                    return 0;
                } else if (rounding_method === "UP" && rounding_applied < 0 && remaining > 0) {
                    rounding_applied += this.pos.cash_rounding[0].rounding;
                } else if (rounding_method === "UP" && rounding_applied > 0 && remaining < 0) {
                    rounding_applied -= this.pos.cash_rounding[0].rounding;
                } else if (rounding_method === "DOWN" && rounding_applied > 0 && remaining > 0) {
                    rounding_applied -= this.pos.cash_rounding[0].rounding;
                } else if (rounding_method === "DOWN" && rounding_applied < 0 && remaining < 0) {
                    rounding_applied += this.pos.cash_rounding[0].rounding;
                }
                else if(rounding_method === "HALF-UP" && rounding_applied === this.pos.cash_rounding[0].rounding / -2){
                    rounding_applied += this.pos.cash_rounding[0].rounding;
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
            !this.pos.config.cash_rounding ||
            this.get_total_with_tax() < this.pos.cash_rounding[0].rounding
        ) {
            return false;
        }

        const only_cash = this.pos.config.only_round_cash_method;
        var lines = this.paymentlines;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            if (only_cash && !line.payment_method.is_cash_count) {
                continue;
            }

            if (
                !floatIsZero(
                    line.amount - round_pr(line.amount, this.pos.cash_rounding[0].rounding),
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
        return !!this.paymentlines.find(function (pl) {
            return pl.payment_method.is_cash_count;
        });
    }
    check_paymentlines_rounding() {
        if (this.pos.config.cash_rounding) {
            var cash_rounding = this.pos.cash_rounding[0].rounding;
            var default_rounding = this.pos.currency.rounding;
            for (var id in this.get_paymentlines()) {
                var line = this.get_paymentlines()[id];
                var diff = round_pr(
                    round_pr(line.amount, cash_rounding) - round_pr(line.amount, default_rounding),
                    default_rounding
                );
                if (this.get_total_with_tax() < this.pos.cash_rounding[0].rounding) {
                    return true;
                }
                if (diff && line.payment_method.is_cash_count) {
                    return false;
                } else if (!this.pos.config.only_round_cash_method && diff) {
                    return false;
                }
            }
            return true;
        }
        return true;
    }
    get_total_cost() {
        return this.orderlines.reduce(function (sum, orderLine) {
            return sum + orderLine.get_total_cost();
        }, 0);
    }
    /* ---- Invoice --- */
    set_to_invoice(to_invoice) {
        this.assert_editable();
        this.to_invoice = to_invoice;
    }
    is_to_invoice() {
        return this.to_invoice;
    }
    /* ---- Partner --- */
    // the partner related to the current order.
    set_partner(partner) {
        this.assert_editable();
        this.partner = partner;
    }
    get_partner() {
        return this.partner;
    }
    get_partner_name() {
        const partner = this.partner;
        return partner ? partner.name : "";
    }
    get_cardholder_name() {
        var card_payment_line = this.paymentlines.find((pl) => pl.cardholder_name);
        return card_payment_line ? card_payment_line.cardholder_name : "";
    }
    /* ---- Screen Status --- */
    // the order also stores the screen status, as the PoS supports
    // different active screens per order. This method is used to
    // store the screen status.
    set_screen_data(value) {
        this.screen_data["value"] = value;
    }
    //see set_screen_data
    get_screen_data() {
        const screen = this.screen_data["value"];
        // If no screen data is saved
        //   no payment line -> product screen
        //   with payment line -> payment screen
        if (!screen) {
            if (this.get_paymentlines().length > 0) {
                return { name: "PaymentScreen" };
            }
            return { name: "ProductScreen" };
        }
        if (!this.finalized && this.get_paymentlines().length > 0) {
            return { name: "PaymentScreen" };
        }
        return screen;
    }
    wait_for_push_order() {
        return false;
    }
    /**
     * @returns {Object} object to use as props for instantiating OrderReceipt.
     */
    getOrderReceiptEnv() {
        // Formerly get_receipt_render_env defined in ScreenWidget.
        return {
            order: this,
            receipt: this.export_for_printing(),
            orderlines: this.get_orderlines(),
            paymentlines: this.get_paymentlines(),
            shippingDate: this.shippingDate ? this._exportShippingDateForPrinting() : false,
        };
    }
    updatePricelist(newPartner) {
        let newPartnerPricelist, newPartnerFiscalPosition;
        const defaultFiscalPosition = this.pos.fiscal_positions.find(
            (position) => position.id === this.pos.config.default_fiscal_position_id[0]
        );
        if (newPartner) {
            newPartnerFiscalPosition = newPartner.property_account_position_id
                ? this.pos.fiscal_positions.find(
                      (position) => position.id === newPartner.property_account_position_id[0]
                  )
                : defaultFiscalPosition;
            newPartnerPricelist =
                this.pos.pricelists.find(
                    (pricelist) => pricelist.id === newPartner.property_product_pricelist[0]
                ) || this.pos.default_pricelist;
        } else {
            newPartnerFiscalPosition = defaultFiscalPosition;
            newPartnerPricelist = this.pos.default_pricelist;
        }
        this.set_fiscal_position(newPartnerFiscalPosition);
        this.set_pricelist(newPartnerPricelist);
    }
    /* ---- Ship later --- */
    setShippingDate(shippingDate) {
        this.shippingDate = shippingDate;
    }
    getShippingDate() {
        return this.shippingDate;
    }
    getHasRefundLines() {
        for (const line of this.get_orderlines()) {
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
        if (this.get_orderlines().length == 0) {
            return this.get_paymentlines().length != 0;
        } else {
            return true;
        }
    }
    _get_qr_code_data() {
        if (this.pos.company.point_of_sale_use_ticket_qr_code) {
            const codeWriter = new window.ZXing.BrowserQRCodeSvgWriter();
            // Use the unique access token to ensure the authenticity of the request. Use the order reference as a second check just in case.
            const address = `${this.pos.base_url}/pos/ticket/validate?access_token=${this.access_token}`;
            const qr_code_svg = new XMLSerializer().serializeToString(
                codeWriter.write(address, 150, 150)
            );
            return "data:image/svg+xml;base64," + window.btoa(qr_code_svg);
        } else {
            return false;
        }
    }
    /**
     * Returns a random 5 digits alphanumeric code
     * @returns {string}
     */
    _generateTicketCode() {
        let code = "";
        while (code.length != 5) {
            code = Math.random().toString(36).slice(2, 7);
        }
        return code;
    }
}
