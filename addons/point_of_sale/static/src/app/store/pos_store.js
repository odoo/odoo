/** @odoo-module */
/* global waitForWebfonts */

import { Mutex } from "@web/core/utils/concurrency";
import { markRaw } from "@odoo/owl";
import { floatIsZero } from "@web/core/utils/numbers";
import { registry } from "@web/core/registry";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { deduceUrl, random5Chars, uuidv4, getOnNotified } from "@point_of_sale/utils";
import { Reactive } from "@web/core/utils/reactive";
import { HWPrinter } from "@point_of_sale/app/printer/hw_printer";
import { memoize } from "@web/core/utils/functions";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { CashOpeningPopup } from "@point_of_sale/app/store/cash_opening_popup/cash_opening_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { renderToString } from "@web/core/utils/render";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import { ProductConfiguratorPopup } from "./product_configurator_popup/product_configurator_popup";
import { ComboConfiguratorPopup } from "./combo_configurator_popup/combo_configurator_popup";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { PartnerList } from "../screens/partner_list/partner_list";
import { ScaleScreen } from "../screens/scale_screen/scale_screen";
import { computeComboLines } from "../models/utils/compute_combo_lines";
import { changesToOrder, getOrderChanges } from "../models/utils/order_change";
import {
    getPriceUnitAfterFiscalPosition,
    getTaxesAfterFiscalPosition,
    getTaxesValues,
} from "../models/utils/tax_utils";
import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { ConnectionLostError } from "@web/core/network/rpc";

