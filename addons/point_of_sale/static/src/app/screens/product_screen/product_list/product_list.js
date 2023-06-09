/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { identifyError } from "@point_of_sale/app/errors/error_handlers";
import { ConnectionLostError, ConnectionAbortedError } from "@web/core/network/rpc_service";

import { ProductItem } from "@point_of_sale/app/screens/product_screen/product/product";
import { ProductsWidgetControlPanel } from "@point_of_sale/app/screens/product_screen/product_list/control_panel/control_panel";
import { Component, useState } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";
import { OfflineErrorPopup } from "@point_of_sale/app/errors/popups/offline_error_popup";

export class ProductsWidget extends Component {
    static components = { ProductItem, ProductsWidgetControlPanel };
    static template = "point_of_sale.ProductsWidget";

    /**
     * @param {Object} props
     * @param {number?} props.startCategoryId
     */
    setup() {
        this.state = useState({
            previousSearchWord: "",
            currentOffset: 0,
            showReloadMessage: false,
        });
        this.pos = usePos();
        this.popup = useService("popup");
        this.notification = useService("pos_notification");
        this.orm = useService("orm");
    }
    get hasProducts() {
        return Object.keys(this.pos.db.product_by_id).length > 0;
    }
    get selectedCategoryId() {
        return this.pos.selectedCategoryId;
    }
    get searchWord() {
        return this.pos.searchProductWord.trim();
    }
    get productsToDisplay() {
        const { db } = this.pos;
        let list = [];
        if (this.searchWord !== "") {
            list = db.search_product_in_category(this.selectedCategoryId, this.searchWord);
        } else {
            list = db.get_product_by_category(this.selectedCategoryId);
        }
        return list.sort(function (a, b) {
            return a.display_name.localeCompare(b.display_name);
        });
    }
    get subcategories() {
        const { db } = this.pos;
        return db
            .get_category_childs_ids(this.selectedCategoryId)
            .map((id) => db.get_category_by_id(id));
    }
    get breadcrumbs() {
        const { db } = this.pos;
        if (this.selectedCategoryId === db.root_category_id) {
            return [];
        }
        return [
            ...db.get_category_ancestors_ids(this.selectedCategoryId).slice(1),
            this.selectedCategoryId,
        ].map((id) => db.get_category_by_id(id));
    }
    get hasNoCategories() {
        return this.pos.db.get_category_childs_ids(0).length === 0;
    }
    get shouldShowButton() {
        return this.productsToDisplay.length === 0 && this.searchWord;
    }
    switchCategory(categoryId) {
        this.pos.setSelectedCategoryId(categoryId);
    }
    updateSearch(searchWord) {
        this.pos.searchProductWord = searchWord;
    }
    clearSearch() {
        this.pos.searchProductWord = "";
    }
    updateProductList(event) {
        this.switchCategory(0);
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
                sprintf(
                    this.env._t('%s product(s) found for "%s".'),
                    result.length,
                    searchProductWord
                ),
                3000
            );
        } else {
            this.notification.add(
                sprintf(this.env._t('No more product found for "%s".'), searchProductWord),
                3000
            );
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

        try {
            const limit = 30;
            const ProductIds = await this.orm.call(
                "product.product",
                "search",
                [
                    [
                        "&",
                        ["available_in_pos", "=", true],
                        "|",
                        "|",
                        ["name", "ilike", searchProductWord],
                        ["default_code", "ilike", searchProductWord],
                        ["barcode", "ilike", searchProductWord],
                    ],
                ],
                {
                    offset: this.state.currentOffset,
                    limit: limit,
                }
            );
            if (ProductIds.length) {
                await this.pos._addProducts(ProductIds, false);
            }
            this.updateProductList();
            return ProductIds;
        } catch (error) {
            const identifiedError = identifyError(error);
            if (
                identifiedError instanceof ConnectionLostError ||
                identifiedError instanceof ConnectionAbortedError
            ) {
                return this.popup.add(OfflineErrorPopup, {
                    title: this.env._t("Network Error"),
                    body: this.env._t(
                        "Product is not loaded. Tried loading the product from the server but there is a network error."
                    ),
                });
            } else {
                throw error;
            }
        }
    }
    async loadDemoDataProducts() {
        const { products, categories } = await this.orm.call(
            "pos.session",
            "load_product_frontend",
            [this.pos.pos_session.id]
        );
        this.pos.db.add_categories(categories);
        this.pos._loadProductProduct(products);
    }

    createNewProducts() {
        window.open("/web#action=point_of_sale.action_client_product_menu", "_blank");
        this.state.showReloadMessage = true;
    }
}
