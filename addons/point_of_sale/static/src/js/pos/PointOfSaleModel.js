/** @odoo-module alias=point_of_sale.PointOfSaleModel **/

import env from 'web.env';
import OrderFetcher from 'point_of_sale.OrderFetcher';
import BarcodeParser from 'barcodes.BarcodeParser';
import BarcodeReader from 'point_of_sale.BarcodeReader';
// IMPROVEMENT: maybe extract the htmlToImg method from Printer to avoid this Printer dependency.
import { Printer } from 'point_of_sale.Printer';
import devices from 'point_of_sale.devices';
import time from 'web.time';
import { _t, qweb } from 'web.core';
import { Mutex } from 'web.concurrency';
import { format, parse } from 'web.field_utils';
import { round_decimals, round_precision, float_is_zero, unaccent, is_email } from 'web.utils';
import {
    cloneDeep,
    uuidv4,
    sum,
    maxDateString,
    generateWrappedName,
    posRound,
    posFloatCompare,
} from 'point_of_sale.utils';
const { EventBus } = owl.core;
const { Component } = owl;
const { onMounted, onWillUnmount } = owl.hooks;
import { getImplementation } from 'point_of_sale.PaymentInterface';

class PointOfSaleModel extends EventBus {
    constructor(webClient, searchLimit = 100, storage = null) {
        super(...arguments);
        this.setup(webClient, searchLimit, storage);
    }
    /**
     * `constructor` is not patchable so we introduce this method as alternative
     * to be able to patch the initialization of this class.
     * This is a good place to declare the top-level fields.
     */
    setup(webClient, searchLimit, storage) {
        this.data = {
            records: this._initDataRecords(),
            derived: this._initDataDerived(),
            uiState: this._initDataUiState(),
            fields: {},
            sortedIds: {},
        };
        this.mutex = new Mutex();
        this.searchLimit = searchLimit;
        this.webClient = webClient;
        this.barcodeReader = new BarcodeReader({ model: this });
        this.orderFetcher = new OrderFetcher(this);
        this.proxy = new devices.ProxyDevice(this);
        this.proxy_queue = new devices.JobQueue();
        this.customerDisplayWindow = null;
        this.extrasFieldsMap = this._defineExtrasFields();
        // other top-level fields (@see _assignTopLevelFields)
        // Declare here in case it is needed before mounting `PointOfSaleUI`.
        this.session = {};
        this.config = {};
        this.company = {};
        this.country = {};
        this.currency = {};
        this.cashRounding = {};
        this.companyCurrency = {};
        this.user = {};
        this.pickingType = {};
        this.backStatement = {};
        this.version = {};
        if (!storage) {
            this.storage = window.localStorage;
        } else {
            this.storage = storage;
        }
        this.POS_N_DECIMALS = 6;
    }
    useModel() {
        const component = Component.current;
        onMounted(() => {
            this.on('ACTION_DONE', this, () => {
                component.render();
            });
        });
        onWillUnmount(() => {
            this.off('ACTION_DONE', this);
        });
    }
    /**
     * Use this to dispatch an action. We use mutex to `sequentialize` the execution of actions.
     * This means that the succeeding actions won't be executed until the previous action has resolved
     * (or rejected).
     * @param {Object} action
     * @param {string} action.name
     * @param {any[]} action.args args needed by the action
     * @param {Object} mutex the mutex to use to execute the action. If not provided, a default mutex is used.
     *      Allowing the use of other mutex aside from the default that is created in this file is
     *      practically an extension point. This is useful when we don't want to block an action
     *      from being executed when another action is not yet done.
     */
    actionHandler(action, mutex) {
        if (!mutex) {
            mutex = this.mutex;
        }
        return new Promise((resolve, reject) => {
            mutex.exec(async () => {
                try {
                    resolve(await this._actionHandler(action));
                } catch (e) {
                    reject(e);
                }
            });
        });
    }
    /**
     * This can be used to dispatch an action inside another dispatched action. However,
     * use this with caution because it doesn't use mutex. So if multiple actions are
     * dispatched simultaneously using this, race condition issues may happen because of
     * interleaving async method calls.
     */
    async _actionHandler(action) {
        try {
            const handler = this[action.name];
            if (!handler) throw new Error(`Action '${action.name}' is not defined.`);
            return await handler.call(this, ...(action.args || []));
        } finally {
            this.trigger('ACTION_DONE');
            this.persistActiveOrder();
            // NOTE: Calling this only on actions that involve the activeOrder is better performance-wise.
            if (!this.data.uiState.isLoading) {
                this._updateCustomerDisplay();
            }
        }
    }
    /**
     * Declare the containers of the models that are dynamic in the pos ui and those that are not
     * loaded during `load_pos_data`. We don't declare `res.partner` here even though it is dynamic
     * since it is part of the loaded records.
     */
    _initDataRecords() {
        return {
            ['pos.order']: {},
            ['pos.order.line']: {},
            ['pos.payment']: {},
            ['pos.pack.operation.lot']: {},
        };
    }
    /**
     * Declare here the initial values of the data that will be derived after `load_pos_data`.
     */
    _initDataDerived() {
        return {
            decimalPrecisionByName: {},
            productByBarcode: {},
            fiscalPositionTaxMaps: {},
            // sorted payment methods (cash method first)
            paymentMethods: [],
            // Maps the `use_payment_terminal` field of a payment method to its `PaymentInterface` implementation _instance_.
            paymentTerminals: {},
            // it's value can be one of the three:
            // 'NO_ROUNDING' | 'WITH_ROUNDING' | 'ONLY_CASH_ROUNDING'
            roundingScheme: 'NO_ROUNDING',
            companyLogoBase64: false,
            categoryParent: {},
            categoryChildren: {},
            categoryAncestors: {},
            /**
             * The idea is to construct this search string which will contain all the partners.
             * Then, we pattern match the string to get the ids of the search result.
             * The search string will look like:
             * ```
             *  1:partner 1 name|partner 1 address...
             *  2:partner 2 name|partner 2 address...
             * ```
             */
            partnerSearchString: '',
            // Contains similar string values as `partnerSearchString`, keyed by category id.
            categorySearchStrings: {},
            // This maps a category id to a set of product ids.
            // We use set to prevent duplicates in the product ids assigned to each category.
            // Rendering duplicates can result to crashing in owl.
            // Ordering is not a problem because Set preserves the insertion order of the items.
            productsByCategoryId: {},
            attributes_by_ptal_id: {},
            partnerByBarcode: {},
            latestWriteDates: {},
        };
    }
    /**
     * Declare here the initial values of all the global ui states.
     */
    _initDataUiState() {
        return {
            isLoading: true,
            showOfflineError: true,
            previousScreen: '',
            activeScreen: '',
            activeScreenProps: {},
            activeOrderId: false,
            activeCategoryId: 0,
            TicketScreen: {
                filter: undefined,
                searchDetails: {},
            },
            OrderManagementScreen: {
                managementOrderIds: new Set([]),
                activeOrderId: false,
                searchTerm: '',
            },
            DebugWidget: {
                successfulRequest: true,
                successfulCancel: true,
                successfulReverse: true,
                idleTimerEnabled: true,
            },
            LoadingScreen: {
                skipButtonIsShown: false,
            },
        };
    }
    /**
     * Maps model name -> _extras fields
     * Declare here the _extras signature of the model. Each field
     * should be serializeable because `_extras` is part of a record which
     * is saved in the localStorage.
     * IMPROVEMENT: use the defined type for validation.
     */
    _defineExtrasFields() {
        return {
            'pos.order': {
                activeScreen: 'string',
                activeOrderlineId: 'string',
                activePaymentId: 'string',
                uid: 'string',
                // when this is set, it also means that the order is validated and
                // that it is supposed to be synced. So if this extra field has
                // value, and there is no value set to server_id, it means that
                // the order failed to sync to the backend.
                validationDate: 'string',
                server_id: 'number',
                ReceiptScreen: {
                    inputEmail: 'string',
                    emailSuccessful: 'boolean',
                    emailNotice: 'string',
                },
                printed: 'number',
                isFromClosedSession: 'boolean',
                deleted: 'boolean',
            },
            'pos.order.line': {
                description: 'string',
                price_extra: 'number',
                dontMerge: 'boolean',
            },
            'pos.payment': {
                can_be_reversed: 'boolean',
            },
            'product.product': {
                image_base64: 'string',
            },
        };
    }

    //#region LOADING

