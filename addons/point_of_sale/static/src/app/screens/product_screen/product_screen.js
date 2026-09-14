/** @odoo-module native */
import { Component, onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import {
    BACKSPACE,
    DEFAULT_LAST_ROW,
    getButtons,
    Numpad,
    SWITCHSIGN,
} from "@point_of_sale/app/components/numpad/numpad";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { OptionalProductPopup } from "@point_of_sale/app/components/popups/optional_products_popup/optional_products_popup";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { useBarcodeReader } from "@point_of_sale/app/hooks/barcode_reader_hook";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useLongPress } from "@point_of_sale/app/hooks/long_press_hook";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import {
    ControlButtons,
    ControlButtonsPopup,
} from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { BarcodeVideoScanner } from "@web/components/barcode";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { luxon } from "@web/core/l10n/luxon";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/ui/dialog";
const { DateTime } = luxon;

const log = makeLogger("pos.screen.product");

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
    static props = {
        orderUuid: { type: String },
    };

    setup() {
        useLifecycleLog(log);
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.numberBuffer = useService("number_buffer");
        this.isValidatingOrder = false;
        this.state = useState({
            previousSearchWord: "",
            currentOffset: 0,
        });

        useRouterParamsChecker();
        onMounted(() => {
            this.currentOrder.deselectOrderline();
            this.pos.openOpeningControl();
            this.numberBuffer.reset();
        });

        useEffect(
            () => {
                if (this.currentOrder?.state !== "draft" && !this.isValidatingOrder) {
                    log.logic("effect: non-draft order, adding new", () => ({
                        order: this.currentOrder?.uuid,
                        state: this.currentOrder?.state,
                    }));
                    this.pos.addNewOrder();
                }
            },
            () => [this.currentOrder, this.currentOrder?.state, this.isValidatingOrder],
        );

        onWillUnmount(async () => {
            const futurePreset =
                this.pos.config.use_presets &&
                this.currentOrder &&
                this.currentOrder.preset_id &&
                this.currentOrder.preset_time;
            log.logic("willUnmount: preset sync", () => ({
                order: this.currentOrder?.uuid,
                futurePreset: Boolean(futurePreset),
                sync: Boolean(
                    futurePreset && this.currentOrder.preset_time > DateTime.now(),
                ),
            }));
            if (futurePreset) {
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
        this.longPressHandlers = useLongPress((product) =>
            this.pos.onProductInfoClick(product),
        );
        this.onScroll = this.longPressHandlers.onScroll;
    }

    get quantityByProductTmplId() {
        const quantities = {};
        for (const line of this.currentOrder?.lines ?? []) {
            if (!line.combo_parent_id) {
                const id = line.product_id.product_tmpl_id.id;
                quantities[id] = (quantities[id] || 0) + line.qty;
            }
        }
        log.logic("cart quantities", () => ({ quantities }));
        return quantities;
    }

    onMouseDown(event, product) {
        this.longPressHandlers.onMouseDown(event, product);
    }

    onTouchStart(product) {
        this.longPressHandlers.onTouchStart(product);
    }

    getNumpadButtons() {
        const colorClassMap = {
            [this.env.services.localization.decimalPoint]:
                "o_colorlist_item_numpad_color_6",
            Backspace: "o_colorlist_item_numpad_color_1",
            "-": "o_colorlist_item_numpad_color_3",
        };

        return getButtons(DEFAULT_LAST_ROW, [
            { value: "quantity", text: _t("Qty") },
            {
                value: "discount",
                text: _t("%"),
                disabled: !this.pos.config.manual_discount || this.pos.cashierIsMinimal,
            },
            {
                value: "price",
                text: _t("Price"),
                disabled:
                    !this.pos.cashierHasPriceControlRights() ||
                    this.pos.cashierIsMinimal,
            },
            BACKSPACE,
        ]).map((button) => ({
            ...button,
            disabled:
                button.disabled ||
                (button.value === SWITCHSIGN.value && this.pos.cashierIsMinimal),
            class: `
                ${colorClassMap[button.value] || ""}
                ${this.pos.numpadMode === button.value ? "active" : ""}
                ${button.value === "quantity" ? "numpad-qty rounded-0" : ""}
                ${button.value === "price" ? "numpad-price rounded-0" : ""}
                ${button.value === "discount" ? "numpad-discount rounded-0" : ""}
            `,
        }));
    }
    onNumpadClick(buttonValue) {
        log.logic("onNumpadClick", () => ({
            buttonValue,
            mode: this.pos.numpadMode,
            line: this.currentOrder?.getSelectedOrderline()?.uuid,
        }));
        if (["quantity", "discount", "price"].includes(buttonValue)) {
            this.numberBuffer.capture();
            this.numberBuffer.reset();
            this.pos.numpadMode = buttonValue;
            return;
        }
        if (this.pos.selectedOrder.isRefund && buttonValue !== "Backspace") {
            log.logic("onNumpadClick: refund order, rejected", () => ({
                buttonValue,
                mode: this.pos.numpadMode,
            }));
            return this.dialog.add(AlertDialog, {
                title: _t("%s update not allowed", this.pos.numpadMode),
                body: _t(
                    "You can not change the %s of the refund order.",
                    this.pos.numpadMode,
                ),
            });
        }
        this.numberBuffer.sendKey(buttonValue);
    }
    get currentOrder() {
        return this.pos.getOrder();
    }
    get total() {
        return this.currentOrder?.currencyDisplayPrice || 0;
    }
    get items() {
        return this.env.utils.formatProductQty(
            this.currentOrder?.totalQuantity ?? 0,
            false,
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
            },
            onError: console.error,
            delayBetweenScan: 2000,
            cssClass: "w-100 h-100",
        };
    }
    async _getProductByBarcode(code) {
        let product = this.pos.models["product.product"].getBy(
            "barcode",
            code.base_code,
        );

        if (!product) {
            const productPackaging = this.pos.models["product.uom"].getBy(
                "barcode",
                code.base_code,
            );
            product = productPackaging && productPackaging.product_id;
        }

        if (!product) {
            log.pipeline("[barcode] product: server lookup", () => ({
                code: code.base_code,
            }));
            const records = await this.pos.loadNewProducts([
                ["product_variant_ids.barcode", "in", [code.base_code]],
            ]);

            if (records && records["product.product"].length > 0) {
                return records["product.product"][0];
            }
        }

        log.logic("[barcode] product lookup", () => ({
            code: code.base_code,
            type: code.type,
            product: product?.id,
        }));
        return product;
    }
    async _barcodeProductAction(code) {
        const product = await this._getProductByBarcode(code);

        if (!product) {
            log.logic("[barcode] product not found", () => ({ code: code.base_code }));
            this.sound.play("scan-error");
            this.barcodeReader.showNotFoundNotification(code);
            return;
        }
        this.sound.play("beep");
        log.pipeline("[barcode] add product", () => ({
            code: code.base_code,
            type: code.type,
            product: product.id,
            configure: product.needToConfigure(),
        }));

        await this.pos.addLineToCurrentOrder(
            { product_id: product, product_tmpl_id: product.product_tmpl_id },
            { code },
            product.needToConfigure(),
        );
        this.numberBuffer.reset();
        this.showOptionalProductPopupIfNeeded(product);
    }
    async _getPartnerByBarcode(code) {
        let partner = this.pos.models["res.partner"].getBy("barcode", code.code);
        if (!partner) {
            partner = await this.pos.data.searchRead("res.partner", [
                ["barcode", "=", code.code],
            ]);
            partner = partner.length > 0 && partner[0];
        }
        return partner;
    }
    async _barcodePartnerAction(code) {
        const partner = await this._getPartnerByBarcode(code);
        log.logic("[barcode] partner", () => ({
            code: code.code,
            partner: partner?.id,
            current: this.currentOrder.getPartner()?.id,
        }));
        if (partner) {
            this.sound.play("beep");
            if (this.currentOrder.getPartner() !== partner) {
                this.pos.setPartnerToCurrentOrder(partner);
            }
            return;
        }
        this.sound.play("scan-error");
        this.barcodeReader.showNotFoundNotification(code);
    }
    _barcodeDiscountAction(code) {
        const last_orderline = this.currentOrder.getLastOrderline();
        log.logic("[barcode] discount", () => ({
            value: code.value,
            line: last_orderline?.uuid,
        }));
        if (last_orderline) {
            this.pos.setDiscountFromUI(last_orderline, code.value);
        }
    }
    async _barcodeGS1Action(parsed_results) {
        const productBarcode = parsed_results.find(
            (element) => element.type === "product",
        );
        const lotBarcode = parsed_results.find((element) => element.type === "lot");
        const qty = parsed_results.find((element) => element.type === "quantity");
        const product = await this._getProductByBarcode(productBarcode);

        if (!product) {
            log.logic("[barcode] gs1 product not found", () => ({
                code: productBarcode?.base_code,
            }));
            this.sound.play("scan-error");
            this.barcodeReader.showNotFoundNotification(productBarcode);
            return;
        }
        this.sound.play("beep");
        const vals = {
            product_id: product,
            product_tmpl_id: product.product_tmpl_id,
        };
        const uomMatches = Boolean(
            qty &&
            product.uom_id &&
            qty.rule?.associated_uom_id &&
            product.uom_id.id === qty.rule.associated_uom_id[0],
        );
        log.pipeline("[barcode] gs1", () => ({
            elements: parsed_results.map((e) => e.type),
            product: product.id,
            lot: lotBarcode?.code,
            qty: qty?.value,
            uomMatches,
        }));
        if (uomMatches) {
            vals.qty = qty.value;
        }

        await this.pos.addLineToCurrentOrder(vals, { code: lotBarcode });
        this.numberBuffer.reset();
        this.showOptionalProductPopupIfNeeded(product);
    }
    displayAllControlPopup() {
        this.dialog.add(ControlButtonsPopup);
    }

    switchPane() {
        this.pos.scanning = false;
        this.pos.switchPane();
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
        log.logic("onPressEnterKey: server search", () => ({
            searchProductWord,
            offset: this.state.currentOffset,
            results: result.length,
        }));
        if (result.length === 0) {
            this.notification.add(
                _t('No other products found for "%s".', searchProductWord),
                3000,
            );
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
        log.pipeline("loadProductFromDB", () => ({ searchProductWord }));
        if (!searchProductWord) {
            return;
        }

        this.pos.setSelectedCategory(0);
        const domain = this.loadProductFromDBDomain(searchProductWord);

        const { limit_categories, iface_available_categ_ids } = this.pos.config;
        log.logic("loadProductFromDB: category limit", () => ({
            limit_categories,
            categories: iface_available_categ_ids.length,
        }));
        if (limit_categories && iface_available_categ_ids.length > 0) {
            const categIds = iface_available_categ_ids.map((categ) => categ.id);
            domain.push(["pos_categ_ids", "in", categIds]);
        }

        const results = await this.pos.loadNewProducts(
            domain,
            this.state.currentOffset,
            30,
        );
        return results["product.product"];
    }

    async addProductToOrder(product) {
        log.logic("addProductToOrder", () => ({
            product: product.id,
            configurable: product.isConfigurable(),
            searchWord: this.searchWord,
        }));
        const options = {};
        if (this.searchWord && product.isConfigurable()) {
            const barcode = this.searchWord;
            const searchedProduct = product.product_variant_ids.filter(
                (p) => p.barcode && p.barcode.includes(barcode),
            );
            log.logic("addProductToOrder: preset variant", () => ({
                product: product.id,
                barcode,
                matches: searchedProduct.length,
            }));
            if (searchedProduct.length === 1) {
                options["presetVariant"] = searchedProduct[0];
            }
        }
        await this.pos.addLineToCurrentOrder({ product_tmpl_id: product }, options);
        this.showOptionalProductPopupIfNeeded(product);
    }
    showOptionalProductPopupIfNeeded(product) {
        log.logic("showOptionalProductPopupIfNeeded", () => ({
            product: product.id,
            optional: product.pos_optional_product_ids?.length ?? 0,
        }));
        if (product.pos_optional_product_ids?.length) {
            this.dialog.add(OptionalProductPopup, {
                productTemplate: product,
            });
        }
    }

    async fastValidate(paymentMethod) {
        log.logic("fastValidate", () => ({
            method: paymentMethod?.id,
            validating: this.isValidatingOrder,
        }));
        if (this.isValidatingOrder) {
            return;
        }
        try {
            this.isValidatingOrder = true;
            await this.pos.validateOrderFast(paymentMethod);
        } finally {
            this.isValidatingOrder = false;
        }
    }
}

registry.category("pos_pages").add("ProductScreen", {
    name: "ProductScreen",
    component: ProductScreen,
    route: `/pos/ui/${odoo.pos_config_id}/product/{string:orderUuid}`,
    params: {
        orderUuid: true,
        orderFinalized: false,
    },
});
