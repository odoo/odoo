/** @odoo-module */

import { identifyError } from "@point_of_sale/js/utils";
import { ConnectionLostError, ConnectionAbortedError } from "@web/core/network/rpc_service";
import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";
import { debounce } from "@web/core/utils/timing";

const { onMounted, onWillUnmount } = owl;

class ProductsWidgetControlPanel extends PosComponent {
    setup() {
        super.setup();
        this.updateSearch = debounce(this.updateSearch, 100);
        this.state = { searchInput: "" };

        onMounted(() => {
            this.env.posbus.on("search-product-from-info-popup", this, this.searchProductFromInfo);
            if (!this.env.pos.config.limited_products_loading) {
                this.env.pos.isEveryProductLoaded = true;
            }
        });

        onWillUnmount(() => {
            this.env.posbus.off("search-product-from-info-popup", this);
        });
    }
    _clearSearch() {
        this.state.searchInput = "";
        this.trigger("clear-search");
    }
    get displayCategImages() {
        return (
            Object.values(this.env.pos.db.category_by_id).some((categ) => categ.has_image) &&
            !this.env.isMobile
        );
    }
    updateSearch(event) {
        this.trigger("update-search", this.state.searchInput);
        if (event.key === "Enter") {
            this._onPressEnterKey();
        }
    }
    async _onPressEnterKey() {
        if (!this.state.searchInput) {
            return;
        }
        if (!this.env.pos.isEveryProductLoaded) {
            const result = await this.loadProductFromDB();
            this.showNotification(
                _.str.sprintf(
                    this.env._t('%s product(s) found for "%s".'),
                    result.length,
                    this.state.searchInput
                ),
                3000
            );
            if (!result.length) {
                this._clearSearch();
            }
        }
    }
    searchProductFromInfo(productName) {
        this.state.searchInput = productName;
        this.trigger("switch-category", 0);
        this.trigger("update-search", productName);
    }
    _toggleMobileSearchbar() {
        this.trigger("toggle-mobile-searchbar");
    }
    async loadProductFromDB() {
        if (!this.state.searchInput) {
            return;
        }

        try {
            const ProductIds = await this.rpc({
                model: "product.product",
                method: "search",
                args: [
                    [
                        "&",
                        ["available_in_pos", "=", true],
                        "|",
                        "|",
                        "|",
                        ["name", "ilike", this.state.searchInput],
                        ["default_code", "ilike", this.state.searchInput],
                        ["barcode", "ilike", this.state.searchInput],
                    ],
                ],
                context: this.env.session.user_context,
            });
            if (ProductIds.length) {
                if (!this.env.pos.isEveryProductLoaded) {
                    await this.env.pos.updateIsEveryProductLoaded();
                }
                await this.env.pos._addProducts(ProductIds, false);
            }
            this.trigger("update-product-list");
            return ProductIds;
        } catch (error) {
            const identifiedError = identifyError(error);
            if (
                identifiedError instanceof ConnectionLostError ||
                identifiedError instanceof ConnectionAbortedError
            ) {
                return this.showPopup("OfflineErrorPopup", {
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
}
ProductsWidgetControlPanel.template = "ProductsWidgetControlPanel";

Registries.Component.add(ProductsWidgetControlPanel);

export default ProductsWidgetControlPanel;