    /**
     * Method called when the `PointOfSaleUI` component is mounted.
     */
    async loadPosData() {
        await this._fetchAndProcessPosData();
        await this._connectToProxy();
        await this.actionHandler({ name: 'actionDoneLoading' });
        await this._afterDoneLoading();
    }
    /**
     * First step of the loading.
     * Fetches the data needed from the backend then process the loaded data.
     */
    async _fetchAndProcessPosData() {
        const [records, sortedIds, fields] = await this.rpc({
            model: 'pos.session',
            method: 'load_pos_data',
            args: [[odoo.pos_session_id]],
        });
        this._assignDataRecords(records);
        this._assignDataSortedIds(sortedIds);
        this._assignDataFields(fields);
        await this._assignTopLevelFields();
        await this._assignDataDerived();
        await this._loadPersistedOrders();
    }
    /**
     * Second step of the loading.
     * Connect to proxy if necessary.
     */
    async _connectToProxy() {
        if (!this.getUseProxy()) {
            return;
        }
        this.barcodeReader.disconnect_from_proxy();
        await this.actionHandler({ name: 'actionShowSkipButton' });
        try {
            await this.proxy.autoconnect({
                force_ip: this.config.proxy_ip || undefined,
            });
            if (this.config.iface_scan_via_proxy) {
                await this.barcodeReader.connect_to_proxy(this.proxy);
            }
        } catch (error) {
            if (error instanceof Error) throw error;
            const [statusText, url] = error;
            if (statusText == 'error' && window.location.protocol == 'https:') {
                this.ui.askUser('ErrorPopup', {
                    title: _t('HTTPS connection to IoT Box failed'),
                    body: _.str.sprintf(
                        _t(
                            'Make sure you are using IoT Box v18.12 or higher. Navigate to %s to accept the certificate of your IoT Box.'
                        ),
                        url
                    ),
                });
            }
        }
    }
    /**
     * Final step of loading.
     * At this point, the UI is ready. Use this method as a hook to run
     * needed background tasks after loading.
     */
    async _afterDoneLoading() {
        this._loadFonts();
        this._preloadImages();
    }
    /**
     * /!\ ATTENTION: This works as long as you are in production mode. In dev mode,
     * different js files are asking for the images (this file and the owl.js file).
     * Because of that, even if this file already preloaded the images, owl.js (during
     * rendering) will still ask for them and it will appear that the images are not
     * cached (you will see that it still tries to reach the server). Not sure if
     * this is a bug or a feature of chrome.
     */
    async _preloadImages() {
        const imageUrls = [];
        for (const product of this.getProducts(0)) {
            imageUrls.push(this.getImageUrl('product.product', product));
        }
        for (const category of this.getRecords('pos.category')) {
            if (category.id == 0) continue;
            imageUrls.push(this.getImageUrl('pos.category', category));
        }
        for (const imageName of ['backspace.png', 'bc-arrow-big.png']) {
            imageUrls.push(`/point_of_sale/static/src/img/${imageName}`);
        }
        await this.loadImages(imageUrls);
    }
    _loadFonts() {
        return new Promise(function (resolve) {
            // Waiting for fonts to be loaded to prevent receipt printing
            // from printing empty receipt while loading Inconsolata
            // ( The font used for the receipt )
            waitForWebfonts(['Lato', 'Inconsolata'], function () {
                resolve();
            });
            // The JS used to detect font loading is not 100% robust, so
            // do not wait more than 5sec
            setTimeout(resolve, 5000);
        });
    }
    _assignDataRecords(records) {
        Object.assign(this.data.records, records);
    }
    _assignDataSortedIds(sortedIds) {
        Object.assign(this.data.sortedIds, sortedIds);
    }
    _assignDataFields(fields) {
        Object.assign(this.data.fields, fields);
    }
    async _assignTopLevelFields() {
        this.session = this.getRecord('pos.session', odoo.pos_session_id);
        this.config = this.getRecord('pos.config', this.session.config_id);
        this.company = this.getRecord('res.company', this.config.company_id);
        this.country = this.getRecord('res.country', this.company.country_id);
        this.currency = this.getRecord('res.currency', this.config.currency_id);
        this.cashRounding = this.getRecord('account.cash.rounding', this.config.rounding_method);
        this.companyCurrency = this.getRecord('res.currency', this.company.currency_id);
        this.user = this.getRecord('res.users', this.session.user_id);
        this.pickingType = this.getRecord('stock.picking.type', this.config.picking_type_id);
        this.backStatement = this.getRecord('account.bank.statement', this.session.cash_register_id);
        this.version = await this._getVersion();
    }
    async _assignDataDerived() {
        this._setDecimalPrecisionByName();
        this._setFiscalPositionMap();
        this._setupProducts();
        this._setPartnerByBarcode();
        this._initPartnerLatestWriteDate();
        this._setPartnerSearchString();
        this._setPaymentMethods();
        this._setCashRounding();
        await this._setCompanyLogo();
        await this._setBarcodeParser();
    }
    /**
     * Call related methods in setting up product and pos category data.
     */
    _setupProducts() {
        this._processCategories();
        this._addProducts(this.getRecords('product.product'));
        this._setProductAttributes();
    }
    _addProducts(products) {
        this._setProductByBarcode(products);
        this._setProductSearchStrings(products);
    }
    _processCategories() {
        this.setRecord('pos.category', 0, {
            id: 0,
            name: 'Root',
            parent_id: false,
        });
        const categoryParent = this.data.derived.categoryParent;
        const categoryChildren = this.data.derived.categoryChildren;
        const categoryAncestors = this.data.derived.categoryAncestors;
        for (const category of this.getRecords('pos.category')) {
            if (category.id === 0) continue;
            let parentId = category.parent_id;
            if (!parentId || !this.exists('pos.category', parentId)) {
                parentId = 0;
            }
            categoryParent[category.id] = parentId;
            if (!categoryChildren[parentId]) {
                categoryChildren[parentId] = [];
            }
            categoryChildren[parentId].push(category.id);
        }
        (function makeAncestors(categoryId, ancestors) {
            categoryAncestors[categoryId] = ancestors;

            ancestors = ancestors.slice(0);
            ancestors.push(categoryId);

            const children = categoryChildren[categoryId] || [];
            for (let i = 0, len = children.length; i < len; i++) {
                makeAncestors(children[i], ancestors);
            }
        })(0, []);
        this.data.uiState.activeCategoryId = this.config.iface_start_categ_id ? this.config.iface_start_categ_id : 0;
    }
    _setProductSearchStrings(products) {
        const productsByCategoryId = this.data.derived.productsByCategoryId;
        const categorySearchStrings = this.data.derived.categorySearchStrings;

        const addProductOnCategory = (categoryId, productId, searchString) => {
            if (!productsByCategoryId[categoryId]) {
                productsByCategoryId[categoryId] = new Set();
                categorySearchStrings[categoryId] = '';
            }
            if (!productsByCategoryId[categoryId].has(productId)) {
                productsByCategoryId[categoryId].add(productId);
                categorySearchStrings[categoryId] += searchString;
            }
        };

        for (const product of products) {
            if (!product.available_in_pos) continue;
            const searchString = unaccent(this._getProductSearchString(product));
            const categoryId = product.pos_categ_id ? product.pos_categ_id : 0;
            addProductOnCategory(categoryId, product.id, searchString);
            for (const ancestor of this.getCategoryAncestorIds(categoryId)) {
                addProductOnCategory(ancestor, product.id, searchString);
            }
        }
    }
    /**
     * IMPROVEMENT: Perhaps it is better to generalize indexing of records
     * based on other fields. E.g. the products and partners are indexed
     * by barcode here. pos.order can also be indexed by it's name.
     */
    _setProductByBarcode(products) {
        for (const product of products) {
            if (!product.barcode) continue;
            if (product.barcode in this.data.derived.productByBarcode) {
                console.warn(
                    `Failed to set '${product.display_name} (id=${product.id})' to barcode '${product.barcode}'. The barcode is already assign to another product.`
                );
                continue;
            }
            this.data.derived.productByBarcode[product.barcode] = product;
        }
    }
    _setPartnerByBarcode() {
        for (const partner of this.getRecords('res.partner')) {
            if (!partner.barcode) continue;
            this.data.derived.partnerByBarcode[partner.barcode] = partner;
        }
    }
    _setDecimalPrecisionByName() {
        for (const dp of this.getRecords('decimal.precision')) {
            this.data.derived.decimalPrecisionByName[dp.name] = dp;
        }
    }
    _setFiscalPositionMap() {
        for (const fiscalPosition of this.getRecords('account.fiscal.position')) {
            const fiscalPositionTaxes = fiscalPosition.tax_ids.map((id) =>
                this.getRecord('account.fiscal.position.tax', id)
            );
            const taxMapping = {};
            for (const fptax of fiscalPositionTaxes) {
                // It's possible the single source tax maps to multiple different destination taxes.
                if (!taxMapping[fptax.tax_src_id]) {
                    taxMapping[fptax.tax_src_id] = [];
                }
                taxMapping[fptax.tax_src_id].push(fptax.tax_dest_id);
            }
            this.data.derived.fiscalPositionTaxMaps[fiscalPosition.id] = taxMapping;
        }
    }
    async _loadPersistedOrders() {
        this.recoverPersistedOrders();
        const orders = this.getDraftOrders().sort((order1, order2) => (order1.date_order > order2.date_order ? -1 : 1));
        await this._chooseActiveOrder(orders);
    }
    async _chooseActiveOrder(draftOrders) {
        if (draftOrders.length) {
            await this.actionSelectOrder(draftOrders[0]);
        } else {
            const order = this._createDefaultOrder();
            this._setActiveOrderId(order.id);
        }
    }
    _initPartnerLatestWriteDate() {
        this._setLatestWriteDate(
            'res.partner',
            maxDateString(...this.getRecords('res.partner').map((partner) => partner.write_date))
        );
    }
    _setPartnerSearchString() {
        let searchString = '';
        for (const partner of this.getRecords('res.partner')) {
            searchString += this._getPartnerSearchString(partner);
        }
        this.data.derived.partnerSearchString = unaccent(searchString);
    }
    _setPaymentMethods() {
        this.data.derived.paymentMethods = this.getRecords('pos.payment.method').sort((a, b) => {
            if (a.is_cash_count && !b.is_cash_count) {
                return -1;
            } else if (!a.is_cash_count && b.is_cash_count) {
                return 1;
            } else {
                return a.id - b.id;
            }
        });
        for (const paymentMethod of this.data.derived.paymentMethods) {
            this._setPaymentTerminal(paymentMethod);
        }
    }
    _setProductAttributes() {
        const attributes_by_ptal_id = this.data.derived.attributes_by_ptal_id;
        for (const ptav of this.getRecords('product.template.attribute.value')) {
            if (!attributes_by_ptal_id[ptav.attribute_line_id]) {
                const productAttribute = this.getRecord('product.attribute', ptav.attribute_id);
                attributes_by_ptal_id[ptav.attribute_line_id] = {
                    id: ptav.attribute_line_id,
                    name: productAttribute.name,
                    display_type: productAttribute.display_type,
                    values: [],
                };
            }
            const productAttributeValue = this.getRecord('product.attribute.value', ptav.product_attribute_value_id);
            attributes_by_ptal_id[ptav.attribute_line_id].values.push({
                id: ptav.product_attribute_value_id,
                name: productAttributeValue.name,
                is_custom: productAttributeValue.is_custom,
                html_color: productAttributeValue.html_color,
                price_extra: ptav.price_extra,
            });
        }
    }
    _setCashRounding() {
        if (this.config.cash_rounding) {
            this.data.derived.roundingScheme = this.config.only_round_cash_method
                ? 'ONLY_CASH_ROUNDING'
                : 'WITH_ROUNDING';
        } else {
            this.data.derived.roundingScheme = 'NO_ROUNDING';
        }
    }
    _setCompanyLogo() {
        const companyLogoImg = new Image();
        return new Promise((resolve) => {
            companyLogoImg.onload = () => {
                let ratio = 1;
                const targetwidth = 300;
                const maxheight = 150;
                if (companyLogoImg.width !== targetwidth) {
                    ratio = targetwidth / companyLogoImg.width;
                }
                if (companyLogoImg.height * ratio > maxheight) {
                    ratio = maxheight / companyLogoImg.height;
                }
                const width = Math.floor(companyLogoImg.width * ratio);
                const height = Math.floor(companyLogoImg.height * ratio);
                const c = document.createElement('canvas');
                c.width = width;
                c.height = height;
                const ctx = c.getContext('2d');
                ctx.drawImage(companyLogoImg, 0, 0, width, height);
                this.data.derived.companyLogoBase64 = c.toDataURL();
                resolve();
            };
            companyLogoImg.onerror = () => {
                console.warn(_t('Unexpected error when loading company logo.'));
            };
            companyLogoImg.crossOrigin = 'anonymous';
            companyLogoImg.src =
                '/web/binary/company_logo' +
                '?dbname=' +
                env.session.db +
                '&company=' +
                this.company.id +
                '&_' +
                Math.random();
        });
    }
    /**
     * Barcode can only be loaded/configured when the config is loaded.
     */
    async _setBarcodeParser() {
        const barcodeParser = new BarcodeParser({ nomenclature_id: [this.config.barcode_nomenclature_id] });
        await barcodeParser.is_loaded();
        this.barcodeReader.set_barcode_parser(barcodeParser);
    }
    async _getVersion() {
        return env.session.rpc('/web/webclient/version_info', {});
    }
    /**
     * This method instantiates the PaymentInterface implementation that corresponds
     * to the `use_payment_terminal` of the given `paymentMethod`.
     * @see PaymentInterface
     * @see _setPaymentMethods
     * @param {'pos.payment.method'} paymentMethod
     */
    _setPaymentTerminal(paymentMethod) {
        const paymentTerminals = this.data.derived.paymentTerminals;
        const terminalName = paymentMethod.use_payment_terminal;
        if (terminalName && !(terminalName in paymentTerminals)) {
            const Implementation = getImplementation(terminalName);
            if (!Implementation) {
                throw new Error(
                    `PaymentInterface implementation of '${terminalName}' for payment method '${paymentMethod.name}' is missing.`
                );
            }
            paymentTerminals[terminalName] = new Implementation(this, paymentMethod);
        }
    }
    getImageUrl(model, record, imgField = 'image_128') {
        return `/web/image?model=${model}&field=${imgField}&id=${record.id}&write_date=${record.write_date}&unique=1`;
    }
    loadImages(urls) {
        return Promise.all(urls.map((url) => this._loadImage(url)));
    }
    /**
     * This resolves when the given src of image has properly loaded.
     * Rejects when it failed to load.
     * @param {string} src
     */
    _loadImage(src) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            image.src = src;
            image.onload = () => {
                resolve();
            };
            image.onerror = () => {
                reject(new Error(`Image with src='${src}' is not loaded.`));
            };
        });
    }

    //#endregion LOADING

    //#region UTILITY

    /**
     * Checks if there is an existing `model` record for the given `id`.
     * @param
     */
    exists(model, id) {
        if (!(model in this.data.records)) return false;
        return id in this.data.records[model];
    }
    _getNextId() {
        return uuidv4();
    }
    /**
     * Creates the default order and returns it.
     */
    _createDefaultOrder() {
        const sequenceNumber = this.session.sequence_number;
        const uid = this._generateOrderUID(sequenceNumber);
        this.session.sequence_number++;
        const newOrder = this.createRecord(
            'pos.order',
            {
                id: uid,
                fiscal_position_id: this.config.default_fiscal_position_id,
                pricelist_id: this.config.pricelist_id,
                sequence_number: sequenceNumber,
                session_id: this.session.id,
                user_id: this.user.id,
                state: 'draft',
            },
            this._defaultOrderExtras(uid)
        );
        return newOrder;
    }
    _defaultOrderExtras(uid) {
        return {
            uid,
            activeScreen: 'ProductScreen',
            ReceiptScreen: {
                inputEmail: '',
                // if null, email is not yet sent
                emailSuccessful: null,
                emailNotice: '',
            },
            printed: 0,
            deleted: false,
        };
    }
    _createOrderline(vals, extras) {
        return this.createRecord('pos.order.line', vals, extras);
    }
    /**
     * Returns true if the given screen can be set a active screen of an order.
     * @param {string} screen
     * @return {boolean}
     */
    _shouldSetScreenToOrder(screen) {
        return ['ProductScreen', 'PaymentScreen', 'ReceiptScreen'].includes(screen);
    }
    /**
     * Sets the given screen as activeScreen of the given order.
     * @param {'pos.order'} order
     * @param {string} screen one of the available screens
     */
    _setScreenToOrder(order, screen) {
        order._extras.activeScreen = screen;
    }
    /**
     * Returns true if line2merge can be merged with existingLine.
     */
    _canBeMergedWith(existingLine, line2merge) {
        const existingLineUnit = this.getOrderlineUnit(existingLine);
        const existingLineProduct = this.getRecord('product.product', existingLine.product_id);
        if (existingLine.product_id !== line2merge.product_id) {
            return false;
        } else if (!existingLineUnit || !existingLineUnit.is_pos_groupable) {
            return false;
        } else if (existingLine.discount > 0 && !this.floatEQ(existingLine.discount, line2merge.discount)) {
            return false;
        } else if (
            existingLineProduct.tracking == 'lot' &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots)
        ) {
            return false;
        } else if (existingLine._extras.description !== line2merge._extras.description) {
            return false;
        } else if (!this.monetaryEQ(this.getOrderlineUnitPrice(existingLine), this.getOrderlineUnitPrice(line2merge))) {
            return false;
        } else {
            return true;
        }
    }
    _getProductSearchString(product) {
        let str = product.display_name;
        if (product.barcode) {
            str += '|' + product.barcode;
        }
        if (product.default_code) {
            str += '|' + product.default_code;
        }
        if (product.description) {
            str += '|' + product.description;
        }
        if (product.description_sale) {
            str += '|' + product.description_sale;
        }
        return product.id + ':' + str.replace(/:/g, '') + '\n';
    }
    _getPartnerSearchString(partner) {
        let str = partner.name || '';
        if (partner.barcode) {
            str += '|' + partner.barcode;
        }
        const address = this.getAddress(partner);
        if (address) {
            str += '|' + address;
        }
        if (partner.phone) {
            str += '|' + partner.phone.split(' ').join('');
        }
        if (partner.mobile) {
            str += '|' + partner.mobile.split(' ').join('');
        }
        if (partner.email) {
            str += '|' + partner.email;
        }
        if (partner.vat) {
            str += '|' + partner.vat;
        }
        str = '' + partner.id + ':' + str.replace(':', '').replace(/\n/g, ' ') + '\n';
        return str;
    }
    _setLatestWriteDate(model, date) {
        this.data.derived.latestWriteDates[model] = date;
    }
    _getShouldBeConfigured(product) {
        return (
            this.config.product_configurator &&
            _.some(product.attribute_line_ids, (id) => id in this.data.derived.attributes_by_ptal_id)
        );
    }
    /**
     * @param {{ [number]: number }} linesTaxDetails map of tax id to the tax amount
     * @return {{ amount: number, tax: 'account.tax', name: string }}
     */
    _getOrderTaxDetails(linesTaxDetails) {
        const details = {};
        for (const taxDetail of linesTaxDetails) {
            for (const id in taxDetail) {
                if (details[id]) {
                    details[id] += taxDetail[id];
                } else {
                    details[id] = taxDetail[id];
                }
            }
        }
        return Object.keys(details).map((taxId) => {
            const tax = this.getRecord('account.tax', taxId);
            return {
                amount: details[taxId],
                tax: tax,
                name: tax.name,
            };
        });
    }
    _generateOrderUID(sequenceNumber) {
        // Generates a public identification number for the order.
        // The generated number must be unique and sequential. They are made 12 digit long
        // to fit into EAN-13 barcodes, should it be needed
        const zero_pad = (num, size) => {
            let s = '' + num;
            while (s.length < size) {
                s = '0' + s;
            }
            return s;
        };
        return zero_pad(this.session.id, 5) + '-' + zero_pad(odoo.login_number, 3) + '-' + zero_pad(sequenceNumber, 4);
    }
    /**
     * @param {'pos.pack.operation.lot'[]} existingPackLots
     * @param {{ id: string | undefined, text: string }[]} modifications
     * @return {[{ id: string, text: string }[], { text: string }[], Set<string>]}
     */
    _getPackLotChanges(existingPackLots, modifications) {
        const toUpdate = [];
        const toAdd = [];
        const toRemove = [];
        for (const modif of modifications) {
            if (modif.id) {
                toUpdate.push({ id: modif.id, text: modif.text });
            } else {
                toAdd.push({ text: modif.text });
            }
        }
        const toUpdateIds = new Set(toUpdate.map((item) => item.id));
        for (const existingLot of existingPackLots) {
            if (!toUpdateIds.has(existingLot.id)) {
                toRemove.push(existingLot.id);
            }
        }
        return [toUpdate, toAdd, new Set(toRemove)];
    }
    roundAmount(amount) {
        const prec = this.cashRounding.rounding;
        const method = this.cashRounding.rounding_method;
        return posRound(amount, prec, method, this.POS_N_DECIMALS);
    }
    /**
     * Returns the formatted value based on the session's currency or explicitly provided
     * currency. Number of decimal places will be based on the currency's decimal places
     * or on the digits of provided precision name.
     * @param {number} value
     * @param {object} [options]
     * @param {string?} [options.precisionName]
     * @param {'res.currency'?} [options.currency]
     * @param {boolean?} [options.withSymbol]
     */
    formatValue(value, options = {}) {
        const currency = options.currency || this.currency;
        let decimalPlaces = currency.decimal_places;
        if (options.precisionName) {
            const dp = this.getDecimalPrecision(options.precisionName);
            // Would be nice to log a warning if dp is not found. It might not be loaded
            // or the provided name is invalid.
            decimalPlaces = dp ? dp.digits : decimalPlaces;
        }
        return options.withSymbol
            ? format.monetary(value, undefined, { currency, digits: [false, decimalPlaces], forceString: true })
            : format.float(value, undefined, { currency, digits: [false, decimalPlaces] });
    }
    formatCurrency(value, precisionName = false) {
        const currency = this.currency;
        return this.formatValue(value, { currency, precisionName, withSymbol: true });
    }
    formatCurrencyNoSymbol(value, precisionName = false) {
        const currency = this.currency;
        return this.formatValue(value, { currency, precisionName, withSymbol: false });
    }
    /**
     * Returns the fields info of the given model.
     * @param {string} model
     * @return {object}
     */
    getModelFields(model) {
        return this.data.fields[model];
    }
    /**
     * Creates a model record based on the given vals and extras.
     * @param {string} model name of the ORM model
     * @param {object} vals an object to create the record
     * @param {object} extras saved to `_extras` field of a record
     */
    createRecord(model, vals, extras) {
        const fields = this.getModelFields(model);
        if (!fields) throw new Error(`No field definitions for '${model}' model.`);
        const record = {};
        for (const name in fields) {
            const fieldsInfo = fields[name];
            switch (fieldsInfo.type) {
                case 'integer':
                case 'float':
                case 'monetary':
                    record[name] = vals[name] || 0;
                    break;
                case 'many2many':
                case 'one2many':
                    record[name] = vals[name] || [];
                    break;
                case 'boolean':
                case 'many2one':
                    record[name] = vals[name] || false;
                    break;
                case 'datetime':
                case 'date':
                    // Set date as string so that it's not a speciale case during
                    // serialization (e.g. saving to localStorage). Convert it
                    // to Date object when necessary.
                    record[name] = vals[name] || new Date().toISOString();
                    break;
                case 'text':
                case 'char':
                    record[name] = vals[name] || '';
                    break;
                case 'selection':
                    const choices = fieldsInfo.selection;
                    record[name] = vals[name] || choices[0];
                default:
                    record[name] = vals[name] || false;
                    break;
            }
        }
        // _extras field will be the container of information that is not defined in the orm model
        if (extras) {
            record._extras = extras;
        }
        this.data.records[model][record.id] = record;
        return record;
    }
    /**
     * Returns a model record of the given id.
     * @param {string} model
     * @param {string | number} id
     */
    getRecord(model, id) {
        if (!(model in this.data.records)) return undefined;
        return this.data.records[model][id];
    }
    /**
     * Returns all the records of the given model, filtered using
     * the given predicate.
     * @param {string} model
     * @return {object[]}
     */
    getRecords(model) {
        if (!(model in this.data.records)) return [];
        if (model in this.data.sortedIds) {
            return this.data.sortedIds[model].map((id) => this.getRecord(model, id));
        } else {
            return Object.values(this.data.records[model]);
        }
    }
    /**
     * Manually set an `obj` as a record of a `model`.
     * @param {string} model
     * @param {string | number} id
     * @param {object} obj object that is compatible as record of `model`
     * @param {object | undefined} extras _extras to be set for the obj
     */
    setRecord(model, id, obj, extras) {
        if (extras) {
            if ('_extras' in obj) {
                Object.assign(obj._extras, extras);
            } else {
                Object.assign(obj, { _extras: extras });
            }
        }
        this.data.records[model][id] = obj;
    }
    /**
     * Clones a record for a given model.
     * @param {string} model
     * @param {object} record
     * @param {object} [newVals] used to override existing fields of the cloned record
     * @return {object} cloned record
     */
    cloneRecord(model, record, newVals = {}) {
        const newObj = cloneDeep(record, newVals);
        this.data.records[model][newObj.id] = newObj;
        return newObj;
    }
    /**
     * Updates the record of the given id and model using the given vals.
     * @param {string} model
     * @param {object} record
     * @param {object} vals
     * @return {object} modified record
     */
    updateRecord(model, id, vals, extras) {
        if (!vals) vals = {};
        if (!extras) extras = {};
        const record = this.getRecord(model, id);
        if (!record) {
            throw new Error('No record found to update.');
        }
        const fields = this.getModelFields(model);
        for (const field in vals) {
            if (!(field in fields)) continue;
            record[field] = vals[field];
        }
        for (const field in extras) {
            record._extras[field] = extras[field];
        }
        return record;
    }
    /**
     * Deletes the model record of the given id.
     * @param {string} model
     * @param {string | number} id
     */
    deleteRecord(model, id) {
        delete this.data.records[model][id];
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
            taxes.sort(function (tax1, tax2) {
                return tax1.sequence - tax2.sequence;
            });
            _(taxes).each(function (tax) {
                if (tax.amount_type === 'group')
                    all_taxes = _collect_taxes(
                        tax.children_tax_ids.map((id) => self.getRecord('account.tax', id)),
                        all_taxes
                    );
                else all_taxes.push(tax);
            });
            return all_taxes;
        };
        var collect_taxes = function (taxes) {
            return _collect_taxes(taxes, []);
        };

        taxes = collect_taxes(taxes);

        // 2) Deal with the rounding methods

        var round_tax = this.company.tax_calculation_rounding_method != 'round_globally';

        var initial_currency_rounding = currency_rounding;
        if (!round_tax) currency_rounding = currency_rounding * 0.00001;

        // 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
        var recompute_base = function (base_amount, fixed_amount, percent_amount, division_amount) {
            return (((base_amount - fixed_amount) / (1.0 + percent_amount / 100.0)) * (100 - division_amount)) / 100;
        };

        var base = round_precision(price_unit * quantity, initial_currency_rounding);

        var sign = 1;
        if (base < 0) {
            base = -base;
            sign = -1;
        }

        var total_included_checkpoints = {};
        var i = taxes.length - 1;
        var store_included_tax_total = true;

        var incl_fixed_amount = 0.0;
        var incl_percent_amount = 0.0;
        var incl_division_amount = 0.0;

        var cached_tax_amounts = {};
        if (handle_price_include) {
            _(taxes.reverse()).each(function (tax) {
                if (tax.include_base_amount) {
                    base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount);
                    incl_fixed_amount = 0.0;
                    incl_percent_amount = 0.0;
                    incl_division_amount = 0.0;
                    store_included_tax_total = true;
                }
                if (tax.price_include) {
                    if (tax.amount_type === 'percent') incl_percent_amount += tax.amount;
                    else if (tax.amount_type === 'division') incl_division_amount += tax.amount;
                    else if (tax.amount_type === 'fixed') incl_fixed_amount += quantity * tax.amount;
                    else {
                        var tax_amount = self._compute_all(tax, base, quantity);
                        incl_fixed_amount += tax_amount;
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

        var total_excluded = round_precision(
            recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount),
            initial_currency_rounding
        );
        var total_included = total_excluded;

        // 4) Iterate the taxes in the sequence order to fill missing base/amount values.

        base = total_excluded;

        var skip_checkpoint = false;

        var taxes_vals = [];
        i = 0;
        var cumulated_tax_included_amount = 0;
        _(taxes.reverse()).each(function (tax) {
            const tax_base_amount = tax.price_include || tax.is_base_affected ? base : total_excluded;

            if (!skip_checkpoint && tax.price_include && total_included_checkpoints[i] !== undefined) {
                var tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount);
                cumulated_tax_included_amount = 0;
            } else {
                var tax_amount = self._compute_all(tax, tax_base_amount, quantity, true);
            }

            tax_amount = round_precision(tax_amount, currency_rounding);

            if (tax.price_include && total_included_checkpoints[i] === undefined)
                cumulated_tax_included_amount += tax_amount;

            taxes_vals.push({
                id: tax.id,
                name: tax.name,
                amount: sign * tax_amount,
                base: sign * round_precision(tax_base_amount, currency_rounding),
            });

            if (tax.include_base_amount) {
                base += tax_amount;
                if (!tax.price_include) {
                    skip_checkpoint = true;
                }
            }

            total_included += tax_amount;
            i += 1;
        });

        return {
            taxes: taxes_vals,
            total_excluded: sign * round_precision(total_excluded, this.currency.rounding),
            total_included: sign * round_precision(total_included, this.currency.rounding),
        };
    }
    /**
     * Mirror JS method of:
     * _compute_amount in addons/account/models/account.py
     */
    _compute_all(tax, base_amount, quantity, price_exclude) {
        if (price_exclude === undefined) var price_include = tax.price_include;
        else var price_include = !price_exclude;
        if (tax.amount_type === 'fixed') {
            var sign_base_amount = Math.sign(base_amount) || 1;
            // Since base amount has been computed with quantity
            // we take the abs of quantity
            // Same logic as bb72dea98de4dae8f59e397f232a0636411d37ce
            return tax.amount * sign_base_amount * Math.abs(quantity);
        }
        if (tax.amount_type === 'percent' && !price_include) {
            return (base_amount * tax.amount) / 100;
        }
        if (tax.amount_type === 'percent' && price_include) {
            return base_amount - base_amount / (1 + tax.amount / 100);
        }
        if (tax.amount_type === 'division' && !price_include) {
            return base_amount / (1 - tax.amount / 100) - base_amount;
        }
        if (tax.amount_type === 'division' && price_include) {
            return base_amount - base_amount * (tax.amount / 100);
        }
        return false;
    }
    /**
     * Returns the price of the given product based on the given pricelist and quantity.
     * @param {number} productId
     * @param {number} pricelistId
     * @param {number} quantity
     * @return {number}
     */
    _computeProductPrice(productId, pricelistId, quantity) {
        const product = this.getRecord('product.product', productId);
        const pricelist = this.getRecord('product.pricelist', pricelistId);
        const date = moment().startOf('day');

        if (pricelist === undefined) {
            return product.lst_price;
        }

        const category_ids = [];
        let categoryId = product.categ_id;
        while (categoryId) {
            category_ids.push(categoryId);
            categoryId = this.getRecord('product.category', categoryId).parent_id;
        }

        const pricelistItems = pricelist.item_ids
            .map((itemId) => this.getRecord('product.pricelist.item', itemId))
            .filter((item) => {
                return (
                    (!item.product_tmpl_id || item.product_tmpl_id === product.product_tmpl_id) &&
                    (!item.product_id || item.product_id === product.id) &&
                    (!item.categ_id || category_ids.includes(item.categ_id)) &&
                    (!item.date_start || moment(item.date_start).isSameOrBefore(date)) &&
                    (!item.date_end || moment(item.date_end).isSameOrAfter(date))
                );
            });

        let price = product.lst_price;
        pricelistItems.find((rule) => {
            if (rule.min_quantity && quantity < rule.min_quantity) {
                return false;
            }

            if (rule.base === 'pricelist') {
                price = this._computeProductPrice(productId, rule.base_pricelist_id, quantity);
            } else if (rule.base === 'standard_price') {
                price = product.standard_price;
            }

            if (rule.compute_price === 'fixed') {
                price = rule.fixed_price;
                return true;
            } else if (rule.compute_price === 'percentage') {
                price = price - price * (rule.percent_price / 100);
                return true;
            } else {
                var price_limit = price;
                price = price - price * (rule.price_discount / 100);
                if (rule.price_round) {
                    price = round_precision(price, rule.price_round);
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
                return true;
            }

            return false;
        });

        // This return value has to be rounded with round_di before
        // being used further. Note that this cannot happen here,
        // because it would cause inconsistencies with the backend for
        // pricelist that have base == 'pricelist'.
        return price;
    }
    /**
     * Compares a and b based on the given decimal digits.
     * @param {number} a
     * @param {number} b
     * @param {number?} decimalPlaces number of decimal digits
     * @return {-1 | 0 | 1} If a and b are equal, returns 0. If a greater than b, returns 1. Otherwise returns -1.
     */
    floatCompare(a, b, decimalPlaces) {
        return posFloatCompare(a, b, decimalPlaces || this.POS_N_DECIMALS);
    }
    floatEQ(a, b, decimalPlaces) {
        return this.floatCompare(a, b, decimalPlaces) === 0;
    }
    floatLT(a, b, decimalPlaces) {
        return this.floatCompare(a, b, decimalPlaces) === -1;
    }
    floatLTE(a, b, decimalPlaces) {
        return this.floatCompare(a, b, decimalPlaces) <= 0;
    }
    floatGT(a, b, decimalPlaces) {
        return this.floatCompare(a, b, decimalPlaces) === 1;
    }
    floatGTE(a, b, decimalPlaces) {
        return this.floatCompare(a, b, decimalPlaces) >= 0;
    }
    /**
     * Compares monetary amounts a and b. Comparison is based on the
     * currencies decimal places.
     * @param {number} a
     * @param {number} b
     * @return {-1 | 0 | 1} If a and b are equal, returns 0. If a greater than b, returns 1. Otherwise returns -1.
     */
    monetaryCompare(a, b) {
        return posFloatCompare(a, b, this.currency.decimal_places);
    }
    monetaryEQ(a, b) {
        return this.monetaryCompare(a, b) === 0;
    }
    monetaryLT(a, b) {
        return this.monetaryCompare(a, b) === -1;
    }
    monetaryLTE(a, b) {
        return this.monetaryCompare(a, b) <= 0;
    }
    monetaryGT(a, b) {
        return this.monetaryCompare(a, b) === 1;
    }
    monetaryGTE(a, b) {
        return this.monetaryCompare(a, b) >= 0;
    }
    /**
     * @param {'pos.order'} order
     * @param {string} email
     * @param {HTMLElement} receiptEl
     */
    async _sendReceipt(order, email, receiptEl) {
        if (!receiptEl) throw new Error("receipt can't be null");
        if (!is_email(email)) {
            return { successful: false, message: _t('Invalid email.') };
        }
        try {
            const printer = new Printer();
            const receiptString = receiptEl.outerHTML;
            const ticketImage = await printer.htmlToImg(receiptString);
            const client = this.getRecord('res.partner', order.partner_id);
            const orderName = this.getOrderName(order);
            const orderClient = {
                email,
                name: client ? client.name : email,
            };
            const order_server_id = order._extras.server_id;
            await this.uirpc({
                model: 'pos.order',
                method: 'action_receipt_to_customer',
                args: [[order_server_id], orderName, orderClient, ticketImage],
            });
            return { successful: true, message: _t('Email sent.') };
        } catch (error) {
            return { successful: false, message: _t('Sending email failed. Please try again.') };
        }
    }
    /**
     * Returns the tip orderline of the given order.
     * @param {'pos.order'} order
     */
    _getTipLine(order) {
        return this.getOrderlines(order).find((line) => line.product_id === this.config.tip_product_id);
    }
    /**
     * Returns the current tip amount of the given order.
     * @param {'pos.order'} order
     */
    _getExistingTipAmount(order) {
        const tipLine = this._getTipLine(order);
        if (!tipLine) return 0;
        return this.getOrderlineUnitPrice(tipLine);
    }
    /**
     * Sets as tip the provided amount to the order. Removes the tip
     * if the given amount is zero.
     * @param {'pos.order'} order
     * @param {number} amount
     * @returns {'pos.order.line' | undefined} tip orderline
     */
    async _setTip(order, amount) {
        const tipLine = this._getTipLine(order);
        const amountIsZero = this.monetaryEQ(amount, 0);
        if (tipLine) {
            if (amountIsZero) {
                await this.actionDeleteOrderline(order, tipLine);
                return;
            } else {
                this.updateRecord('pos.order.line', tipLine.id, { price_unit: amount, qty: 1 });
                return tipLine;
            }
        } else {
            if (amountIsZero) return;
            const tipProduct = this.getRecord('product.product', this.config.tip_product_id);
            const tipLine = await this.actionAddProduct(order, tipProduct, {
                qty: 1,
                price_unit: amount,
                price_manually_set: true,
            });
            const { priceWithTax } = this.getOrderlinePrices(tipLine);
            this.updateRecord('pos.order', order.id, {
                is_tipped: true,
                tip_amount: priceWithTax,
            });
            return tipLine;
        }
    }
    /**
     * Returns true if the given order has at least one cash payment.
     * @param {'pos.order'} order
     * @return {boolean}
     */
    _hasCashPayments(order) {
        const payments = order.payment_ids.map((id) => this.getRecord('pos.payment', id));
        return _.some(payments, (payment) => {
            const paymentMethod = this.getRecord('pos.payment.method', payment.payment_method_id);
            return paymentMethod.is_cash_count;
        });
    }
    /**
     * Remove the payments that are not done from the given order.
     * @param {'pos.order'} order
     */
    _cleanPayments(order) {
        const payments = this.getPayments(order);
        const paymentsToKeep = [];
        const paymentsToDelete = [];
        for (const payment of payments) {
            if (payment.payment_status && payment.payment_status !== 'done') {
                paymentsToDelete.push(payment);
            } else {
                paymentsToKeep.push(payment);
            }
        }
        for (const toDelete of paymentsToDelete) {
            this.deleteRecord('pos.payment', toDelete.id);
        }
        this.updateRecord('pos.order', order.id, { payment_ids: paymentsToKeep.map((payment) => payment.id) });
    }
    /**
     * Wraps the `_pushOrders` method to perform extra procedures.
     * It deletes the pushed orders if they're supposed to be deleted,
     * or persist them to make sure what is saved in the localStorage
     * is updated.
     * @param {'pos.order'[]} orders
     */
    async _syncOrders(orders) {
        await this._pushOrders(orders);
        for (const order of orders) {
            if (order._extras.deleted) {
                this._tryDeleteOrder(order);
            } else {
                // Persist each order because each was updated during the
                // _pushOrders call, new information has been added.
                this.persistOrder(order);
            }
        }
    }
    /**
     * Saves multiple orders to the backend in one request. It also
     * sets the _extras.server_id and account_move to the corresponding order.
     * @param {'pos.order'[]} orders
     * @param {boolean} [draft=false]
     * @return {Promise<{ pos_reference: string, id: number, account_move: number }[]>}
     */
    async _pushOrders(orders, draft = false) {
        const orderData = orders.map((order) => {
            return { id: order.id, data: this.getOrderJSON(order) };
        });
        const result = await this.uirpc(
            {
                model: 'pos.order',
                method: 'create_from_ui',
                args: [orderData, draft],
                kwargs: { context: env.session.user_context },
            },
            {
                timeout: 30000,
            }
        );
        // IMPROVEMENT: can be optimized if the create_from_ui returns
        // mapping of pos_reference to the id, from O(n2) to O(n).
        for (const { id, pos_reference, account_move } of result) {
            for (const order of orders) {
                if (this.getOrderName(order) === pos_reference) {
                    order._extras.server_id = id;
                    order.account_move = account_move;
                }
            }
        }
        return result;
    }
    /**
     * Saves an order to the backend.
     * @param {'pos.order'} order
     * @return {Promise<{ pos_reference: string, id: number, account_move: number } | undefined>}
     */
    async _pushOrder(order) {
        try {
            const result = await this._pushOrders([order]);
            return result[0];
        } catch (error) {
            if (error.message && error.message.code < 0) {
                this.ui.askUser('OfflineErrorPopup', {
                    title: _t('Unable to sync order'),
                    body: _t(
                        'Check the internet connection then try to sync again by clicking on the red wifi button (upper right of the screen).'
                    ),
                    show: this.data.uiState.showOfflineError,
                });
            } else if (error.message && error.message.code === 200) {
                this.ui.askUser('ErrorTracebackPopup', {
                    title: error.message.data.message || _t('Server Error'),
                    body: error.message.data.debug || _t('The server encountered an error while receiving your order.'),
                });
            } else {
                this.ui.askUser('ErrorPopup', {
                    title: _t('Unknown Error'),
                    body: _t('The order could not be sent to the server due to an unknown error'),
                });
            }
            throw error;
        }
    }
    /**
     * This is a hook method during `actionValidateOrder` which is called (and awaited)
     * after pushing the order to the backend but before any invoicing.
     * @param {'pos.order'} order
     */
    async _postPushOrder(order) {}
    /**
     * @param {'pos.order'} order
     */
    async _invoiceOrder(order) {
        try {
            await this.webClient.do_action('point_of_sale.pos_invoice_report', {
                additional_context: {
                    active_ids: [order._extras.server_id],
                },
            });
        } catch (error) {
            this.ui.askUser('ErrorPopup', {
                title: _t('Please print the invoice from the backend'),
                body:
                    _t(
                        'The order has been synchronized earlier. Please make the invoice from the backend for the order: '
                    ) + this.getOrderName(order),
            });
            throw error;
        }
    }
    _cannotRemoveOrderLine() {
        return false;
    }
    /**
     * @param {{
     *  'pos.order': object[],
     *  'pos.order.line': object[],
     *  'pos.payment': object[],
     *  'pos.pack.operation.lot': object[]
     * }} data
     * @param {Set<number>} closedOrders ids of closed orders
     */
    loadManagementOrders(data, closedOrders) {
        let extras = {};
        for (const model in data) {
            for (const record of data[model]) {
                if (model === 'pos.order') {
                    this.data.uiState.OrderManagementScreen.managementOrderIds.add(record.id);
                    extras = { isFromClosedSession: closedOrders.has(record.id), server_id: record.id };
                }
                this.setRecord(model, record.id, record, extras);
                extras = {};
            }
        }
    }
    /**
     * Deletes the order with the given id and it's related records (orderline, payment, etc).
     * @param {string | number} orderId
     */
    deleteOrder(orderId) {
        const order = this.getRecord('pos.order', orderId);
        const orderlines = this.getOrderlines(order);
        for (const orderline of orderlines) {
            for (const lotId of orderline.pack_lot_ids) {
                this.deleteRecord('pos.pack.operation.lot', lotId);
            }
            this.deleteRecord('pos.order.line');
        }
        for (const paymentId of order.payment_ids) {
            this.deleteRecord('pos.payment', paymentId);
        }
        this.deleteRecord('pos.order', orderId);
        this.removePersistedOrder(order);
    }
    /**
     * @param {'pos.order'} order
     * @param {'pos.order.line'} line
     * @param {boolean} [select = true]
     */
    async addOrderline(order, line, select = true) {
        this.updateRecord('pos.order.line', line.id, { order_id: order.id });
        this.updateRecord('pos.order', order.id, { lines: [...order.lines, line.id] });
        if (select) {
            order._extras.activeOrderlineId = line.id;
        }
    }
    /**
     * Normal call to the rpc method available in the env.services.
     */
    rpc() {
        return env.services.rpc(...arguments);
    }
    /**
     * Wrapped call of the rpc method with a side-effect of updating the ui.
     * When the rpc started, the wifi icon at the top right of the screen is changed
     * to a spinner. After the rpc resolved, the icon returned to green icon. However,
     * if there is an error, the icon becomes red.
     */
    async uirpc() {
        try {
            this.ui && this.ui.setSyncStatus('connecting');
            const result = await this.rpc(...arguments);
            this.ui && this.ui.setSyncStatus('connected');
            return result;
        } catch (error) {
            this.ui && this.ui.setSyncStatus('disconnected');
            throw error;
        }
    }
    /**
     * If the order should be synced and is not yet properly synced because
     * of missing `_extras.server_id`, then it should not be removed from
     * ram and from localStorage. Instead, flag it as `deleted`. It will completely
     * be deleted during @see actionSyncOrders.
     * @param {'pos.order'} order
     */
    _tryDeleteOrder(order) {
        if (order._extras.validationDate && !order._extras.server_id) {
            order._extras.deleted = true;
        } else {
            this.deleteOrder(order.id);
        }
    }
    /**
     * @return {Promise<string>}
     */
    async renderCustomerDisplay() {
        const order = this.getActiveOrder();
        const orderlines = this.getOrderlines(order);
        for (const line of orderlines) {
            const product = this.getRecord('product.product', line.product_id);
            if (product._extras && product._extras.image_base64) continue;
            // If we're using an external device like the IoT Box, we
            // cannot get /web/image?model=product.product because the
            // IoT Box is not logged in and thus doesn't have the access
            // rights to access product.product. So instead we'll base64
            // encode it and embed it in the HTML.
            product._extras = { image_base64: await this._getProductImageBase64(product) };
        }
        return qweb.render('point_of_sale.CustomerFacingDisplayOrder', {
            order,
            model: this,
            origin: window.location.origin,
        });
    }
    /**
     * @return {Promise<string>}
     */
    _getProductImageBase64(product) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('CANVAS');
                const ctx = canvas.getContext('2d');
                canvas.height = img.height;
                canvas.width = img.width;
                ctx.drawImage(img, 0, 0);
                resolve(canvas.toDataURL('image/jpeg'));
            };
            img.crossOrigin = 'use-credentials';
            img.src = `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        });
    }
    async _updateCustomerDisplay() {
        const renderedHtml = await this.renderCustomerDisplay();
        if (this.customerDisplayWindow) {
            const $renderedHtml = $('<div>').html(renderedHtml);
            $(this.customerDisplayWindow.document.body).html($renderedHtml.find('.pos-customer_facing_display'));
            const orderlines = $(this.customerDisplayWindow.document.body).find('.pos_orderlines_list');
            orderlines.scrollTop(orderlines.prop('scrollHeight'));
        } else {
            this.proxy.update_customer_facing_display(renderedHtml);
        }
    }
    /**
     * Call this when setting new active order. This makes sure that the
     * previous active order is persisted properly before being replaced.
     * @param {string | number} orderId
     */
    _setActiveOrderId(orderId) {
        const currentActiveOrder = this.getActiveOrder();
        if (currentActiveOrder) this.persistOrder(currentActiveOrder);
        this.data.uiState.activeOrderId = orderId;
    }
    /**
     * Loads the given order data to ram.
     * @param {object} orderData
     * @param {'pos.order'} orderData.order
     * @param {'pos.order.line'[]} orderData.orderlines
     * @param {'pos.payment'[]} orderData.payments
     * @param {'pos.pack.operation.lot'[]} orderData.packlots
     */
    _loadOrderData({ order, orderlines, payments, packlots }) {
        if (!order) return;
        this.setRecord('pos.order', order.id, order);
        for (const line of orderlines) {
            this.setRecord('pos.order.line', line.id, line);
        }
        for (const payment of payments) {
            this.setRecord('pos.payment', payment.id, payment);
        }
        for (const lot of packlots) {
            this.setRecord('pos.pack.operation.lot', lot.id, lot);
        }
    }
    /**
     * Stops the existing electronic payment request.
     * @param {'pos.order'} order
     */
    async _stopElectronicPayment(order) {
        const payments = this.getPayments(order);
        const waitingPayment = payments.find(function (payment) {
            const status = payment.payment_status;
            return status && !['done', 'reversed', 'reversing', 'pending', 'retry'].includes(status);
        });
        if (waitingPayment) {
            await this.actionSendPaymentCancel(order, waitingPayment);
        }
    }
    /**
     * Create an array of starting screens with priority number. The priority
     * number is used for sorting the screens. The one with lowest priority value
     * will be prioritized as the starting screen. @see getStartScreen
     *
     * @returns {[string, number][]}
     */
    _getStartScreens(activeOrder) {
        const result = [];
        if (activeOrder) {
            result.push([this.getOrderScreen(activeOrder), 100]);
        }
        return result;
    }
    _getDefaultScreen() {
        return 'ProductScreen';
    }
    /**
     * Activate this feature by overriding `_shouldActivateActivityListeners` to return true.
     *
     * If this feature is active, the `_onAfterIdleCallback` is called whenever none of the
     * `_getNonIdleEvents()` is not triggered during `_getIdleDuration()`. But the callback is only
     * called when `_shouldTriggerAfterIdleCallback()` returns true.
     * Basically, when the ui is inactive (idle) for a certain duration, it triggers the `_onAfterIdleCallback`.
     *
     * NOTE: This method is in the core module because it affects multiple modules that are supposed to be
     * inpedendent, e.g. pos_hr and pos_restaurant.
     */
    _setActivityListeners() {
        if (!this._shouldActivateActivityListeners()) return;
        for (const event of this._getNonIdleEvents()) {
            window.addEventListener(event, () => {
                clearTimeout(this.idleTimer);
                this.idleTimer = setTimeout(async () => {
                    if (this._shouldTriggerAfterIdleCallback() && this.data.uiState.DebugWidget.idleTimerEnabled) {
                        await this._onAfterIdleCallback();
                    }
                }, this._getIdleDuration());
            });
        }
    }
    _getNonIdleEvents() {
        return ['mousemove', 'mousedown', 'touchstart', 'touchend', 'touchmove', 'click', 'scroll', 'keypress'];
    }
    /**
     * Override this method to return true in order to activate the activity listener feature.
     */
    _shouldActivateActivityListeners() {
        return false;
    }
    /**
     * Override this method to conditionally trigger the `_onAfterIdleCallback`.
     */
    _shouldTriggerAfterIdleCallback() {
        return true;
    }
    /**
     * This method is called when the UI is idle for a duration of `_getIdleDuration()`.
     */
    async _onAfterIdleCallback() {}
    /**
     * Returns the idle duration (in ms) before `_onAfterIdleCallback` is called.
     * Override this to change the default duration of 60s.
     */
    _getIdleDuration() {
        return 60000;
    }
    _manageOrderWhenOrderDone() {
        const ongoingOrders = this.getDraftOrders().filter((order) => {
            return order !== this.getActiveOrder() && order._extras.activeScreen == 'ProductScreen';
        });
        if (!ongoingOrders.length) {
            const newOrder = this._createDefaultOrder();
            this._setActiveOrderId(newOrder.id);
        } else {
            this._setActiveOrderId(ongoingOrders[0].id);
        }
    }
    _deleteOrderline(order, orderline) {
        this.updateRecord('pos.order', order.id, { lines: order.lines.filter((id) => id !== orderline.id) });
        for (const lotId of orderline.pack_lot_ids) {
            this.deleteRecord('pos.pack.operation.lot', lotId);
        }
        this.deleteRecord('pos.order.line', orderline.id);
    }

    //#endregion UTILITY

    //#region LIFECYLE HOOKS

    /**
     * This is an async hook that is called before changing screen. It allows to block
     * the changing of screen when one wants to make a network request that needs to
     * be awaited.
     *
     * /!\ ATTENTION: Make sure to not overwhelm this method so that changing screen
     * is still fast.
     *
     * NOTE: willUnmount is not async so this hook is introduced.
     *
     * @param {string} prevScreen
     * @param {string} nextScreen
     */
    async beforeChangeScreen(prevScreen, nextScreen) {
        if (prevScreen === 'PaymentScreen') {
            await this._stopElectronicPayment(this.getActiveOrder());
        }
    }

    //#endregion LIFECYLE HOOKS

    //#region PERSISTENCE OF ORDERS

    /**
     * Returns a string which serves a key to localStorage to save the order.
     * @param {'pos.order'} order
     * @return {string}
     */
    _constructPersistKey(order) {
        return `odoo-pos-data/${this.config.uuid}/${order.session_id}/${order.id}`;
    }
    /**
     * Deconstructs the string created by _constructPersistKey.
     * @param {string} key
     * @return {[string, string, string]}
     */
    _desconstructPersistKey(key) {
        return key.split('/');
    }
    /**
     * Persist the given order to the localStorage.
     * @param {'pos.order'} order
     */
    persistOrder(order) {
        if (!order) return;
        const orderlines = this.getOrderlines(order);
        const payments = this.getPayments(order);
        const packlots = orderlines
            .map((line) => line.pack_lot_ids.map((lotId) => this.getRecord('pos.pack.operation.lot', lotId)))
            .flat();
        const orderData = JSON.stringify({ order, orderlines, payments, packlots });
        this.storage.setItem(this._constructPersistKey(order), orderData);
    }
    /**
     * Persist to the localStorage the active order.
     */
    persistActiveOrder() {
        this.persistOrder(this.getActiveOrder());
    }
    removePersistedOrder(order) {
        this.storage.removeItem(this._constructPersistKey(order));
    }
    recoverPersistedOrders() {
        const ordersToLoad = this._getPersistedOrders();
        for (const [, orderData] of ordersToLoad) {
            this._loadOrderData(orderData);
        }
    }
    /**
     * Returns all the persisted orders in the localStorage that belong to the config of the
     * opened session. May include orders from closed sessions -- those that are not properly
     * synced.
     * @return {[
     *  string,
     *  {
     *      order: 'pos.order',
     *      orderlines: 'pos.order.line'[],
     *      payments: 'pos.payment'[],
     *      packlots: 'pos.pack.operation.lot'[]
     *  }
     * ][]}
     */
    _getPersistedOrders() {
        const orderData = [];
        for (const [key, orderJSON] of Object.entries(this.storage)) {
            const [prefix, configUUID] = this._desconstructPersistKey(key);
            if (!(prefix === 'odoo-pos-data' && configUUID === this.config.uuid)) continue;
            orderData.push([key, JSON.parse(orderJSON)]);
        }
        return orderData;
    }
    getPersistedPaidOrders() {
        return this._getPersistedOrders().filter(([, item]) => item.order._extras.validationDate);
    }
    getPersistedUnpaidOrders() {
        return this._getPersistedOrders().filter(([, item]) => !item.order._extras.validationDate);
    }

    //#endregion PERSISTENCE OF ORDERS

    //#region ACTIONS

    /**
     * @see PointOfSaleUI.mounted
     */
    async actionDoneLoading() {
        this.data.uiState.isLoading = false;
        const startScreen = this.getStartScreen();
        this._setActivityListeners();
        await this.actionShowScreen(startScreen);
    }
    actionSetActiveCategoryId(categoryId) {
        this.data.uiState.activeCategoryId = categoryId;
    }
    /**
     * Opens the EditListPopup to modify the pack lots of the given orderline.
     * @param {'pos.order.line'} orderline
     * @return {{ cancelled: boolean }}
     */
    async actionSetOrderlineLots(orderline) {
        const product = this.getRecord('product.product', orderline.product_id);
        const currentPackLots = orderline.pack_lot_ids.map((lotId) => this.getRecord('pos.pack.operation.lot', lotId));
        const isSingleItem = product.tracking === 'lot';
        const dialogTitle = isSingleItem ? _t('A Lot Number Required') : _t('Serial Numbers Required');
        const [confirm, modifiedPackLots] = await this.ui.askUser('EditListPopup', {
            title: dialogTitle,
            array: currentPackLots.map((lot) => ({ id: lot.id, text: lot.lot_name })),
            isSingleItem,
        });
        if (!confirm) return { cancelled: true };
        const [toUpdate, toAdd, toRemove] = this._getPackLotChanges(currentPackLots, modifiedPackLots);
        for (const item of toUpdate) {
            this.updateRecord('pos.pack.operation.lot', item.id, { lot_name: item.text });
        }
        for (const item of toAdd) {
            const newLot = this.createRecord(
                'pos.pack.operation.lot',
                {
                    id: this._getNextId(),
                    lot_name: item.text,
                },
                {}
            );
            orderline.pack_lot_ids.push(newLot.id);
        }
        for (const id of toRemove) {
            this.deleteRecord('pos.pack.operation.lot', id);
        }
        orderline.pack_lot_ids = orderline.pack_lot_ids.filter((id) => !toRemove.has(id));
        // automatically set the quantity to the number of lots.
        orderline.qty = orderline.pack_lot_ids.length;
        return { cancelled: false };
    }
    /**
     * @param {'pos.order'} order
     * @param {'product.product'} product
     * @param {Object} [vals] additional field values in creating `pos.order.line`
     * @param {number?} [vals.qty]
     * @param {number?} [vals.price_unit]
     * @param {number?} [vals.discount]
     * @return {'pos.order.line'?} created/updated orderline
     */
    async actionAddProduct(order, product, vals, extras) {
        if (!vals) vals = {};
        if (!extras) extras = {};
        if (this._getShouldBeConfigured(product)) {
            const attributes = product.attribute_line_ids
                .map((id) => this.data.derived.attributes_by_ptal_id[id])
                .filter((attr) => attr !== undefined);
            const [confirmed, productConfig] = await this.ui.askUser('ProductConfiguratorPopup', {
                product: product,
                attributes: attributes,
            });
            if (confirmed) {
                extras.description = productConfig.selected_attributes.join(', ');
                extras.price_extra = productConfig.price_extra;
            } else {
                return;
            }
        }
        const line = this._createOrderline(
            {
                id: this._getNextId(),
                product_id: product.id,
                order_id: order.id,
                qty: vals.qty || 1,
                price_unit: vals.price_unit,
                discount: vals.discount,
                price_manually_set: vals.price_manually_set || false,
            },
            extras
        );
        const mergeWith = this.getOrderlines(order).find((existingLine) => this._canBeMergedWith(existingLine, line));
        if (mergeWith && !line._extras.dontMerge) {
            if (product.tracking === 'serial') {
                const { cancelled } = await this.actionSetOrderlineLots(mergeWith);
                if (cancelled) return;
            } else {
                await this.actionUpdateOrderline(mergeWith, { qty: mergeWith.qty + line.qty });
            }
            this.actionSelectOrderline(order, mergeWith.id);
            return mergeWith;
        } else {
            if (product.tracking === 'serial' || product.tracking === 'lot') {
                const { cancelled } = await this.actionSetOrderlineLots(line);
                if (cancelled) {
                    this.deleteRecord('pos.order.line', line.id);
                    return;
                }
            }
            await this.addOrderline(order, line);
            return line;
        }
    }
    actionSelectOrderline(order, lineID) {
        order._extras.activeOrderlineId = lineID;
    }
    async actionUpdateOrderline(orderline, vals) {
        if ('price_unit' in vals) {
            vals['price_manually_set'] = true;
        }
        if ('discount' in vals) {
            if (vals['discount'] > 100) {
                vals['discount'] = 100;
            }
        }
        this.updateRecord('pos.order.line', orderline.id, vals);
    }
    /**
     * Deletes the given orderline from the lines of the given order.
     * If the orderline is the active orderline in the order, set a new active orderline.
     * @param {'pos.order'} order
     * @param {'pos.order.line'} orderline
     */
    async actionDeleteOrderline(order, orderline) {
        // Do not set new active orderline if the line being deleted is not
        // the active orderline.
        const isActiveOrderline = this.getActiveOrderline(order) === orderline;
        // needed to set the new active orderline
        const indexOfDeleted = order.lines.indexOf(orderline.id);
        this._deleteOrderline(order, orderline);
        if (order.lines.length && isActiveOrderline) {
            // set as active the orderline with the same index as the deleted
            if (indexOfDeleted === order.lines.length) {
                this.actionSelectOrderline(order, order.lines[order.lines.length - 1]);
            } else {
                this.actionSelectOrderline(order, order.lines[indexOfDeleted]);
            }
        }
    }
    /**
     * This action is called if decreasing the quantity of an orderline is not allowed.
     * @alias actionDecreaseQuantityPopup
     */
    async actionShowDecreaseQuantityPopup(orderline) {
        const order = this.getRecord('pos.order', orderline.order_id);
        const groupedOrderlines = this.getGroupedOrderlines(this.getOrderlines(order));
        const relatedOrderlines = groupedOrderlines[orderline.id].map((id) => this.getRecord('pos.order.line', id));
        const currentQuantity = sum([orderline, ...relatedOrderlines], (line) => line.qty);
        const [confirm, inputNumber] = await this.ui.askUser('NumberPopup', {
            startingValue: currentQuantity,
            title: _t('Set the new quantity'),
            isInputSelected: true,
        });
        if (!confirm || (confirm && inputNumber === '')) return;
        const newQuantity = parse.float(inputNumber);
        if (this.floatGTE(newQuantity, currentQuantity)) {
            this.actionUpdateOrderline(orderline, { qty: orderline.qty - currentQuantity + newQuantity });
        } else {
            const decreasedQuantity = currentQuantity - newQuantity;
            const newLine = this.cloneRecord('pos.order.line', orderline, {
                qty: -decreasedQuantity,
                id: this._getNextId(),
            });
            order.lines.push(newLine.id);
            this.actionSelectOrderline(order, newLine.id);
        }
    }
    /**
     * Change the `activeScreen` using the given `screen` and set, if needed,
     * the given screen to the active order.
     * Before actually changing the activeScreen, the `beforeChangeScreen` hook
     * is called. If some state variables needs to adapt when changing screen,
     * the said hook is the good place to change them.
     * @param {string} screen
     */
    async actionShowScreen(screen, props) {
        if (!props) props = {};
        const prevScreen = this.getActiveScreen();
        if (prevScreen === screen) return;
        await this.beforeChangeScreen(prevScreen, screen);
        if (this._shouldSetScreenToOrder(screen)) {
            this._setScreenToOrder(this.getActiveOrder(), screen);
        }
        this.data.uiState.previousScreen = prevScreen;
        this.data.uiState.activeScreen = screen;
        this.data.uiState.activeScreenProps = props;
    }
    async actionSelectOrder(order) {
        if (this.data.uiState.OrderManagementScreen.managementOrderIds.has(order.id)) {
            this.data.uiState.OrderManagementScreen.activeOrderId = order.id;
        } else {
            this._setActiveOrderId(order.id);
            await this.actionShowScreen(this.getOrderScreen(order));
        }
    }
    actionDeleteOrder(order) {
        if (this.getOrderlines(order).length && this._cannotRemoveOrderLine()) {
            this.ui.askUser('ErrorPopup', {
                title: _t('POS Error'),
                body: _t('Deleting orders is not allowed.'),
            });
            return;
        }
        const activeOrderIsDeleted = this.getActiveOrder().id === order.id;
        this._tryDeleteOrder(order);
        if (activeOrderIsDeleted) {
            const orders = this.getOrdersSelection();
            if (orders.length) {
                this._setActiveOrderId(orders[0].id);
            }
        }
    }
    actionCreateNewOrder() {
        const newOrder = this._createDefaultOrder();
        this.actionSelectOrder(newOrder);
    }
    /**
     * @param {string} screenToToggle
     */
    async actionToggleScreen(screenToToggle) {
        const activeScreen = this.getActiveScreen();
        const screen = activeScreen === screenToToggle ? this.getPreviousScreen() : screenToToggle;
        await this.actionShowScreen(screen);
    }
    /**
     * @param {string} [filter]
     */
    actionSetTicketScreenFilter(filter) {
        this.data.uiState.TicketScreen.filter = filter;
    }
    /**
     * @param {{ field: string, term: string }} [searchDetails]
     */
    actionSetTicketScreenSearchDetails(searchDetails) {
        this.data.uiState.TicketScreen.searchDetails = searchDetails;
    }
    /**
     * Changing the client in an order should also set the pricelist and
     * fiscal position to the order.
     * @param {number | false} [selectedClientId]
     */
    actionSetClient(order, selectedClientId) {
        if (!selectedClientId) {
            this.updateRecord('pos.order', order.id, {
                partner_id: false,
                pricelist_id: this.config.pricelist_id,
                fiscal_position_id: this.config.default_fiscal_position_id,
            });
        } else {
            const customer = this.getRecord('res.partner', selectedClientId);
            // It is possible that customer is set with property_product_pricelist but it's value
            // is not loaded because it is not included in the list of pricelist set in pos.config.
            // Same is true for the property_account_position_id of the customer.
            const customerPricelist =
                this.getRecord('product.pricelist', customer.property_product_pricelist) ||
                this.getRecord('product.pricelist', this.config.pricelist_id);
            const customerFiscalPosition =
                this.getRecord('account.fiscal.position', customer.property_account_position_id) ||
                this.getRecord('account.fiscal.position', this.config.default_fiscal_position_id);
            this.updateRecord('pos.order', order.id, {
                partner_id: customer.id,
                pricelist_id: customerPricelist ? customerPricelist.id : false,
                fiscal_position_id: customerFiscalPosition ? customerFiscalPosition.id : false,
            });
        }
    }
    async actionLoadUpdatedPartners() {
        const domain = [['write_date', '>', this.getLatestWriteDate('res.partner')]];
        const fieldNames = Object.keys(this.getModelFields('res.partner'));
        try {
            const newPartners = await this.uirpc(
                {
                    model: 'res.partner',
                    method: 'search_read',
                    args: [domain, fieldNames],
                    kwargs: { load: false },
                },
                {
                    timeout: 3000,
                    shadow: true,
                }
            );
            for (const partner of newPartners) {
                this.setRecord('res.partner', partner.id, partner);
            }
            this._setLatestWriteDate('res.partner', maxDateString(...newPartners.map((partner) => partner.write_date)));
            this._setPartnerSearchString();
        } catch (error) {
            console.warn(error);
        }
    }
    /**
     * @param {'pos.order'} order
     * @param {'pos.payment.method'} paymentMethod
     * @param {number | undefined} amount
     */
    actionAddPayment(order, paymentMethod, amount) {
        // Create a new payment record without an amount.
        const newPayment = this.createRecord(
            'pos.payment',
            {
                id: this._getNextId(),
                pos_order_id: order.id,
                payment_method_id: paymentMethod.id,
            },
            {}
        );
        order.payment_ids.push(newPayment.id);
        amount = amount === undefined ? this.getAutomaticPaymentAmount(order, paymentMethod) : amount;
        this.updateRecord('pos.payment', newPayment.id, {
            amount,
            payment_status: this.getPaymentTerminal(paymentMethod.id) ? 'pending' : '',
        });
        order._extras.activePaymentId = newPayment.id;
        return newPayment;
    }
    /**
     * Sets the given payment as the active payment of it's order.
     * @param {'pos.payment'} payment
     */
    actionSelectPayment(payment) {
        const order = this.getRecord('pos.order', payment.pos_order_id);
        order._extras.activePaymentId = payment.id;
    }
    /**
     * Deletes the given payment. Wait to cancel the payment request if the payment
     * is linked to a terminal.
     */
    async actionDeletePayment(payment) {
        const order = this.getRecord('pos.order', payment.pos_order_id);
        if (['waiting', 'waitingCard', 'timeout'].includes(payment.payment_status)) {
            const paymentTerminal = this.getPaymentTerminal(payment.payment_method_id);
            try {
                await paymentTerminal.send_payment_cancel(order, payment.id);
            } catch (error) {
                const confirmed = await this.ui.askUser('ConfirmPopup', {
                    title: _t('Force payment deletion'),
                    body: _t('Failed to cancel terminal payment. Do you wish to force the deletion of the payment?'),
                });
                if (!confirmed) return;
            }
        }
        this.updateRecord('pos.order', order.id, {
            payment_ids: order.payment_ids.filter((paymentId) => paymentId !== payment.id),
        });
        this.deleteRecord('pos.payment', payment.id);
    }
    actionUpdatePayment(payment, vals, extras) {
        this.updateRecord('pos.payment', payment.id, vals, extras);
    }
    /**
     * Render the next screen when done with the currently active order.
     * Create new order and set the created order as active.
     * @param {string} nextScreen name of screen to render
     */
    async actionOrderDone(order, nextScreen) {
        this._manageOrderWhenOrderDone();
        this._tryDeleteOrder(order);
        await this.actionShowScreen(nextScreen);
    }
    /**
     * Set the pricelist of the active order using the given pricelist id.
     * @param {string} pricelistId
     */
    actionSetPricelist(order, pricelistId) {
        this.updateRecord('pos.order', order.id, { pricelist_id: pricelistId });
    }
    /**
     * Set the fiscal position of the active order using the given fiscal position id.
     * @param {string} fiscalPositionId
     */
    actionSetFiscalPosition(order, fiscalPositionId) {
        this.updateRecord('pos.order', order.id, { fiscal_position_id: fiscalPositionId });
    }
    /**
     * @param {'pos.order'} order
     * @param {HTMLElement} receiptEl
     */
    async actionSendReceipt(order, receiptEl) {
        const { successful, message } = await this._sendReceipt(
            order,
            order._extras.ReceiptScreen.inputEmail,
            receiptEl
        );
        order._extras.ReceiptScreen.emailSuccessful = successful;
        order._extras.ReceiptScreen.emailNotice = message;
    }
    actionToggleToInvoice(order) {
        this.updateRecord('pos.order', order.id, { to_invoice: !order.to_invoice });
    }
    actionToggleToShip(order) {
        this.updateRecord('pos.order', order.id, { to_ship: !order.to_ship });
    }
    /**
     * Opens a number popup to ask for the tip amount and adds the tip line accordingly.
     * @see _setTip.
     */
    async actionAddTip(order) {
        const existingTipAmount = this._getExistingTipAmount(order);
        const hasTip = !this.monetaryEQ(existingTipAmount, 0);
        const startingValue = hasTip ? existingTipAmount : this.getOrderChange(order);
        const [confirmed, amountStr] = await this.ui.askUser('NumberPopup', {
            title: hasTip ? _t('Change Tip') : _t('Add Tip'),
            startingValue,
        });
        if (confirmed) {
            const amount = parse.float(amountStr);
            await this._setTip(order, amount);
        }
    }
    /**
     * Responsible for delegating the send_payment_request to the correct payment terminal
     * of the given payment.
     * @param {'pos.order'} order
     * @param {'pos.payment'} payment
     * @param {any[]} otherArgs optional args that is passed to send_payment_request
     */
    async actionSendPaymentRequest(order, payment, ...otherArgs) {
        for (const _payment of this.getPayments(order)) {
            if (_payment !== payment) {
                // Other payments can not be reversed anymore.
                _payment._extras.can_be_reversed = false;
            }
        }
        await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'waiting'] });
        const paymentTerminal = this.getPaymentTerminal(payment.payment_method_id);
        const isPaymentSuccessful = await paymentTerminal.send_payment_request(payment.id, ...otherArgs);
        if (isPaymentSuccessful) {
            payment._extras.can_be_reversed = paymentTerminal.supports_reversals;
            await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'done'] });
        } else {
            await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'retry'] });
        }
    }
    /**
     * Responsible for delegating the send_payment_cancel to the correct payment terminal
     * of the given payment.
     * @param {'pos.order'} order
     * @param {'pos.payment'} payment
     * @param {any[]} otherArgs optional args that is passed to send_payment_cancel
     */
    async actionSendPaymentCancel(order, payment, ...otherArgs) {
        const paymentTerminal = this.getPaymentTerminal(payment.payment_method_id);
        const prevPaymentStatus = payment.payment_status;
        await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'waitingCancel'] });
        try {
            await paymentTerminal.send_payment_cancel(order, payment.id, ...otherArgs);
            await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'retry'] });
        } catch (error) {
            await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, prevPaymentStatus] });
        }
    }
    /**
     * Responsible for delegating the send_payment_reversal to the correct payment terminal
     * of the given payment.
     * @param {'pos.order'} order
     * @param {'pos.payment'} payment
     * @param {any[]} otherArgs optional args that is passed to send_payment_reversal
     */
    async actionSendPaymentReverse(order, payment, ...otherArgs) {
        const paymentTerminal = this.getPaymentTerminal(payment.payment_method_id);
        await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'reversing'] });
        const isReversalSuccessful = await paymentTerminal.send_payment_reversal(payment.id, ...otherArgs);
        if (isReversalSuccessful) {
            payment.amount = 0;
            await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'reversed'] });
        } else {
            await this._actionHandler({ name: 'actionSetPaymentStatus', args: [payment, 'done'] });
        }
    }
    actionSetPaymentStatus(payment, status) {
        payment.payment_status = status;
    }
    actionSetReceiptInfo(payment, value) {
        payment.ticket += value;
    }
    /**
     * When an order has enough payment, it can be validated. Validating an order is done in
     * several steps:
     * - remove payments that are not done (or not counted)
     * - opens the cashbox if there is a cash payment
     * - saves the order to the server
     * - invoices the order is necessary
     * - then show the next screen
     * @param {'pos.order'} order
     * @param {string} nextScreen
     */
    async actionValidateOrder(order, nextScreen) {
        this._cleanPayments(order);
        if (this._hasCashPayments(order) && this.proxy.printer && this.config.iface_cashdrawer) {
            this.proxy.printer.open_cashbox();
        }
        try {
            order._extras.validationDate = new Date().toISOString();
            await this._pushOrder(order);
            await this._postPushOrder(order);
            if (order.to_invoice) {
                await this._invoiceOrder(order);
            }
        } finally {
            await this.actionShowScreen(nextScreen);
        }
    }
    /**
     * Sync remaining unsynced orders.
     */
    async actionSyncOrders() {
        const unsyncedOrders = this.getOrdersToSync();
        if (!unsyncedOrders.length) return;
        await this._syncOrders(unsyncedOrders);
    }
    async actionsetNPerPage(val) {
        await this.orderFetcher.setNPerPage(val);
    }
    async actionSearch(domain) {
        await this.orderFetcher.setSearchDomain(domain);
    }
    async actionNextPage() {
        await this.orderFetcher.nextPage();
    }
    async actionPrevPage() {
        await this.orderFetcher.prevPage();
    }
    /**
     * Action to return to the backend. Before closing pos, unsynced paid orders are
     * tried again to sync.
     */
    async actionClosePos() {
        const ordersToSync = this.getOrdersToSync();
        if (!ordersToSync.length) {
            window.location = '/web#action=point_of_sale.action_client_pos_menu';
        } else {
            // If there are orders in the db left unsynced, we try to sync.
            // If sync successful, close without asking.
            // Otherwise, ask again saying that some orders are not yet synced.
            try {
                await this._syncOrders(ordersToSync);
                window.location = '/web#action=point_of_sale.action_client_pos_menu';
            } catch (error) {
                if (error instanceof Error) throw error;
                let message;
                if (error.message && error.message.code === 200) {
                    message = _t(
                        'Some orders could not be submitted to ' +
                            'the server due to configuration errors. ' +
                            'You can exit the Point of Sale, but do ' +
                            'not close the session before the issue ' +
                            'has been resolved.'
                    );
                } else {
                    message = _t(
                        'Some orders could not be submitted to ' +
                            'the server due to internet connection issues. ' +
                            'You can exit the Point of Sale, but do ' +
                            'not close the session before the issue ' +
                            'has been resolved.'
                    );
                }
                const confirmed = await this.ui.askUser('ConfirmPopup', {
                    title: _t('Offline Orders'),
                    body: message,
                });
                if (confirmed) {
                    window.location = '/web#action=point_of_sale.action_client_pos_menu';
                }
            }
        }
    }
    /**
     * This removes orders from ram and from localStorage. Takes `orders` param
     * with signature similar to the return of @see _getPersistedOrders.
     */
    async actionRemoveOrders(orders) {
        for (const [key, { order }] of orders) {
            this.storage.removeItem(key);
            if (this.exists('pos.order', order.id)) {
                this.deleteOrder(order.id);
            }
        }
        // If the active order is also deleted, we make sure to set a new one.
        if (!this.getActiveOrder()) {
            const orders = this.getDraftOrders();
            // IMPROVEMENT: perhaps select the order next to the deleted one instead of the first order
            const orderToSet = orders.length ? orders[0] : this._createDefaultOrder();
            this._setActiveOrderId(orderToSet.id);
            await this.actionShowScreen(this.getOrderScreen(this.getActiveOrder()));
        }
    }
    /**
     * This imports paid or unpaid orders from a json file whose
     * contents are provided as the string str.
     * It returns a report of what could and what could not be
     * imported.
     */
    actionImportOrders(str) {
        const json = JSON.parse(str);
        const report = {
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
            for (const [key, orderData] of json.paid_orders) {
                this._loadOrderData(orderData);
                this.storage.setItem(key, JSON.stringify(orderData));
            }
            report.paid = json.paid_orders.length;
        }
        if (json.unpaid_orders) {
            let ordersToLoad = [];
            const skipped_sessions = {};
            for (const [key, orderData] of json.unpaid_orders) {
                const order = orderData.order;
                if (order.session_id !== this.session.id) {
                    report.unpaid_skipped_session += 1;
                    skipped_sessions[order.session_id] = true;
                } else if (this.exists('pos.order', order.id)) {
                    report.unpaid_skipped_existing += 1;
                } else {
                    ordersToLoad.push([key, orderData]);
                }
            }
            // IMPROVEMENT: Is this sorting necessary?
            ordersToLoad = ordersToLoad.sort(function (a, b) {
                const [, { order: orderA }] = a;
                const [, { order: orderB }] = b;
                return orderA.sequence_number - orderB.sequence_number;
            });
            for (const [key, orderData] of ordersToLoad) {
                this._loadOrderData(orderData);
                this.storage.setItem(key, JSON.stringify(orderData));
            }
            report.unpaid = ordersToLoad.length;
            report.unpaid_skipped_sessions = _.keys(skipped_sessions);
        }
        return report;
    }
    async actionPrintSalesDetails() {
        const saleDetails = await this.uirpc({
            model: 'report.point_of_sale.report_saledetails',
            method: 'get_sale_details',
            args: [false, false, false, [this.session.id]],
        });
        const report = qweb.render(
            'point_of_sale.SaleDetailsReport',
            Object.assign({}, saleDetails, {
                date: new Date().toLocaleString(),
                model: this,
            })
        );
        // IMPROVEMENT: Allow downloading the report as image/pdf.
        // Strategy used in `htmlToImg` can be employed.
        if (this.proxy.printer) {
            const printResult = await this.proxy.printer.print_receipt(report);
            if (!printResult.successful) {
                await this.ui.askUser('ErrorPopup', {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
            }
        }
    }
    /**
     * If no product data is loaded, install the onboarding data is she likes,
     * otherwise, do nothing.
     */
    async actionLoadDemoData() {
        const confirmed = await this.ui.askUser('ConfirmPopup', {
            title: _t('You do not have any products'),
            body: _t('Would you like to load demo data?'),
            confirmText: _t('Yes'),
            cancelText: _t('No'),
        });
        if (confirmed) {
            await this.uirpc({
                route: '/pos/load_onboarding_data',
            });
            const { products, categories } = await this.uirpc({
                model: 'pos.session',
                method: 'get_onboarding_data',
                args: [],
            });
            this.data.records['product.product'] = products;
            this.data.records['pos.category'] = categories;
            this._setupProducts();
        }
    }
    actionShowSkipButton() {
        this.data.uiState.LoadingScreen.skipButtonIsShown = true;
    }

    //#endregion ACTIONS

    //#region GETTERS

    getLatestWriteDate(model) {
        return this.data.derived.latestWriteDates[model];
    }
    getActiveScreen() {
        return this.data.uiState.activeScreen;
    }
    getActiveScreenProps() {
        return Object.assign({}, this.data.uiState.activeScreenProps, { activeOrder: this.getActiveOrder() });
    }
    /**
     * Returns the active screen of the given order.
     * @param {'pos.order'} order
     * @return {string}
     */
    getOrderScreen(order) {
        if (!order) return this._getDefaultScreen();
        return order._extras.activeScreen || 'ProductScreen';
    }
    getActiveOrder() {
        return this.getRecord('pos.order', this.data.uiState.activeOrderId);
    }
    /**
     * Returns the translated name of the order.
     * @param {'pos.order'} order
     * @return {string}
     */
    getOrderName(order) {
        if (order.pos_reference) return order.pos_reference;
        return _.str.sprintf(_t('Order %s'), order._extras.uid);
    }
    /**
     * Calculates all the total amounts of the given order.
     * @param {'pos.order'} order
     * @return {{
     *  noTaxNoDiscount: number,
     *  noTaxWithDiscount: number,
     *  withTaxWithDiscount: number,
     *  withTaxNoDiscount: number,
     *  totalTax: number,
     *  orderTaxDetails: { amount: number, tax: 'account.tax', name: string }
     * }}
     */
    getOrderTotals(order) {
        const orderlines = this.getOrderlines(order);
        let noTaxNoDiscount = 0,
            noTaxWithDiscount = 0,
            withTaxNoDiscount = 0,
            withTaxWithDiscount = 0,
            totalTax = 0;
        const linesTaxDetails = [];
        for (const line of orderlines) {
            const {
                priceWithTax,
                priceWithoutTax,
                noDiscountPriceWithTax,
                noDiscountPriceWithoutTax,
                tax,
                taxDetails,
            } = this.getOrderlinePrices(line);
            noTaxNoDiscount += noDiscountPriceWithoutTax;
            noTaxWithDiscount += priceWithoutTax;
            withTaxNoDiscount += noDiscountPriceWithTax;
            withTaxWithDiscount += priceWithTax;
            totalTax += tax;
            linesTaxDetails.push(taxDetails);
        }
        const orderTaxDetails = this._getOrderTaxDetails(linesTaxDetails);
        return {
            noTaxNoDiscount,
            noTaxWithDiscount,
            withTaxNoDiscount,
            withTaxWithDiscount,
            totalTax,
            orderTaxDetails,
        };
    }
    /**
     * Returns the required amount to be paid of the given order.
     * @param {'pos.order'} order
     * @return {number}
     */
    getAmountToPay(order) {
        return this.getOrderTotals(order).withTaxWithDiscount;
    }
    /**
     * Returns the total amount of the payments of the given order.
     * @param {'pos.order'} order
     * @return {number}
     */
    getPaymentsTotalAmount(order) {
        const donePayments = this.getPayments(order).filter((payment) =>
            payment.payment_status ? payment.payment_status === 'done' : true
        );
        return sum(donePayments, (payment) => payment.amount);
    }
    getAutomaticPaymentAmount(order, paymentMethod) {
        const due = this.getOrderDue(order);
        const shouldBeRounded = this.getShouldBeRounded(paymentMethod);
        return shouldBeRounded ? this.roundAmount(due) : due;
    }
    /**
     * Returns the change of the given order.
     * @param {'pos.order'} order
     * @return {number}
     */
    getOrderChange(order) {
        const shouldRound = this.data.derived.roundingScheme !== 'NO_ROUNDING';
        const due = this._getRemainingAmountToPay(order, shouldRound);
        return this.monetaryLT(due, 0) ? -due : 0;
    }
    getShouldBeRounded(paymentMethod) {
        const scheme = this.data.derived.roundingScheme;
        return scheme === 'ONLY_CASH_ROUNDING' ? paymentMethod.is_cash_count : scheme === 'WITH_ROUNDING';
    }
    /**
     * Returns the remaining amount to pay.
     * @param {'pos.order'} order
     * @return {number}
     */
    getOrderDue(order) {
        return this.getIsOrderPaid(order) ? 0 : this._getRemainingAmountToPay(order);
    }
    /**
     * @param {'pos.order'} order
     * @param {boolean} shouldRound if false, it ignores any rounding.
     * @return {number}
     */
    _getRemainingAmountToPay(order, shouldRound) {
        const payments = this.getPayments(order);
        const amountToPay = this.getAmountToPay(order);
        const totalPaymentAmount = sum(payments, (payment) => payment.amount);
        const diff = amountToPay - totalPaymentAmount;
        return shouldRound ? this.roundAmount(diff) : diff;
    }
    /**
     * Returns the ancestor ids of the given category.
     * @param {number} categoryId
     * @return {number[]}
     */
    getCategoryAncestorIds(categoryId) {
        return this.data.derived.categoryAncestors[categoryId] || [];
    }
    /**
     * Returns the partners which are compatible to the given query string. It however only returns
     * max of `searchLimit` items.
     * @param {string | undefined | null } queryString
     * @return {'res.partner'[]}
     */
    getPartners(queryString) {
        const partnerIds = [];
        if (!queryString) return this.getRecords('res.partner').slice(0, this.searchLimit);
        queryString = queryString.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.').replace(/ /g, '.+');
        const re = RegExp('([0-9]+):.*?' + unaccent(queryString), 'gi');
        for (let i = 0; i < this.searchLimit; i++) {
            const r = re.exec(this.data.derived.partnerSearchString);
            if (r) {
                partnerIds.push(r[1]);
            } else {
                break;
            }
        }
        return partnerIds.map((id) => this.getRecord('res.partner', id));
    }
    /**
     * Returns the products of the given pos category which satisfies the given search string.
     * Number of items returned is limited to `searchLimit`.
     * @param {string} categoryId
     * @param {string} searchTerm
     * @return {'product.product'[]}
     */
    getProducts(categoryId, searchTerm) {
        if (!searchTerm) {
            const productIds = [...(this.data.derived.productsByCategoryId[categoryId] || [])];
            return productIds.map((productId) => this.getRecord('product.product', productId));
        }
        try {
            const query = searchTerm
                .replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.')
                .replace(/ /g, '.+');
            const re = RegExp('([0-9]+):.*?' + unaccent(query), 'gi');
            const results = [];
            for (let i = 0; i < this.searchLimit; i++) {
                const r = re.exec(this.data.derived.categorySearchStrings[categoryId]);
                if (r) {
                    const res = this.getRecord('product.product', r[1]);
                    if (res) results.push(res);
                } else {
                    break;
                }
            }
            return results;
        } catch (e) {
            return [];
        }
    }
    /**
     * Returns all the orders including those that are fetched from the backend.
     * @return {'pos.order'[]}
     */
    getOrders(predicate) {
        return this.getRecords('pos.order').filter(predicate);
    }
    getUndeletedOrders() {
        return this.getOrders((order) => order.session_id === odoo.pos_session_id && !order._extras.deleted);
    }
    /**
     * Returns an array of orders as selection for setting the active order.
     * @return {'pos.order'[]}
     */
    getOrdersSelection() {
        return this.getDraftOrders();
    }
    /**
     * Returns the draft orders -- those without state or has state == 'draft and those
     * not flagged as `deleted`.
     * @return {'pos.order'[]}
     */
    getDraftOrders() {
        return this.getUndeletedOrders().filter((order) => !order.state || order.state === 'draft');
    }
    getPaidOrders() {
        return this.getUndeletedOrders().filter((order) => ['paid', 'invoice'].includes(order.state));
    }
    /**
     * @param {'pos.order' | undefined} order
     * @return {'pos.order.line'[]}
     */
    getOrderlines(order) {
        if (!order) return [];
        return order.lines.map((lineId) => this.getRecord('pos.order.line', lineId));
    }
    /**
     * @param {'pos.order'} order
     * @return {'pos.payment'[]}
     */
    getPayments(order) {
        return order.payment_ids.map((paymentId) => this.getRecord('pos.payment', paymentId));
    }
    /**
     * @param {string} name
     * @returns {'decimal.precision'}
     */
    getDecimalPrecision(name) {
        return this.data.derived.decimalPrecisionByName[name];
    }
    /**
     * Returns the pricelist of the given order.
     * @param {string | number} orderId
     * @return {'product.pricelist'}
     */
    getOrderPricelist(orderId) {
        const order = this.getRecord('pos.order', orderId);
        return this.getRecord('product.pricelist', order.pricelist_id);
    }
    /**
     * Returns the product that has the given barcode.
     * @param {string} barcode
     * @return {'product.product'}
     */
    getProductByBarcode(barcode) {
        return this.data.derived.productByBarcode[barcode];
    }
    /**
     * Returns the partner that has the given barcode.
     * @param {string} barcode
     * @return {'res.partner'}
     */
    getPartnerByBarcode(barcode) {
        return this.data.derived.partnerByBarcode[barcode];
    }
    /**
     * Returns the unit of the given product.
     * @param {number} productId
     * @return {'uom.uom'}
     */
    getProductUnit(productId) {
        const product = this.getRecord('product.product', productId);
        if (!productId || !product) return false;
        if (!product.uom_id) return false;
        return this.getRecord('uom.uom', product.uom_id);
    }
    /**
     * Returns the raw price of the product based on the given pricelist and quantity.
     * @param {number} productId
     * @param {number} pricelistId
     * @param {number} quantity
     * @return {number}
     */
    getProductPrice(productId, pricelistId, quantity) {
        const productPrice = this._computeProductPrice(productId, pricelistId, quantity);
        const dp = this.getDecimalPrecision('Product Price');
        return round_decimals(productPrice, dp.digits);
    }
    /**
     * Returns the taxes of the given orderline. It doesn't take into account the fiscal position.
     * @param {'pos.order.line'} orderline
     * @return {'account.tax'[]}
     */
    getOrderlineTaxes(orderline) {
        const product = this.getRecord('product.product', orderline.product_id);
        const taxIds = orderline.tax_ids.length ? orderline.tax_ids : product.taxes_id;
        return taxIds.map((id) => this.getRecord('account.tax', id)).filter(Boolean);
    }
    /**
     * Converts the given taxes to their fiscal position mapping.
     * @param {'account.tax'} taxes
     * @param {number | false} fiscalPositionId
     * @return {'account.tax'[]}
     */
    getFiscalPositionTaxes(taxes, fiscalPositionId) {
        if (!fiscalPositionId) return taxes;
        const mappedTaxIds = [];
        for (const tax of taxes) {
            const taxMap = this.data.derived.fiscalPositionTaxMaps[fiscalPositionId];
            if (!taxMap[tax.id]) {
                // If a tax isn't mapped, then it should be registered.
                // This is different from a tax mapped to an empty destination.
                // That one is considered in the else clause.
                mappedTaxIds.push(tax.id);
            } else {
                // We filter the result of the tax mapping corresponding to the given tax
                // because a tax may be mapped to an empty destination.
                mappedTaxIds.push(...taxMap[tax.id].filter(Boolean));
            }
        }
        // There should be no duplicates in the mapped taxes.
        return _.uniq(mappedTaxIds).map((taxId) => this.getRecord('account.tax', taxId));
    }
    /**
     * Given a base price (which contains included taxes) and the taxes, this method returns
     * the untaxed and fully-taxed amounts.
     * @param {number} basePrice the base price containing included taxes
     * @param {'account.tax'[]} taxes
     * @return {[number, number]} [untaxed, taxed]
     */
    getUnitPrices(basePrice, taxes = []) {
        if (taxes.length === 0) return [basePrice, basePrice];
        const prices = this.compute_all(taxes, basePrice, 1, this.currency.rounding, true);
        return [prices.total_excluded, prices.total_included];
    }
    /**
     * Returns the unit price of the given orderline.
     * @param {'pos.order.line'} orderline
     * @return {number}
     */
    getOrderlineUnitPrice(orderline) {
        let unitPrice = orderline._extras.price_extra || 0.0;
        const order = this.getRecord('pos.order', orderline.order_id);
        if (orderline.price_manually_set) {
            unitPrice += orderline.price_unit;
        } else {
            unitPrice += this.getProductPrice(orderline.product_id, order.pricelist_id, orderline.qty);
        }
        return unitPrice;
    }
    /**
     * Returns all the prices for the given orderline.
     * @param {'pos.order.line'} orderline
     * @return {{
     *  priceWithTax: number,
     *  priceWithoutTax: number,
     *  noDiscountPriceWithTax: number,
     *  noDiscountPriceWithoutTax: number,
     *  priceSumTaxVoid: number,
     *  tax: number,
     *  taxDetails: Record<number, number>,
     *  unitPrice: number,
     *  noTaxUnitPrice: number,
     *  withTaxUnitPrice: number,
     * }}
     */
    getOrderlinePrices(orderline) {
        const unitPrice = this.getOrderlineUnitPrice(orderline);
        const discountedUnitPrice = unitPrice * (1.0 - orderline.discount / 100.0);
        const order = this.getRecord('pos.order', orderline.order_id);
        const taxes = this.getFiscalPositionTaxes(this.getOrderlineTaxes(orderline), order.fiscal_position_id);
        const rounding = this.currency.rounding;

        const [noTaxUnitPrice, withTaxUnitPrice] = this.getUnitPrices(unitPrice, taxes);
        const allTaxes = this.compute_all(taxes, discountedUnitPrice, orderline.qty, rounding, true);
        const allTaxesBeforeDiscount = this.compute_all(taxes, unitPrice, orderline.qty, rounding, true);

        let taxTotal = 0;
        const taxDetails = {};
        for (const tax of allTaxes.taxes) {
            taxTotal += tax.amount;
            taxDetails[tax.id] = tax.amount;
        }

        return {
            priceWithTax: allTaxes.total_included,
            priceWithoutTax: allTaxes.total_excluded,
            noDiscountPriceWithTax: allTaxesBeforeDiscount.total_included,
            noDiscountPriceWithoutTax: allTaxesBeforeDiscount.total_excluded,
            priceSumTaxVoid: allTaxes.total_void,
            tax: taxTotal,
            taxDetails,
            unitPrice,
            noTaxUnitPrice,
            withTaxUnitPrice,
        };
    }
    getActivePayment(order) {
        return this.getRecord('pos.payment', order._extras.activePaymentId);
    }
    getDiscountPolicy(orderline) {
        const order = this.getRecord('pos.order', orderline.order_id);
        const pricelist = this.getRecord('product.pricelist', order.pricelist_id);
        return pricelist.discount_policy;
    }
    getOrderlineUnit(orderline) {
        const product = this.getRecord('product.product', orderline.product_id);
        const unit = this.getRecord('uom.uom', product.uom_id);
        return unit;
    }
    getFullProductName(orderline) {
        if (orderline.full_product_name) return orderline.full_product_name;
        const product = this.getRecord('product.product', orderline.product_id);
        const description = orderline._extras.description;
        return description ? `${product.display_name} (${description})` : product.display_name;
    }
    getQuantityStr(orderline) {
        const product = this.getRecord('product.product', orderline.product_id);
        const unit = this.getRecord('uom.uom', product.uom_id);
        if (unit) {
            if (unit.rounding) {
                const decimals = this.getDecimalPrecision('Product Unit of Measure').digits;
                return format.float(orderline.qty, { digits: [false, decimals] });
            } else {
                return orderline.qty.toFixed(0);
            }
        } else {
            return '' + orderline.qty;
        }
    }
    getOrderlineDisplayPrice(orderlinePrices) {
        return this.config.iface_tax_included === 'subtotal'
            ? orderlinePrices.priceWithoutTax
            : orderlinePrices.priceWithTax;
    }
    getIsZeroDiscount(orderline) {
        return float_is_zero(orderline.discount, 3);
    }
    getCustomer(order) {
        return this.getRecord('res.partner', order.partner_id) || false;
    }
    getCustomerName(order) {
        const customer = this.getCustomer(order);
        return customer ? customer.name : '';
    }
    getAddress(partner) {
        const state = this.getRecord('res.country.state', partner.state_id);
        const country = this.getRecord('res.country', partner.country_id);
        return (
            (partner.street ? partner.street + ', ' : '') +
            (partner.zip ? partner.zip + ', ' : '') +
            (partner.city ? partner.city + ', ' : '') +
            (state ? state.name + ', ' : '') +
            (country ? country.name : '')
        );
    }
    /**
     * Returns a serializeable version of the order that is compatible as argument
     * to the remote 'pos.order' `create_from_ui` method.
     * @param {'pos.order'} order
     */
    getOrderJSON(order) {
        const orderlines = order.lines.map((lineId) => this.getRecord('pos.order.line', lineId));
        const payments = order.payment_ids.map((paymentId) => this.getRecord('pos.payment', paymentId));
        const { withTaxWithDiscount, totalTax } = this.getOrderTotals(order);
        return {
            name: this.getOrderName(order),
            amount_paid: this.getPaymentsTotalAmount(order) - this.getOrderChange(order),
            amount_total: withTaxWithDiscount,
            amount_tax: totalTax,
            amount_return: this.getOrderChange(order),
            lines: orderlines.map((orderline) => [0, 0, this.getOrderlineJSON(orderline)]),
            statement_ids: payments.map((payment) => [0, 0, this.getPaymentJSON(payment)]),
            pos_session_id: order.session_id,
            pricelist_id: order.pricelist_id,
            partner_id: order.partner_id,
            user_id: order.user_id,
            uid: order._extras.uid,
            sequence_number: order.sequence_number,
            creation_date: order._extras.validationDate || order.date_order,
            fiscal_position_id: order.fiscal_position_id,
            server_id: order._extras.server_id || false,
            to_invoice: order.to_invoice,
            is_tipped: order.is_tipped,
            tip_amount: order.tip_amount || 0,
        };
    }
    /**
     * @param {'pos.order.line'} line
     */
    getOrderlineJSON(line) {
        const { priceWithTax, priceWithoutTax } = this.getOrderlinePrices(line);
        return {
            id: line.id,
            qty: line.qty,
            price_unit: this.getOrderlineUnitPrice(line),
            price_manually_set: line.price_manually_set,
            price_subtotal: priceWithoutTax,
            price_subtotal_incl: priceWithTax,
            discount: line.discount,
            product_id: line.product_id,
            tax_ids: [[6, false, this.getOrderlineTaxes(line).map((tax) => tax.id)]],
            pack_lot_ids: line.pack_lot_ids
                .map((id) => this.getRecord('pos.pack.operation.lot', id))
                .map((lot) => [0, 0, this.getPackLotJSON(lot)]),
            description: line._extras.description,
            full_product_name: this.getFullProductName(line),
        };
    }
    /**
     * @param {'pos.payment'} payment
     */
    getPaymentJSON(payment) {
        return {
            name: time.datetime_to_str(new Date()),
            payment_method_id: payment.payment_method_id,
            amount: payment.amount,
            payment_status: payment.payment_status,
            ticket: payment.ticket,
            card_type: payment.card_type,
            cardholder_name: payment.cardholder_name,
            transaction_id: payment.transaction_id,
            cashier_receipt: payment.cashier_receipt,
        };
    }
    /**
     * @param {'pos.pack.operation.lot'} lot
     */
    getPackLotJSON(lot) {
        return {
            lot_name: lot.lot_name,
        };
    }
    /**
     * @param {'pos.order'} order
     * @return {'pos.order.line' | undefined} orderline
     */
    getActiveOrderline(order) {
        const id = order._extras.activeOrderlineId;
        return id ? this.getRecord('pos.order.line', id) : undefined;
    }
    checkDisallowDecreaseQuantity(orderline, newQuantity) {
        if (!this.shouldDisallowDecreaseQuantity()) return false;
        if (this.isLastOrderline(orderline)) {
            return this.floatGT(orderline.qty, 1) && this.floatLT(newQuantity, orderline.qty);
        } else {
            return this.floatLT(newQuantity, orderline.qty);
        }
    }
    shouldDisallowDecreaseQuantity() {
        return false;
    }
    shouldDisallowOrderlineDeletion() {
        return false;
    }
    /**
     * @param {number} paymentMethodId
     * @param {PaymentInterface}
     */
    getPaymentTerminal(paymentMethodId) {
        const paymentMethod = this.getRecord('pos.payment.method', paymentMethodId);
        if (!paymentMethod) {
            throw new Error(_t('Payment method not found.'));
        }
        if (!paymentMethod.use_payment_terminal) return undefined;
        return this.data.derived.paymentTerminals[paymentMethod.use_payment_terminal];
    }
    /**
     * Checks if the given payment is valid based on the roundingScheme.
     * @param {'pos.payment'} payment
     * @return {boolean}
     */
    isPaymentValidOnRounding(payment) {
        const paymentMethod = this.getRecord('pos.payment.method', payment.payment_method_id);
        const scheme = this.data.derived.roundingScheme;
        let shouldBeRounded;
        if (scheme === 'NO_ROUNDING') {
            shouldBeRounded = false;
        } else if (scheme === 'ONLY_CASH_ROUNDING') {
            shouldBeRounded = paymentMethod.is_cash_count;
        } else {
            shouldBeRounded = true;
        }
        if (!shouldBeRounded) return true;
        const roundedAmount = this.roundAmount(payment.amount);
        return this.monetaryEQ(payment.amount, roundedAmount);
    }
    getIsOrderPaid(order) {
        const shouldRound = this.data.derived.roundingScheme !== 'NO_ROUNDING';
        return this.monetaryLTE(this._getRemainingAmountToPay(order, shouldRound), 0);
    }
    /**
     * Returns the first payment that is not rounded properly.
     * @param {'pos.order'} order
     */
    getInvalidRoundingPayment(order) {
        return this.getPayments(order).find((payment) => !this.isPaymentValidOnRounding(payment));
    }
    getCashierName() {
        return this.user.name;
    }
    /**
     * Return the orders that are supposed to be synced -- meaning, order is validated but it still has no server_id.
     */
    getOrdersToSync() {
        return this.getOrders((order) => order._extras.validationDate && !order._extras.server_id);
    }
    getIsCashierManager() {
        const userGroupIds = (this.user && this.user.groups_id) || [];
        return userGroupIds.includes(this.config.group_pos_manager_id);
    }
    /**
     * Returns the screen with lowest value attached to it from the list of screens
     * returned by `_getStartScreens`.
     */
    getStartScreen() {
        const startScreens = this._getStartScreens(this.getActiveOrder());
        startScreens.sort((a, b) => a[1] - b[1]);
        return startScreens[0][0];
    }
    getUseProxy() {
        return (
            this.config.is_posbox &&
            (this.config.iface_electronic_scale ||
                this.config.iface_print_via_proxy ||
                this.config.iface_scan_via_proxy ||
                this.config.iface_customer_facing_display_via_proxy)
        );
    }
    getPreviousScreen() {
        return this.data.uiState.previousScreen;
    }
    /**
     * Returns the data needed to render the receipt based on the given order.
     * @alias getReceiptInfo
     * @param {'pos.order'} order
     */
    getOrderInfo(order) {
        const orderlines = this.getOrderlines(order).map((line) => this._getOrderlineInfo(line));
        const payments = this.getPayments(order)
            .filter((payment) => !payment.is_change)
            .map((payment) => this._getPaymentInfo(payment));
        const changePayment = this.getPayments(order).find((payment) => payment.is_change);
        const amountPaid = this.getPaymentsTotalAmount(order) - this.getOrderChange(order);
        const company = this.company;

        function is_html(subreceipt) {
            return subreceipt ? subreceipt.split('\n')[0].indexOf('<!DOCTYPE QWEB') >= 0 : false;
        }

        const render_html = (subreceipt, receipt) => {
            if (!is_html(subreceipt)) {
                return subreceipt;
            } else {
                subreceipt = subreceipt.split('\n').slice(1).join('\n');
                const qweb = new QWeb2.Engine();
                qweb.debug = config.isDebug();
                qweb.default_dict = _.clone(QWeb.default_dict);
                qweb.add_template('<templates><t t-name="subreceipt">' + subreceipt + '</t></templates>');
                return qweb.render('subreceipt', { model: this, order, receipt });
            }
        };

        const {
            noTaxNoDiscount,
            noTaxWithDiscount,
            withTaxWithDiscount,
            totalTax,
            orderTaxDetails,
        } = this.getOrderTotals(order);

        const receipt = {
            orderlines,
            paymentlines: payments,
            subtotal: noTaxWithDiscount,
            total_with_tax: withTaxWithDiscount,
            // If amount paid and the total amount are not exactly equal, then the payment is rounded.
            is_payment_rounded: !this.monetaryEQ(amountPaid, withTaxWithDiscount),
            rounding_applied: amountPaid - withTaxWithDiscount,
            total_rounded: amountPaid,
            total_tax: totalTax,
            total_discount: noTaxNoDiscount - noTaxWithDiscount,
            tax_details: orderTaxDetails,
            change: changePayment ? Math.abs(changePayment.amount) : this.getOrderChange(order),
            name: this.getOrderName(order),
            cashier: this.getCashierName(),
            client: this.getCustomer(order),
            date: {
                localestring: format.datetime(moment(order._extras.validationDate), {}, { timezone: false }),
            },
            company: {
                email: company.email,
                website: company.website,
                company_registry: company.company_registry,
                contact_address: this.getRecord('res.partner', company.partner_id).display_name,
                vat: company.vat,
                vat_label: (company.country && company.country.vat_label) || _t('Tax ID'),
                name: company.name,
                phone: company.phone,
                logo: this.data.derived.companyLogoBase64,
            },
            country: this.country,
        };

        if (is_html(this.config.receipt_header)) {
            receipt.header = '';
            receipt.header_html = render_html(this.config.receipt_header, receipt);
        } else {
            receipt.header = this.config.receipt_header || '';
        }

        if (is_html(this.config.receipt_footer)) {
            receipt.footer = '';
            receipt.footer_html = render_html(this.config.receipt_footer, receipt);
        } else {
            receipt.footer = this.config.receipt_footer || '';
        }

        return receipt;
    }
    /**
     * @param {'pos.order.line'} line
     */
    _getOrderlineInfo(line) {
        const order = this.getRecord('pos.order', line.order_id);
        const product = this.getRecord('product.product', line.product_id);
        const unit = this.getProductUnit(line.product_id);
        const pricelist = this.getOrderPricelist(line.order_id);
        const prices = this.getOrderlinePrices(line);
        const unitPrice = this.getOrderlineUnitPrice(line);
        const taxes = this.getFiscalPositionTaxes(this.getOrderlineTaxes(line), order.fiscal_position_id);
        const [noTaxUnitPrice, withTaxUnitPrice] = this.getUnitPrices(unitPrice, taxes);
        let price, price_display;
        if (this.config.iface_tax_included === 'total') {
            price_display = prices.priceWithTax;
            price = withTaxUnitPrice;
        } else {
            price_display = prices.priceWithoutTax;
            price = noTaxUnitPrice;
        }
        return {
            id: line.id,
            quantity: line.qty,
            unit_name: unit.name,
            price,
            discount: line.discount,
            product_name: product.display_name,
            product_name_wrapped: generateWrappedName(this.getFullProductName(line)),
            price_lst: product.lst_price,
            display_discount_policy: pricelist.discount_policy,
            price_display_one: price * (1.0 - line.discount / 100.0),
            price_display,
            price_with_tax: prices.priceWithTax,
            price_without_tax: prices.priceWithoutTax,
            price_with_tax_before_discount: prices.noDiscountPriceWithTax,
            tax: prices.tax,
            product_description: product.description,
            product_description_sale: product.description_sale,
            pack_lot_lines: line.pack_lot_ids.map((id) => this.getRecord('pos.pack.operation.lot', id)),
        };
    }
    /**
     * @param {'pos.payment'} payment
     */
    _getPaymentInfo(payment) {
        const paymentMethod = this.getRecord('pos.payment.method', payment.payment_method_id);
        return {
            id: payment.id,
            amount: payment.amount,
            name: paymentMethod.name,
            ticket: payment.ticket,
        };
    }
    isLastOrderline(orderline) {
        const order = this.getRecord('pos.order', orderline.order_id);
        return order.lines[order.lines.length - 1] === orderline.id;
    }
    /**
     * Given an array of orderlines, return an object that represents the groupings
     * of the orderlines. The return object maps the id of the 'parent' orderline
     * to the ids of the other orderlines that **can be merged** to the 'parent'.
     * E.g.
     *
     * ```js
     * // Input:
     * [
     *  ol1,
     *  ol2,
     *  ol3, // can be merged to ol1
     *  ol4, // can be merged to ol2
     *  ol5, // can be merged to ol1
     *  ol6,
     * ]
     *
     * // Output:
     * {
     *  [ol1.id]: [ol3.id, ol5.id],
     *  [ol2.id]: [ol4.id],
     *  [ol6.id]: [],
     * }
     * ```
     * @param {'pos.order.line'} orderlines
     * @return {{ string: string[] }}
     */
    getGroupedOrderlines(orderlines) {
        const alreadyAddedInGroup = new Set();
        const groupedOrderlines = {};
        for (const line of orderlines) {
            if (alreadyAddedInGroup.has(line) || line.id in groupedOrderlines) continue;
            groupedOrderlines[line.id] = [];
            for (const _line of orderlines) {
                if (line === _line) continue;
                if (this._canBeMergedWith(line, _line)) {
                    groupedOrderlines[line.id].push(_line.id);
                    alreadyAddedInGroup.add(_line);
                }
            }
        }
        return groupedOrderlines;
    }

    //#endregion GETTERS
}

export default PointOfSaleModel;
