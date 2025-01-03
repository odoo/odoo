import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useBarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_hook";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, useState, reactive } from "@odoo/owl";
import { CategorySelector } from "@point_of_sale/app/generic_components/category_selector/category_selector";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import {
    BACKSPACE,
    Numpad,
    getButtons,
    DEFAULT_LAST_ROW,
} from "@point_of_sale/app/generic_components/numpad/numpad";
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
import { pick } from "@web/core/utils/objects";
import { unaccent } from "@web/core/utils/strings";
import { CameraBarcodeScanner } from "@point_of_sale/app/screens/product_screen/camera_barcode_scanner";

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
        CameraBarcodeScanner,
    };
    static numpadActionName = _t("Payment");
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
        });
        onMounted(() => {
            this.pos.openCashControl();

            if (this.pos.config.iface_start_categ_id) {
                this.pos.setSelectedCategory(this.pos.config.iface_start_categ_id.id);
            }
            this.pos.addPendingOrder([this.pos.get_order().id]);

            // Call `reset` when the `onMounted` callback in `numberBuffer.use` is done.
            // We don't do this in the `mounted` lifecycle method because it is called before
            // the callbacks in `onMounted` hook.
            this.numberBuffer.reset();
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
    }
    getAncestorsAndCurrent() {
        const selectedCategory = this.pos.selectedCategory;
        return selectedCategory
            ? [undefined, ...selectedCategory.allParents, selectedCategory]
            : [selectedCategory];
    }
    getChildCategories(selectedCategory) {
        return selectedCategory
            ? [...selectedCategory.child_ids]
            : this.pos.models["pos.category"].filter((category) => !category.parent_id);
    }

    getCategoriesList(list, allParents, depth) {
        return list.map((category) => {
            if (category.id === allParents[depth]?.id && category.child_ids?.length) {
                return [
                    category,
                    this.getCategoriesList(category.child_ids, allParents, depth + 1),
                ];
            }
            return category;
        });
    }

    getCategoriesAndSub() {
        const rootCategories = this.pos.models["pos.category"].filter(
            (category) => !category.parent_id
        );
        const selected = this.pos.selectedCategory ? [this.pos.selectedCategory] : [];
        const allParents = selected.concat(this.pos.selectedCategory?.allParents || []).reverse();
        return this.getCategoriesList(rootCategories, allParents, 0)
            .flat(Infinity)
            .map(this.getChildCategoriesInfo, this);
    }

    getChildCategoriesInfo(category) {
        return {
            ...pick(category, "id", "name", "color"),
            imgSrc:
                this.pos.config.show_category_images && category.has_image
                    ? `/web/image?model=pos.category&field=image_128&id=${category.id}`
                    : undefined,
            isSelected: this.getAncestorsAndCurrent().includes(category),
            isChildren: this.getChildCategories(this.pos.selectedCategory).includes(category),
        };
    }

    getNumpadButtons() {
        return getButtons(DEFAULT_LAST_ROW, [
            { value: "quantity", text: _t("Qty") },
            { value: "discount", text: _t("% Disc"), disabled: !this.pos.config.manual_discount },
            {
                value: "price",
                text: _t("Price"),
                disabled: !this.pos.cashierHasPriceControlRights(),
            },
            BACKSPACE,
        ]).map((button) => ({
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
    get currentOrder() {
        return this.pos.get_order();
    }
    get total() {
        return this.env.utils.formatCurrency(this.currentOrder?.get_total_with_tax() ?? 0);
    }
    get items() {
        return this.currentOrder.lines?.reduce((items, line) => items + line.qty, 0) ?? 0;
    }
    getProductName(product) {
        const productTmplValIds = product.attribute_line_ids
            .map((l) => l.product_template_value_ids)
            .flat();
        return productTmplValIds.length > 1 ? product.name : product.display_name;
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
            { product_id: product },
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
            if (this.currentOrder.get_partner() !== partner) {
                this.currentOrder.set_partner(partner);
            }
            return;
        }
        this.barcodeReader.showNotFoundNotification(code);
    }
    _barcodeDiscountAction(code) {
        var last_orderline = this.currentOrder.get_last_orderline();
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

        await this.pos.addLineToCurrentOrder({ product_id: product }, { code: lotBarcode });
        this.numberBuffer.reset();
    }
    displayAllControlPopup() {
        this.dialog.add(ControlButtonsPopup);
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

    switchPane() {
        this.pos.scanning = false;
        this.pos.switchPane();
    }

    getProductPrice(product) {
        const price = product.list_price === product.lst_price ? false : product.lst_price;
        return this.pos.getProductPriceFormatted(product, price);
    }

    getProductImage(product) {
        return product.getTemplateImageUrl(this.pos.productHighResolution);
    }

    get searchWord() {
        return this.pos.searchProductWord.trim();
    }

    get products() {
        return this.pos.models["product.product"].getAll();
    }

    get productsToDisplay() {
        let list = [];

        if (this.searchWord !== "") {
            list = this.getProductsBySearchWord(this.searchWord);
        } else if (this.pos.selectedCategory?.id) {
            list = this.getProductsByCategory(this.pos.selectedCategory);
        } else {
            list = this.products;
        }

        if (!list || list.length === 0) {
            return [];
        }

        const excludedProductIds = [
            this.pos.config.tip_product_id?.id,
            ...this.pos.hiddenProductIds,
            ...this.pos.session._pos_special_products_ids,
        ];

        const filteredList = [];
        for (const product of list) {
            if (filteredList.length >= 100) {
                break;
            }
            if (!excludedProductIds.includes(product.id) && product.available_in_pos) {
                filteredList.push(product);
            }
        }

        return this.searchWord !== ""
            ? filteredList
            : filteredList.sort((a, b) => a.display_name.localeCompare(b.display_name));
    }

    getProductsBySearchWord(searchWord) {
        const products = this.pos.selectedCategory?.id
            ? this.getProductsByCategory(this.pos.selectedCategory)
            : this.products;

        const exactMatches = products.filter((product) => product.exactMatch(searchWord));

        if (exactMatches.length > 0 && searchWord.length > 2) {
            return this.addMainProductsToDisplay(exactMatches);
        }

        const fuzzyMatches = fuzzyLookup(unaccent(searchWord, false), products, (product) =>
            unaccent(product.searchString, false)
        );

        return this.addMainProductsToDisplay([...exactMatches, ...fuzzyMatches]);
    }

    addMainProductsToDisplay(products) {
        const uniqueProductsMap = new Map();
        for (const product of products) {
            if (product.id in this.pos.mainProductVariant) {
                const mainProduct = this.pos.mainProductVariant[product.id];
                uniqueProductsMap.set(mainProduct.id, mainProduct);
            } else {
                uniqueProductsMap.set(product.id, product);
            }
        }
        return Array.from(uniqueProductsMap.values());
    }

    getProductsByCategory(category) {
        const allCategoryIds = category.getAllChildren().map((cat) => cat.id);
        const products = allCategoryIds.flatMap(
            (catId) => this.pos.models["product.product"].getBy("pos_categ_ids", catId) || []
        );
        // Remove duplicates since owl doesn't like it.
        return Array.from(new Set(products));
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
        await reactive(this.pos).addLineToCurrentOrder({ product_id: product }, {});
    }

    async onProductInfoClick(product) {
        const info = await reactive(this.pos).getProductInfo(product, 1);
        this.dialog.add(ProductInfoPopup, { info: info, product: product });
    }
}

registry.category("pos_screens").add("ProductScreen", ProductScreen);
