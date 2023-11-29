/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, useExternalListener, useState, reactive } from "@odoo/owl";
import { CategorySelector } from "@point_of_sale/app/generic_components/category_selector/category_selector";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { Numpad } from "@point_of_sale/app/generic_components/numpad/numpad";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { ProductInfoPopup } from "./product_info_popup/product_info_popup";
import { fuzzyLookup } from "@web/core/utils/search";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import {
    ControlButtons,
    ControlButtonsPopup,
} from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

export class ProductScreen extends Component {
    static template = "point_of_sale.ProductScreen";
    static components = {
        ActionpadWidget,
        Numpad,
        Orderline,
        OrderWidget,
        CategorySelector,
        Input,
        ControlButtons,
        OrderSummary,
        ProductCard,
    };
    static numpadActionName = _t("Payment");
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.notification = useService("pos_notification");
        this.numberBuffer = useService("number_buffer");
        this.state = useState({
            showProductReminder: false,
            loadingDemo: false,
            scrollDown: false,
            previousSearchWord: "",
            currentOffset: 0,
        });
        onMounted(() => {
            this.pos.openCashControl();

            if (this.pos.config.iface_start_categ_id) {
                this.pos.setSelectedCategoryId(this.pos.config.iface_start_categ_id.id);
            }

            // Call `reset` when the `onMounted` callback in `numberBuffer.use` is done.
            // We don't do this in the `mounted` lifecycle method because it is called before
            // the callbacks in `onMounted` hook.
            this.numberBuffer.reset();
        });
        this.barcodeReader = useService("barcode_reader");
        useExternalListener(window, "click", this.clickEvent.bind(this));

        useBarcodeReader({
            product: this._barcodeProductAction,
            quantity: this._barcodeProductAction,
            weight: this._barcodeProductAction,
            price: this._barcodeProductAction,
            client: this._barcodePartnerAction,
            discount: this._barcodeDiscountAction,
            gs1: this._barcodeGS1Action,
        });

