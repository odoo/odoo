import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, onMounted, useEffect, useState, onWillRender, onWillUnmount } from "@odoo/owl";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import {
    BACKSPACE,
    Numpad,
    getButtons,
    DEFAULT_LAST_ROW,
    SWITCHSIGN,
} from "@point_of_sale/app/components/numpad/numpad";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import {
    ControlButtons,
    ControlButtonsPopup,
} from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { BarcodeVideoScanner } from "@web/core/barcode/barcode_video_scanner";

const { DateTime } = luxon;

export class ProductScreen extends Component {
    static template = "point_of_sale.ProductScreen";
    static components = {
        ActionpadWidget,
        Numpad,
        Orderline,
        CategorySelector,
        Input,
        ControlButtons,
        OrderSummary,
        ProductCard,
        BarcodeVideoScanner,
    };
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.numberBuffer = useService("number_buffer");
        this.state = useState({
            previousSearchWord: "",
            currentOffset: 0,
            quantityByProductTmplId: {},
        });
        onMounted(() => {
            this.pos.openOpeningControl();
            // Call `reset` when the `onMounted` callback in `numberBuffer.use` is done.
            // We don't do this in the `mounted` lifecycle method because it is called before
            // the callbacks in `onMounted` hook.
            this.numberBuffer.reset();
        });

        onWillRender(() => {
            // If its a shared order it can be paid from another POS
            if (this.currentOrder?.state !== "draft") {
                this.pos.addNewOrder();
            }
        });

        onWillUnmount(async () => {
            if (
                this.pos.config.use_presets &&
                this.currentOrder &&
                this.currentOrder.preset_id &&
                this.currentOrder.preset_time
            ) {
                if (this.currentOrder.preset_time > DateTime.now()) {
                    this.pos.addPendingOrder([this.currentOrder.id]);
                    await this.pos.syncAllOrders();
                }
            }
        });

        this.barcodeReader = useService("barcode_reader");
        this.sound = useService("mail.sound_effects");

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

        this.doLoadSampleData = useTrackedAsync(() => this.pos.loadSampleData());

