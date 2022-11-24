/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { identifyError } from "@point_of_sale/app/error_handlers/error_handlers";
import { ConnectionLostError, ConnectionAbortedError } from "@web/core/network/rpc_service";

import { ProductItem } from "./ProductItem";
import { ProductsWidgetControlPanel } from "./ProductsWidgetControlPanel";
import { Component, useState } from "@odoo/owl";
import { sprintf } from "@web/core/utils/strings";
import { OfflineErrorPopup } from "@point_of_sale/js/Popups/OfflineErrorPopup";

export class ProductsWidget extends Component {
    static components = { ProductItem, ProductsWidgetControlPanel };
    static template = "ProductsWidget";

    /**
     * @param {Object} props
     * @param {number?} props.startCategoryId
     */
    setup() {
        super.setup();
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
        return Object.keys(this.pos.globalState.db.product_by_id).length > 0;
    }
    get selectedCategoryId() {
        return this.env.pos.selectedCategoryId;
    }
    get searchWord() {
        return this.env.pos.searchProductWord.trim();
    }
    get productsToDisplay() {
        let list = [];
        if (this.searchWord !== "") {
            list = this.env.pos.db.search_product_in_category(
                this.selectedCategoryId,
                this.searchWord
            );
        } else {
            list = this.env.pos.db.get_product_by_category(this.selectedCategoryId);
        }
        return list.sort(function (a, b) {
            return a.display_name.localeCompare(b.display_name);
        });
    }
    get subcategories() {
        return this.env.pos.db
            .get_category_childs_ids(this.selectedCategoryId)
            .map((id) => this.env.pos.db.get_category_by_id(id));
    }
    get breadcrumbs() {
        if (this.selectedCategoryId === this.env.pos.db.root_category_id) {
            return [];
        }
        return [
            ...this.env.pos.db.get_category_ancestors_ids(this.selectedCategoryId).slice(1),
            this.selectedCategoryId,
        ].map((id) => this.env.pos.db.get_category_by_id(id));
    }
    get hasNoCategories() {
        return this.env.pos.db.get_category_childs_ids(0).length === 0;
    }
    get shouldShowButton() {
        return this.productsToDisplay.length === 0 && this.searchWord;
    }
    switchCategory(categoryId) {
        this.env.pos.setSelectedCategoryId(categoryId);
    }
    updateSearch(searchWord) {
        this.env.pos.searchProductWord = searchWord;
    }
    clearSearch() {
        this.env.pos.searchProductWord = "";
    }
    updateProductList(event) {
        this.render(true);
        this.switchCategory(0);
    }
    async onPressEnterKey() {
        if (!this.env.pos.searchProductWord) {
            return;
        }
        if (this.state.previousSearchWord != this.env.pos.searchProductWord) {
            this.state.currentOffset = 0;
        }
        const result = await this.loadProductFromDB();
        if (result.length > 0) {
            this.notification.add(
                sprintf(
                    this.env._t('%s product(s) found for "%s".'),
                    result.length,
                    this.env.pos.searchProductWord
                ),
                3000
            );
        } else {
            this.notification.add(
                sprintf(
                    this.env._t('No more product found for "%s".'),
                    this.env.pos.searchProductWord
                ),
                3000
            );
        }
        if (this.state.previousSearchWord == this.env.pos.searchProductWord) {
            this.state.currentOffset += result.length;
        } else {
            this.state.previousSearchWord = this.env.pos.searchProductWord;
            this.state.currentOffset = result.length;
        }
    }
    async loadProductFromDB() {
        if (!this.env.pos.searchProductWord) {
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
                        ["name", "ilike", this.env.pos.searchProductWord],
                        ["default_code", "ilike", this.env.pos.searchProductWord],
                        ["barcode", "ilike", this.env.pos.searchProductWord],
                    ],
                ],
                {
                    offset: this.state.currentOffset,
                    limit: limit,
                }
            );
            if (ProductIds.length) {
                await this.env.pos._addProducts(ProductIds, false);
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
            [this.pos.globalState.pos_session.id]
        );
        this.pos.globalState.db.add_categories(categories);
        this.pos.globalState._loadProductProduct(products);
    }

    createNewProducts() {
        window.open("/web#action=point_of_sale.action_client_product_menu", "_blank");
        this.state.showReloadMessage = true;
    }
}