        this.numberBuffer.use({
            useWithBarcode: true,
        });
    }
    setScrollDirection(scroll) {
        this.state.scrollDown = scroll.down;
    }
    getCategories() {
        if (this.pos.selectedCategoryId) {
            const categoriesToDisplay = [];
            const category = this.pos.models["pos.category"].get(this.pos.selectedCategoryId);

            if (category.parent_id) {
                categoriesToDisplay.push(...category.allParents);
            }

            categoriesToDisplay.push(category);

            if (category.child_id) {
                categoriesToDisplay.push(...category.child_id);
            }

            return categoriesToDisplay;
        } else {
            return this.pos.models["pos.category"].filter((category) => !category.parent_id);
        }
    }
    computeImageUrl(category) {
        return `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
    }
    getNumpadButtons() {
        return [
            { value: "1" },
            { value: "2" },
            { value: "3" },
            { value: "quantity", text: "Qty" },
            { value: "4" },
            { value: "5" },
            { value: "6" },
            {
                value: "discount",
                text: "% Disc",
                disabled: !this.pos.config.manual_discount,
            },
            { value: "7" },
            { value: "8" },
            { value: "9" },
            { value: "price", text: "Price", disabled: !this.pos.cashierHasPriceControlRights() },
            { value: "-", text: "+/-" },
            { value: "0" },
            { value: this.env.services.localization.decimalPoint },
            // Unicode: https://www.compart.com/en/unicode/U+232B
            { value: "Backspace", text: "⌫" },
        ].map((button) => ({
            ...button,
            class: this.pos.numpadMode === button.value ? "active border-primary" : "",
        }));
    }
    onNumpadClick(buttonValue) {
        if (["quantity", "discount", "price"].includes(buttonValue)) {
            this.numberBuffer.capture();
            this.numberBuffer.reset();
            this.pos.numpadMode = buttonValue;
            return;
        }
        this.numberBuffer.sendKey(buttonValue);
    }

    clickEvent(e) {
        if (!this.ui.isSmall) {
            return;
        }

        const isProductCard = (() => {
            let element = e.target;
            // 3 because product DOM dept is 3
            for (let i = 0; i < 3; i++) {
                if (element.classList.contains("product")) {
                    return true;
                } else {
                    element = element.parentElement;
                }
            }
            return false;
        })();

        this.state.showProductReminder =
            this.currentOrder &&
            this.currentOrder.get_selected_orderline() &&
            this.selectedOrderlineQuantity &&
            isProductCard;
    }

    /**
     * To be overridden by modules that checks availability of
     * connected scale.
     * @see _onScaleNotAvailable
     */
    get partner() {
        return this.currentOrder ? this.currentOrder.get_partner() : null;
    }
    get currentOrder() {
        return this.pos.get_order();
    }
    get total() {
        return this.env.utils.formatCurrency(this.currentOrder?.get_total_with_tax() ?? 0);
    }
    get items() {
        return this.currentOrder.orderlines?.reduce((items, line) => items + line.quantity, 0) ?? 0;
    }
    async _getProductByBarcode(code) {
        let product = this.pos.models["product.product"].getBy("barcode", code.base_code);

        if (!product) {
            const records = await this.pos.data.callRelated(
                "pos.session",
                "find_product_by_barcode",
                [odoo.pos_session_id, code.base_code]
            );

            if (records && records["product.product"].length > 0) {
                product = records["product.product"][0];
            }
        }

        return product;
    }
    async _barcodeProductAction(code) {
        const product = await this._getProductByBarcode(code);
        if (!product) {
            return this.dialog.add(AlertDialog, {
                title: `Unknown Barcode: ${this.barcodeReader.codeRepr(code)}`,
                body: _t(
                    "The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode."
                ),
            });
        }
        const options = await this.pos.getAddProductOptions(product, code);
        // Do not proceed on adding the product when no options is returned.
        // This is consistent with clickProduct.
        if (!options) {
            return;
        }

        // update the options depending on the type of the scanned code
        if (code.type === "price") {
            Object.assign(options, {
                price: code.value,
                extras: {
                    price_type: "manual",
                },
            });
        } else if (code.type === "weight" || code.type === "quantity") {
            Object.assign(options, {
                quantity: code.value,
                merge: false,
            });
        } else if (code.type === "discount") {
            Object.assign(options, {
                discount: code.value,
                merge: false,
            });
        }
        this.currentOrder.add_product(product, options);
        this.numberBuffer.reset();
    }
    async _getPartnerByBarcode(code) {
        let partner = this.pos.models["res.partner"].getBy("barcode", code.code);
        if (!partner) {
            partner = this.pos.data.searchRead("res.partner", ["barcode", "=", code.code]);
        }
        return partner;
    }
    async _barcodePartnerAction(code) {
        const partner = await this._getPartnerByBarcode(code);
        if (partner) {
            if (this.currentOrder.get_partner() !== partner) {
                this.currentOrder.set_partner(partner);
            }
            return;
        }
        return this.dialog.add(AlertDialog, {
            title: `Unknown Barcode: ${this.barcodeReader.codeRepr(code)}`,
            body: _t(
                "The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode."
            ),
        });
    }
    _barcodeDiscountAction(code) {
        var last_orderline = this.currentOrder.get_last_orderline();
        if (last_orderline) {
            last_orderline.set_discount(code.value);
        }
    }
    async _parseElementsFromGS1(parsed_results) {
        const productBarcode = parsed_results.find((element) => element.type === "product");
        const lotBarcode = parsed_results.find((element) => element.type === "lot");
        const product = await this._getProductByBarcode(productBarcode);
        return { product, lotBarcode, customProductOptions: {} };
    }
    /**
     * Add a product to the current order using the product identifier and lot number from parsed results.
     * This function retrieves the product identifier and lot number from the `parsed_results` parameter.
     * It then uses these values to retrieve the product and add it to the current order.
     */
    async _barcodeGS1Action(parsed_results) {
        const { product, lotBarcode, customProductOptions } = await this._parseElementsFromGS1(
            parsed_results
        );
        if (!product) {
            const productBarcode = parsed_results.find((element) => element.type === "product");
            return this.dialog.add(AlertDialog, {
                title: `Unknown Barcode: ${this.barcodeReader.codeRepr(productBarcode)}`,
                body: _t(
                    "The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode."
                ),
            });
        }
        const options = await this.pos.getAddProductOptions(product, lotBarcode);
        await this.currentOrder.add_product(product, { ...options, ...customProductOptions });
        this.numberBuffer.reset();
    }
    displayAllControlPopup() {
        this.dialog.add(ControlButtonsPopup, {
            controlButtons: this.controlButtons,
        });
    }
    get selectedOrderlineQuantity() {
        return this.currentOrder.get_selected_orderline()?.get_quantity_str();
    }
    get selectedOrderlineDisplayName() {
        return this.currentOrder.get_selected_orderline()?.get_full_product_name();
    }
    get selectedOrderlineTotal() {
        return this.env.utils.formatCurrency(
            this.currentOrder.get_selected_orderline()?.get_display_price()
        );
    }
    /**
     * This getter is used to restart the animation on the product-reminder.
     * When the information present on the product-reminder will change,
     * the key will change and thus a new product-reminder will be created
     * and the old one will be garbage collected leading to the animation
     * being retriggered.
     */
    get animationKey() {
        return [
            this.currentOrder.get_selected_orderline()?.uuid,
            this.selectedOrderlineQuantity,
            this.selectedOrderlineDisplayName,
            this.selectedOrderlineTotal,
        ].join(",");
    }

    get showProductReminder() {
        return this.currentOrder.get_selected_orderline() && this.selectedOrderlineQuantity;
    }
    switchPane() {
        this.pos.switchPane();
    }
    get selectedCategoryId() {
        return this.pos.selectedCategoryId;
    }
    get searchWord() {
        return this.pos.searchProductWord.trim();
    }

    get productsToDisplay() {
        let list = [];

        if (this.searchWord !== "") {
            const product = this.pos.selectedCategoryId
                ? this.pos.models["product.product"].getBy(
                      "pos_categ_ids",
                      this.pos.selectedCategoryId
                  )
                : this.pos.models["product.product"].getAll();
            list = fuzzyLookup(
                this.searchWord,
                product,
                (product) => product.display_name + product.description_sale
            );
        } else if (this.pos.selectedCategoryId) {
            list = this.pos.models["product.product"].getBy(
                "pos_categ_ids",
                this.pos.selectedCategoryId
            );
        } else {
            list = this.pos.models["product.product"].getAll();
        }

        list = list
            .filter((product) => !this.getProductListToNotDisplay().includes(product.id))
            .slice(0, 100);

        return list.sort(function (a, b) {
            return a.display_name.localeCompare(b.display_name);
        });
    }

    getProductListToNotDisplay() {
        return [this.pos.config.tip_product_id, ...this.pos.pos_special_products_ids];
    }

    async loadDemoDataProducts() {
        this.state.loadingDemo = true;
        try {
            const result = await this.pos.data.loadServerMethodTemp(
                "pos.session",
                "load_product_frontend",
                [odoo.pos_session_id]
            );
            const models = result.related;
            const posOrder = result.posOrder;

            if (!models) {
                this.dialog.add(AlertDialog, {
                    title: _t("Demo products are no longer available"),
                    body: _t(
                        "A valid product already exists for Point of Sale. Therefore, demonstration products cannot be loaded."
                    ),
                });
            }

            for (const dataName of ["pos.category", "product.product", "pos.order"]) {
                if (!models[dataName] && Object.keys(posOrder).length === 0) {
                    this._showLoadDemoDataMissingDataError(dataName);
                }
            }

            if (this.pos.models["product.product"].length > 5) {
                this.pos.has_available_products = true;
            }

            this.pos.loadOpenOrders(posOrder);
        } finally {
            this.state.loadingDemo = false;
        }
    }

    _showLoadDemoDataMissingDataError(missingData) {
        console.error(
            "Missing '",
            missingData,
            "' in pos.session:load_product_frontend server answer."
        );
    }

    async onPressEnterKey() {
        const { searchProductWord } = this.pos;
        if (!searchProductWord) {
            return;
        }
        if (this.state.previousSearchWord !== searchProductWord) {
            this.state.currentOffset = 0;
        }
        const result = await this.loadProductFromDB();
        if (result.length > 0) {
            this.notification.add(
                _t('%s product(s) found for "%s".', result.length, searchProductWord),
                3000
            );
        } else {
            this.notification.add(_t('No more product found for "%s".', searchProductWord), 3000);
        }
        if (this.state.previousSearchWord === searchProductWord) {
            this.state.currentOffset += result.length;
        } else {
            this.state.previousSearchWord = searchProductWord;
            this.state.currentOffset = result.length;
        }
    }

    async loadProductFromDB() {
        const { searchProductWord } = this.pos;
        if (!searchProductWord) {
            return;
        }

        this.pos.selectedCategoryId = 0;
        const product = await this.pos.data.searchRead(
            "product.product",
            [
                "&",
                ["available_in_pos", "=", true],
                "|",
                "|",
                ["name", "ilike", searchProductWord],
                ["default_code", "ilike", searchProductWord],
                ["barcode", "ilike", searchProductWord],
            ],
            this.pos.data.fields["product.product"],
            {
                offset: this.state.currentOffset,
                limit: 30,
            }
        );
        return product;
    }

    createNewProducts() {
        window.open("/web#action=point_of_sale.action_client_product_menu", "_self");
    }

    addProductToOrder(product) {
        reactive(this.pos).addProductToCurrentOrder(product);
    }

    async onProductInfoClick(product) {
        const info = await reactive(this.pos).getProductInfo(product, 1);
        this.dialog.add(ProductInfoPopup, { info: info, product: product });
    }
}

registry.category("pos_screens").add("ProductScreen", ProductScreen);