        useEffect(
            () => {
                this.state.quantityByProductTmplId = this.currentOrder?.lines?.reduce((acc, ol) => {
                    if (!ol.combo_parent_id) {
                        const productTmplId = ol.product_id.product_tmpl_id.id;
                        acc[productTmplId] = (acc[productTmplId] || 0) + ol.qty;
                    }
                    return acc;
                }, {});
            },
            () => [this.currentOrder, this.currentOrder.totalQuantity]
        );
    }

    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_numpad_color_6",
            Backspace: "o_colorlist_item_numpad_color_1",
            "-": "o_colorlist_item_numpad_color_3",
        };

        const defaultLastRowValues =
            DEFAULT_LAST_ROW.map((button) => button.value) + [BACKSPACE.value];

        return getButtons(DEFAULT_LAST_ROW, [
            { value: "quantity", text: _t("Qty") },
            {
                value: "discount",
                text: _t("%"),
                disabled: !this.pos.config.manual_discount || this.pos.cashier._role === "minimal",
            },
            {
                value: "price",
                text: _t("Price"),
                disabled:
                    !this.pos.cashierHasPriceControlRights() ||
                    this.pos.cashier._role === "minimal",
            },
            BACKSPACE,
        ]).map((button) => ({
            ...button,
            disabled:
                button.disabled ||
                (button.value === SWITCHSIGN.value && this.pos.cashier._role === "minimal"),
            class: `
                ${defaultLastRowValues.includes(button.value) ? "" : ""}
                ${colorClassMap[button.value] || ""}
                ${this.pos.numpadMode === button.value ? "active" : ""}
                ${button.value === "quantity" ? "numpad-qty rounded-0" : ""}
                ${button.value === "price" ? "numpad-price rounded-0" : ""}
                ${button.value === "discount" ? "numpad-discount rounded-0" : ""}
            `,
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
    get currentOrder() {
        return this.pos.getOrder();
    }
    get total() {
        return this.env.utils.formatCurrency(this.currentOrder?.getTotalWithTax() ?? 0);
    }
    get items() {
        return this.env.utils.formatProductQty(
            this.currentOrder.lines?.reduce((items, line) => items + line.qty, 0) ?? 0,
            false
        );
    }
    getProductName(product) {
        return product.name;
    }
    get barcodeVideoScannerProps() {
        return {
            facingMode: "environment",
            onResult: (result) => {
                this.barcodeReader.scan(result);
                this.sound.play("beep");
            },
            onError: console.error,
            delayBetweenScan: 2000,
            cssClass: "w-100 h-100",
        };
    }
    async _getProductByBarcode(code) {
        let product = this.pos.models["product.product"].getBy("barcode", code.base_code);

        if (!product) {
            const productPackaging = this.pos.models["product.uom"].getBy(
                "barcode",
                code.base_code
            );
            product = productPackaging && productPackaging.product_id;
        }

        if (!product) {
            const records = await this.pos.loadNewProducts([
                ["product_variant_ids.barcode", "in", [code.base_code]],
            ]);

            if (records && records["product.product"].length > 0) {
                return records["product.product"][0];
            }
        }

        return product;
    }
    async _barcodeProductAction(code) {
        const product = await this._getProductByBarcode(code);

        if (!product) {
            this.sound.play("error");
            this.barcodeReader.showNotFoundNotification(code);
            return;
        }

        await this.pos.addLineToCurrentOrder(
            { product_id: product, product_tmpl_id: product.product_tmpl_id },
            { code },
            product.needToConfigure()
        );
        this.numberBuffer.reset();
    }
    async _getPartnerByBarcode(code) {
        let partner = this.pos.models["res.partner"].getBy("barcode", code.code);
        if (!partner) {
            partner = await this.pos.data.searchRead("res.partner", [["barcode", "=", code.code]]);
            partner = partner.length > 0 && partner[0];
        }
        return partner;
    }
    async _barcodePartnerAction(code) {
        const partner = await this._getPartnerByBarcode(code);
        if (partner) {
            if (this.currentOrder.getPartner() !== partner) {
                this.pos.setPartnerToCurrentOrder(partner);
            }
            return;
        }
        this.barcodeReader.showNotFoundNotification(code);
    }
    _barcodeDiscountAction(code) {
        var last_orderline = this.currentOrder.getLastOrderline();
        if (last_orderline) {
            this.pos.setDiscountFromUI(last_orderline, code.value);
        }
    }
    /**
     * Add a product to the current order using the product identifier and lot number from parsed results.
     * This function retrieves the product identifier and lot number from the `parsed_results` parameter.
     * It then uses these values to retrieve the product and add it to the current order.
     */
    async _barcodeGS1Action(parsed_results) {
        const productBarcode = parsed_results.find((element) => element.type === "product");
        const lotBarcode = parsed_results.find((element) => element.type === "lot");
        const product = await this._getProductByBarcode(productBarcode);

        if (!product) {
            this.barcodeReader.showNotFoundNotification(
                parsed_results.find((element) => element.type === "product")
            );
            return;
        }

        await this.pos.addLineToCurrentOrder(
            { product_id: product, product_tmpl_id: product.product_tmpl_id },
            { code: lotBarcode }
        );
        this.numberBuffer.reset();
    }
    displayAllControlPopup() {
        this.dialog.add(ControlButtonsPopup);
    }
    get selectedOrderlineQuantity() {
        return this.currentOrder.getSelectedOrderline()?.getQuantityStr();
    }
    get selectedOrderlineDisplayName() {
        return this.currentOrder.getSelectedOrderline()?.getFullProductName();
    }
    get selectedOrderlineTotal() {
        return this.env.utils.formatCurrency(
            this.currentOrder.getSelectedOrderline()?.getDisplayPrice()
        );
    }

    switchPane() {
        this.pos.scanning = false;
        this.pos.switchPane();
    }

    getProductPrice(product) {
        return this.pos.getProductPrice(product, false, true);
    }

    getProductImage(product) {
        return product.getImageUrl();
    }

    get searchWord() {
        return this.pos.searchProductWord.trim();
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
        if (result.length === 0) {
            this.notification.add(_t('No other products found for "%s".', searchProductWord), 3000);
        }
        if (this.state.previousSearchWord === searchProductWord) {
            this.state.currentOffset += result.length;
        } else {
            this.state.previousSearchWord = searchProductWord;
            this.state.currentOffset = result.length;
        }
    }

    loadProductFromDBDomain(searchProductWord) {
        return [
            "|",
            "|",
            "|",
            ["name", "ilike", searchProductWord],
            ["product_variant_ids.name", "ilike", searchProductWord],
            "|",
            ["default_code", "ilike", searchProductWord],
            ["product_variant_ids.default_code", "ilike", searchProductWord],
            "|",
            ["barcode", "ilike", searchProductWord],
            ["product_variant_ids.barcode", "ilike", searchProductWord],
            ["available_in_pos", "=", true],
            ["sale_ok", "=", true],
        ];
    }

    async loadProductFromDB() {
        const { searchProductWord } = this.pos;
        if (!searchProductWord) {
            return;
        }

        this.pos.setSelectedCategory(0);
        const domain = this.loadProductFromDBDomain(searchProductWord);

        const { limit_categories, iface_available_categ_ids } = this.pos.config;
        if (limit_categories && iface_available_categ_ids.length > 0) {
            const categIds = iface_available_categ_ids.map((categ) => categ.id);
            domain.push(["pos_categ_ids", "in", categIds]);
        }

        const results = await this.pos.loadNewProducts(domain, this.state.currentOffset, 30);
        return results["product.product"];
    }

    async addProductToOrder(product) {
        const options = {};
        if (this.searchWord && product.isConfigurable()) {
            const barcode = this.searchWord;
            const searchedProduct = product.product_variant_ids.filter(
                (p) => p.barcode && p.barcode.includes(barcode)
            );
            if (searchedProduct.length === 1) {
                options["presetVariant"] = searchedProduct[0];
            }
        }
        await this.pos.addLineToCurrentOrder({ product_tmpl_id: product }, options);
    }

    async onProductInfoClick(productTemplate) {
        const info = await this.pos.getProductInfo(productTemplate, 1);
        this.dialog.add(ProductInfoPopup, { info: info, productTemplate: productTemplate });
    }
}

registry.category("pos_screens").add("ProductScreen", ProductScreen);
