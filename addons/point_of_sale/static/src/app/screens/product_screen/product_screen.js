import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
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
import { CameraBarcodeScanner } from "@point_of_sale/app/screens/product_screen/camera_barcode_scanner";

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
        CameraBarcodeScanner,
    };
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useState(useService("ui"));
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
            this.pos.addPendingOrder([this.currentOrder.id]);
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
                const orderDateTime = DateTime.fromSQL(this.currentOrder.preset_time);
                if (orderDateTime > DateTime.now()) {
                    this.pos.addPendingOrder([this.currentOrder.id]);
                    await this.pos.syncAllOrders();
                }
            }
        });

        this.barcodeReader = useService("barcode_reader");

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

        useEffect(
            () => {
                this.state.quantityByProductTmplId = this.currentOrder?.lines?.reduce((acc, ol) => {
                    acc[ol.product_id.product_tmpl_id.id]
                        ? (acc[ol.product_id.product_tmpl_id.id] += ol.qty)
                        : (acc[ol.product_id.product_tmpl_id.id] = ol.qty);
                    return acc;
                }, {});
            },
            () => [this.currentOrder.totalQuantity]
        );
    }

    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]: "o_colorlist_item_color_transparent_6",
            Backspace: "o_colorlist_item_color_transparent_1",
            "-": "o_colorlist_item_color_transparent_3",
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
            class: `
                ${defaultLastRowValues.includes(button.value) ? "border-0" : ""}
                ${colorClassMap[button.value] || ""}
                ${this.pos.numpadMode === button.value ? "active" : ""}
                ${button.value === "quantity" ? "numpad-qty rounded-0 rounded-top mb-0" : ""}
                ${button.value === "price" ? "numpad-price rounded-0 rounded-bottom mt-0" : ""}
                ${
                    button.value === "discount"
                        ? "numpad-discount my-0 rounded-0 border-top border-bottom"
                        : ""
                }
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
        return this.currentOrder.lines?.reduce((items, line) => items + line.qty, 0) ?? 0;
    }
    getProductName(product) {
        return product.name;
    }
    async _getProductByBarcode(code) {
        let product = this.pos.models["product.product"].getBy("barcode", code.base_code);

        if (!product) {
            const productPackaging = this.pos.models["product.packaging"].getBy(
                "barcode",
                code.base_code
            );
            product = productPackaging && productPackaging.product_id;
        }

        if (!product) {
            const records = await this.pos.data.callRelated(
                "pos.session",
                "find_product_by_barcode",
                [odoo.pos_session_id, code.base_code, this.pos.config.id]
            );
            await this.pos.processProductAttributes();

            if (records && records["product.product"].length > 0) {
                product = records["product.product"][0];
                await this.pos._loadMissingPricelistItems([product]);
            }
        }

        return product;
    }
    async _barcodeProductAction(code) {
        const product = await this._getProductByBarcode(code);

        if (!product) {
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
                this.currentOrder.setPartner(partner);
            }
            return;
        }
        this.barcodeReader.showNotFoundNotification(code);
    }
    _barcodeDiscountAction(code) {
        var last_orderline = this.currentOrder.getLastOrderline();
        if (last_orderline) {
<<<<<<< saas-18.1
            last_orderline.setDiscount(code.value);
||||||| 69b404c7109ff689381f56520aad758424ec01aa
            last_orderline.set_discount(code.value);
=======
            this.pos.setDiscountFromUI(last_orderline, code.value);
>>>>>>> f3f07012b8df310db66b3e6cf06ef5598346aadd
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
    /**
     * This getter is used to restart the animation on the product-reminder.
     * When the information present on the product-reminder will change,
     * the key will change and thus a new product-reminder will be created
     * and the old one will be garbage collected leading to the animation
     * being retriggered.
     */
    get animationKey() {
        return [
            this.currentOrder.getSelectedOrderline()?.uuid,
            this.selectedOrderlineQuantity,
            this.selectedOrderlineDisplayName,
            this.selectedOrderlineTotal,
        ].join(",");
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
        if (result.length > 0) {
            this.notification.add(
                _t('%s product(s) found for "%s".', result.length, searchProductWord),
                3000
            );
        } else {
            this.notification.add(_t('No more product found for "%s".', searchProductWord));
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

        this.pos.setSelectedCategory(0);
        const domain = [
            "|",
            "|",
            ["name", "ilike", searchProductWord],
            ["default_code", "ilike", searchProductWord],
            ["barcode", "ilike", searchProductWord],
            ["available_in_pos", "=", true],
            ["sale_ok", "=", true],
        ];

        const { limit_categories, iface_available_categ_ids } = this.pos.config;
        if (limit_categories && iface_available_categ_ids.length > 0) {
            const categIds = iface_available_categ_ids.map((categ) => categ.id);
            domain.push(["pos_categ_ids", "in", categIds]);
        }
        const product = await this.pos.data.searchRead(
            "product.product",
            domain,
            this.pos.data.fields["product.product"],
            {
                context: { display_default_code: false },
                offset: this.state.currentOffset,
                limit: 30,
            }
        );

        await this.pos.processProductAttributes();
        return product;
    }

    async addProductToOrder(product) {
        await this.pos.addLineToCurrentOrder({ product_tmpl_id: product }, {});
    }

    async onProductInfoClick(productTemplate) {
        const info = await this.pos.getProductInfo(productTemplate, 1);
        this.dialog.add(ProductInfoPopup, { info: info, productTemplate: productTemplate });
    }
}

registry.category("pos_screens").add("ProductScreen", ProductScreen);