const { DateTime } = luxon;

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
        "bus_service",
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
        this.env = env;
        this.numberBuffer = number_buffer;
        this.barcodeReader = barcode_reader;
        this.ui = ui;
        this.dialog = dialog;
        this.printer = printer;
        this.bus = bus_service;
        this.data = pos_data;
        this.unwatched = markRaw({});
        this.pushOrderMutex = new Mutex();

        // Business data; loaded from the server at launch
        this.company_logo = null;
        this.company_logo_base64 = "";
        this.order_sequence = 1;
        this.printers_category_ids_set = new Set();

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
        this.selectedOrderUuid = null;
        this.selectedPartner = null;
        this.selectedCategory = null;
        this.showResultMobile = false;
        this.searchProductWord = "";
        this.ready = new Promise((resolve) => {
            this.markReady = resolve;
        });

        // FIXME POSREF: the hardwareProxy needs the pos and the pos needs the hardwareProxy. Maybe
        // the hardware proxy should just be part of the pos service?
        this.hardwareProxy.pos = this;
        await this.initServerData();
        if (this.useProxy()) {
            await this.connectToProxy();
        }
        this.closeOtherTabs();
        this.preloadImages();
        this.showScreen("ProductScreen");
    }

    useProxy() {
        return (
            this.config.is_posbox &&
            (this.config.iface_electronic_scale ||
                this.config.iface_print_via_proxy ||
                this.config.iface_scan_via_proxy ||
                this.config.iface_customer_facing_display_via_proxy)
        );
    }

    async initServerData() {
        await this.processServerData();
        this.onNotified = getOnNotified(this.bus, this.config.access_token);
        return await this.afterProcessServerData();
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

                if (item.raw.product_id && product.id === item.raw.product_id) {
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

    async afterProcessServerData() {
        const openOrders = this.data.models["pos.order"].filter((order) => !order.finalized);

        if (!this.config.module_pos_restaurant) {
            this.selectedOrderUuid = openOrders.length
                ? openOrders[openOrders.length - 1].uuid
                : this.add_new_order().uuid;
        }

        if (this.open_orders_json) {
            // This method is to load the demo datas.
            this.loadOpenOrders(this.open_orders_json);
        }
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
    async openConfigurator(product) {
        return await makeAwaitable(this.dialog, ProductConfiguratorPopup, {
            product: product,
        });
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
            return current_order.pricelist_id;
        }
        return this.config.pricelist_id;
    }

    async set_tip(tip) {
        const currentOrder = this.get_order();
        const tipProduct = this.config.tip_product_id;
        let line = currentOrder.lines.find((line) => line.product_id.id === tipProduct.id);

        if (line) {
            line.set_unit_price(tip);
        } else {
            line = await this.addLineToCurrentOrder(
                { product_id: tipProduct, price_unit: tip },
                {}
            );
        }

        currentOrder.is_tipped = true;
        currentOrder.tip_amount = tip;
        return line;
    }

    selectOrderLine(order, line) {
        order.select_orderline(line);
        this.numpadMode = "quantity";
    }
    // This method should be called every time a product is added to an order.
    // The configure parameter is available if the orderline already contains all
    // the information without having to be calculated. For example, importing a SO.
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const product = vals.product_id;
        let merge = true;

        let order = this.get_order();
        order.assert_editable();

        if (!order) {
            order = this.add_new_order();
        }

        const options = {
            uiState: {
                price_type: "original",
            },
            ...opts,
        };

        if ("price_unit" in vals) {
            merge = false;
            options.uiState.price_type = "manual";
        }

        const values = {
            price_extra: 0,
            price_unit: 0,
            order_id: this.get_order(),
            qty: 1,
            tax_ids: product.taxes_id[0] ? [["link", product.taxes_id[0]]] : [],
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
        if (product.isConfigurable() && configure) {
            const payload = await this.openConfigurator(product);

            if (payload) {
                Object.assign(values, {
                    attribute_value_ids: payload.attribute_value_ids.map((id) => [
                        "link",
                        this.data.models["product.template.attribute.value"].get(id),
                    ]),
                    custom_attribute_value_ids: Object.entries(payload.attribute_custom_values).map(
                        ([id, cus]) => {
                            return [
                                "create",
                                {
                                    custom_product_template_attribute_value_id:
                                        this.data.models["product.template.attribute.value"].get(
                                            id
                                        ),
                                    custom_value: cus,
                                },
                            ];
                        }
                    ),
                    price_extra: values.price_extra + payload.price_extra,
                    qty: payload.qty || values.qty,
                });
            } else {
                return;
            }
        }

        // In case of clicking a combo product a popup will be shown to the user
        // It will return the combo prices and the selected products
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (product.isCombo() && configure) {
            const payload = await makeAwaitable(this.dialog, ComboConfiguratorPopup, {
                product: product,
            });

            if (!payload) {
                return;
            }

            const comboPrices = computeComboLines(
                product,
                payload,
                order.pricelist_id,
                this.data.models["decimal.precision"].getAll(),
                this.data.models["product.template.attribute.value"].getAllBy("id")
            );

            values.combo_line_ids = comboPrices.map((comboLine) => [
                "create",
                {
                    product_id: comboLine.combo_line_id.product_id,
                    tax_ids: comboLine.combo_line_id.product_id.taxes_id[0]
                        ? [["link", comboLine.combo_line_id.product_id.taxes_id[0]]]
                        : [],
                    combo_line_id: comboLine.combo_line_id,
                    price_unit: comboLine.price_unit,
                    order_id: order,
                    qty: 1,
                    attribute_value_ids: comboLine.attribute_value_ids?.map((attr) => [
                        "link",
                        attr,
                    ]),
                    custom_attribute_value_ids: Object.entries(
                        comboLine.attribute_custom_values
                    ).map(([id, cus]) => {
                        return [
                            "create",
                            {
                                custom_product_template_attribute_value_id:
                                    this.data.models["product.template.attribute.value"].get(id),
                                custom_value: cus,
                            },
                        ];
                    }),
                },
            ]);
        }

        // In the case of a product with tracking enabled, we need to ask the user for the lot/serial number.
        // It will return an instance of pos.pack.operation.lot
        // ---
        // This actions cannot be handled inside pos_order.js or pos_order_line.js
        if (product.isTracked() && configure) {
            const code = opts.code;
            let pack_lot_ids = {};
            const packLotLinesToEdit =
                (!product.isAllowOnlyOneLot() &&
                    this.get_order()
                        .get_orderlines()
                        .filter((line) => !line.get_discount())
                        .find((line) => line.product_id.id === product.id)
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
                pack_lot_ids = await this.editLots(product, packLotLinesToEdit);
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
        if (product.to_weight && this.config.iface_electronic_scale && configure) {
            if (product.isScaleAvailable) {
                const weight = await makeAwaitable(this.env.services.dialog, ScaleScreen, {
                    product,
                });
                if (!weight) {
                    return;
                }
                values.qty = weight;
            } else {
                await product._onScaleNotAvailable();
            }
        }

        // Handle price unit
        if (!product.isCombo() && !vals.price_unit) {
            values.price_unit = product.get_price(order.pricelist_id, values.qty);
        }

        if (values.price_extra > 0) {
            const price = values.product_id.get_price(
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

        const selectedOrderline = order.get_selected_orderline();
        if (options.draftPackLotLines && configure) {
            selectedOrderline.setPackLotLines({
                ...options.draftPackLotLines,
                setQuantity: options.quantity === undefined,
            });
        }

        let to_merge_orderline;
        for (const curLine of order.lines) {
            if (curLine.id !== line.id) {
                if (curLine.can_be_merged_with(line) && merge !== false) {
                    to_merge_orderline = curLine;
                }
            }
        }

        if (to_merge_orderline) {
            to_merge_orderline.merge(line);
            line.delete();
            this.selectOrderLine(order, to_merge_orderline);
        } else if (!selectedOrderline) {
            this.selectOrderLine(order, order.get_last_orderline());
        }

        this.numberBuffer.reset();

        // FIXME: Put this in an effect so that we don't have to call it manually.
        order.recomputeOrderData();

        this.numberBuffer.reset();

        // FIXME: If merged with another line, this returned object is useless.
        return line;
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

    loadOpenOrders(openOrders) {
        // This method is for the demo data
        let isOrderSet = false;
        for (const json of openOrders) {
            if (this.models["pos.order"].find((el) => el.id === json.id)) {
                continue;
            }
            this.add_new_order(json);
            if (!isOrderSet) {
                this.selectedOrderUuid = this.pos.models["pos.order"].getFirst().uuid;
                isOrderSet = true;
            }
        }
    }

    posHasValidProduct() {
        return this.has_available_products;
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
        if (this.isOpenOrderShareable() || removeFromServer) {
            if (typeof order.id === "number" && !order.finalized) {
                this.addPendingOrder([order.id], true);
            }
        }

        return this.data.localDeleteCascade(order, removeFromServer);
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
            zero_pad(this.session.id, 5) +
            "-" +
            zero_pad(this.session.login_number, 3) +
            "-" +
            zero_pad(this.session.sequence_number, 4)
        );
    }
    createNewOrder(data = {}) {
        const fiscalPosition = this.models["account.fiscal.position"].find((fp) => {
            return fp.id === this.config.default_fiscal_position_id?.id;
        });

        const uniqId = this.generate_unique_id();
        const order = this.models["pos.order"].create({
            session_id: this.session,
            company_id: this.company,
            config_id: this.config,
            picking_type_id: this.pickingType,
            user_id: this.user,
            sequence_number: this.session.sequence_number,
            access_token: uuidv4(),
            ticket_code: random5Chars(),
            fiscal_position_id: fiscalPosition,
            name: _t("Order %s", uniqId),
            pos_reference: uniqId,
            ...data,
        });

        this.session.sequence_number++;
        order.set_pricelist(this.config.pricelist_id);
        return order;
    }
    add_new_order(data = {}) {
        if (this.get_order()) {
            this.get_order().updateSavedQuantity();
        }

        const order = this.createNewOrder(data);
        this.selectedOrderUuid = order.uuid;
        return order;
    }

    selectNextOrder() {
        const orders = this.models["pos.order"].filter((order) => !order.finalized);
        if (orders.length > 0) {
            this.selectedOrderUuid = orders[0].uuid;
        } else {
            this.add_new_order();
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
        // With the relational model, the record ID looks like this: pos.order_2.
        // If the ID is a string, this means that it has not yet been sent to the server.
        const orderToCreate = this.models["pos.order"].filter(
            (order) => this.pendingOrder.create.has(order.id) && order.lines.length > 0
        );
        const orderToUpdate = this.models["pos.order"].filter((order) =>
            this.pendingOrder.write.has(order.id)
        );

        return {
            orderToCreate,
            orderToUpdate,
        };
    }

    removePendingOrder(order) {
        this.pendingOrder["create"].delete(order.id);
        this.pendingOrder["write"].delete(order.id);
        this.pendingOrder["delete"].delete(order.id);
        return true;
    }

    getSyncAllOrdersContext(orders) {
        return {
            config_id: this.config.id,
        };
    }

    // There for override
    preSyncAllOrders(orders) {}
    postSyncAllOrders(orders) {}
    async syncAllOrders(options = {}) {
        try {
            const { orderToCreate, orderToUpdate } = this.getPendingOrder();
            const orders = [...orderToCreate, ...orderToUpdate];
            this.preSyncAllOrders(orders);
            const idsToDelete = [...this.pendingOrder.delete];
            const context = this.getSyncAllOrdersContext(orders);

            if (idsToDelete.length > 0) {
                this.pendingOrder.delete.clear();
                await this.data.ormDelete("pos.order", idsToDelete);
            }

            // Allow us to force the sync of the orders In the case of
            // pos_restaurant is usefull to get unsynced orders
            // for a specific table
            if (orders.length === 0 && !context.force) {
                return;
            }

            // Re-compute all taxes, prices and other information needed for the backend
            for (const order of orders) {
                order.recomputeOrderData();
            }

            const orderToDelete = [];
            const { localOrders, serializedOrder } = orders.reduce(
                (acc, curr) => {
                    acc.localOrders.push(curr);
                    acc.serializedOrder.push(curr.serialize({ orm: true }));
                    return acc;
                },
                { localOrders: [], serializedOrder: [] }
            );

            const data = await this.data.callRelated(
                "pos.order",
                "sync_from_ui",
                [serializedOrder],
                {
                    context,
                }
            );

            const serverOrders = data["pos.order"];
            for (const localO of localOrders) {
                const serverO = serverOrders.find((o) => o.uuid === localO.uuid);
                serverO.uiState = {
                    ...localO.uiState,
                    locked: serverO.finalized && typeof serverO.id === "number",
                };

                if (serverO && typeof localO.id === "string") {
                    orderToDelete.push(localO);
                }
            }

            for (const serverO of serverOrders) {
                if (serverO.state === "draft") {
                    this.addPendingOrder([serverO.id]);
                } else {
                    this.removePendingOrder(serverO);
                }

                for (const line of serverO.lines) {
                    const refundedOrderLine = line.refunded_orderline_id;

                    if (refundedOrderLine) {
                        const order = refundedOrderLine.order_id;
                        delete order.uiState.lineToRefund[refundedOrderLine.uuid];
                        refundedOrderLine.refunded_qty += Math.abs(line.qty);
                    }
                }
            }

            for (const orderToDel of orderToDelete) {
                this.removePendingOrder(orderToDel);
                // We can force the delete because at this point we have serverO
                this.data.localDeleteCascade(orderToDel, true);
            }

            this.postSyncAllOrders(serverOrders);
            return serverOrders;
        } catch (error) {
            console.warn("Offline mode active, order will be synced later");

            if (options.throw) {
                throw error;
            }

            return error;
        }
    }

    push_orders() {
        return this.pushOrderMutex.exec(() => this.syncAllOrders());
    }

    push_single_order(order) {
        return this.pushOrderMutex.exec(() => this.syncAllOrders(order));
    }

    // created this hook for modularity
    _updateOrder(ordersResponseData, orders) {
        const order = orders.find((order) => order.name === ordersResponseData.pos_reference);
        if (order) {
            order.server_id = ordersResponseData.id;
            return order;
        }
    }

    // load the partners based on the ids
    async _loadPartners(partnerIds) {
        if (partnerIds.length > 0) {
            await this.data.read("res.partner", partnerIds);
        }
    }
    setLoadingOrderState(bool) {
        this.loadingOrderState = bool;
    }
    async pay() {
        const currentOrder = this.get_order();

        if (!currentOrder.canPay()) {
            return;
        }

        if (
            currentOrder.lines.some(
                (line) => line.get_product().tracking !== "none" && !line.has_valid_product_lot()
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
                this.env.services.pos.showScreen("PaymentScreen");
            }
        } else {
            this.mobile_pane = "right";
            this.env.services.pos.showScreen("PaymentScreen");
        }
    }
    async getServerOrders() {
        return await this.data.searchRead("pos.order", [
            ["config_id", "in", [...this.config.raw.trusted_config_ids, this.config.id]],
            ["state", "=", "draft"],
        ]);
    }
    async getProductInfo(product, quantity) {
        const order = this.get_order();
        // check back-end method `get_product_info_pos` to see what it returns
        // We do this so it's easier to override the value returned and use it in the component template later
        const productInfo = await this.data.call("product.product", "get_product_info_pos", [
            [product.id],
            product.get_price(order.pricelist_id, quantity),
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
    // return the current order
    get_order() {
        if (!this.selectedOrderUuid) {
            return undefined;
        }

        return this.models["pos.order"].getBy("uuid", this.selectedOrderUuid);
    }

    // change the current order
    set_order(order, options) {
        if (this.get_order()) {
            this.get_order().updateSavedQuantity();
        }
        this.selectedOrderUuid = order?.uuid;
    }

    // return the list of unpaid orders
    get_order_list() {
        return this.models["pos.order"].filter((o) => !o.finalized);
    }

    getTaxesByIds(taxIds) {
        const taxes = [];
        for (let i = 0; i < taxIds.length; i++) {
            if (this.tax_data_by_id[taxIds[i]]) {
                taxes.push(this.tax_data_by_id[taxIds[i]]);
            }
        }
        return taxes;
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
            // Orders that were not imported because they already exist (uuid conflict)
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
                existing_uids[existing[i].uuid] = true;
            }

            for (i = 0; i < json.unpaid_orders.length; i++) {
                var order = json.unpaid_orders[i];
                if (order.pos_session_id !== this.session.id) {
                    report.unpaid_skipped_session += 1;
                    skipped_sessions[order.pos_session_id] = true;
                } else if (existing_uids[order.uuid]) {
                    report.unpaid_skipped_existing += 1;
                } else {
                    orders.push(this.createNewOrder(order));
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

    getProductPrice(product, p = false) {
        const pricelist = this.getDefaultPricelist();
        let price = p === false ? product.get_price(pricelist, 1) : p;

        let taxes = product.taxes_id;

        // Fiscal position.
        const order = this.get_order();
        if (order && order.fiscal_position_id) {
            price = getPriceUnitAfterFiscalPosition(
                taxes,
                price,
                product,
                this.company._product_default_values,
                order.fiscal_position_id,
                this.models
            );
            taxes = getTaxesAfterFiscalPosition(taxes, order.fiscal_position_id, this.models);
        }

        // Taxes computation.
        const taxesData = getTaxesValues(
            taxes,
            price,
            1,
            product,
            this.company._product_default_values,
            this.company,
            this.currency
        );

        if (this.config.iface_tax_included === "total") {
            return taxesData.total_included;
        } else {
            return taxesData.total_excluded;
        }
    }

    /**
     * @param {str} terminalName
     */
    getPendingPaymentLine(terminalName) {
        return this.get_order().payment_ids.find(
            (paymentLine) =>
                paymentLine.payment_method_id.use_payment_terminal === terminalName &&
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
        return floatIsZero(qty, dp);
    }

    disallowLineQuantityChange() {
        return false;
    }

    getCurrencySymbol() {
        return this.currency ? this.currency.symbol : "$";
    }
    isOpenOrderShareable() {
        return this.config.raw.trusted_config_ids.length > 0;
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
    orderExportForPrinting(order) {
        const headerData = this.getReceiptHeaderData(order);
        const baseUrl = this.base_url;
        return order.export_for_printing(baseUrl, headerData);
    }
    async printReceipt() {
        const isPrinted = await this.printer.print(
            OrderReceipt,
            {
                data: this.orderExportForPrinting(this.get_order()),
                formatCurrency: this.env.utils.formatCurrency,
            },
            { webPrintFallback: true }
        );
        if (isPrinted) {
            this.get_order()._printed = true;
        }
    }
    getOrderChanges(skipped = false, order = this.get_order()) {
        return getOrderChanges(order, skipped, this.orderPreparationCategories);
    }
    // Now the printer should work in PoS without restaurant
    async sendOrderInPreparation(order, cancelled = false) {
        if (this.printers_category_ids_set.size) {
            try {
                const changes = changesToOrder(
                    order,
                    false,
                    this.orderPreparationCategories,
                    cancelled
                );
                if (changes.cancelled.length > 0 || changes.new.length > 0) {
                    const isPrintSuccessful = await order.printChanges(
                        false,
                        this.orderPreparationCategories,
                        cancelled,
                        this.unwatched.printers
                    );
                    if (!isPrintSuccessful) {
                        this.dialog.add(AlertDialog, {
                            title: _t("Printing failed"),
                            body: _t("Failed in printing the changes in the order"),
                        });
                    }
                }
            } catch (e) {
                console.info("Failed in printing the changes in the order", e);
            }
        }
    }
    async sendOrderInPreparationUpdateLastChange(o, cancelled = false) {
        const uuid = o.uuid;
        this.addPendingOrder([o.id]);
        await this.syncAllOrders();

        const order = this.models["pos.order"].find((order) => order.uuid === uuid);
        await this.sendOrderInPreparation(order, cancelled);
        order.updateLastOrderChange();
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
        const openOrder = this.models["pos.order"].filter((order) => !order.finalized);

        if (customerDisplayService) {
            customerDisplayService.update({ closeUI: true });
        }

        // If pos is not properly loaded, we just go back to /web without
        // doing anything in the order data.
        if (!this || openOrder.length === 0) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }

        // If there are orders in the db left unsynced, we try to sync.
        const syncSuccess = await this.push_orders_with_closing_popup();
        if (syncSuccess) {
            window.location = "/web#action=point_of_sale.action_client_pos_menu";
        }
    }
    shouldShowNavbarButtons() {
        return true;
    }
    async selectPricelist(pricelist) {
        await this.get_order().set_pricelist(pricelist);
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
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: currentPartner,
            missingFields,
        });

        if (payload) {
            currentOrder.set_partner(payload);
        } else {
            currentOrder.set_partner(false);
        }

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

    async editLots(product, packLotLinesToEdit) {
        const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
        let canCreateLots = this.pickingType.use_create_lots || !this.pickingType.use_existing_lots;

        let existingLots = [];
        try {
            existingLots = await this.data.call("pos.order.line", "get_existing_lots", [
                this.company.id,
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
            (this.mainScreen.component === ProductScreen &&
                (this.selectedCategory || this.showResultMobile || this.mobile_pane == "left") &&
                this.ui.isSmall) ||
            this.mainScreen.component === TicketScreen
        );
    }

    showSearchButton() {
        return this.mainScreen.component === ProductScreen && this.mobile_pane === "right";
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

    async showQR(payment) {
        let qr;
        try {
            qr = await this.data.call("pos.payment.method", "get_qr_code", [
                [payment.payment_method_id.id],
                payment.amount,
                payment.pos_order_id.name,
                payment.pos_order_id.name,
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
