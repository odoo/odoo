/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { debounce } from "@web/core/utils/timing";
import { usePos } from "@point_of_sale/app/pos_store";

import { CategoryButton } from "./CategoryButton";

import { onMounted, onWillUnmount, useState } from "@odoo/owl";

export class ProductsWidgetControlPanel extends PosComponent {
    static components = { CategoryButton };
    static template = "ProductsWidgetControlPanel";

    setup() {
        super.setup();
        this.pos = usePos();
        this.updateSearch = debounce(this.updateSearch, 100);
        this.state = useState({ searchInput: "", mobileSearchBarIsShown: false });

        onMounted(() => {
            this.env.posbus.on("search-product-from-info-popup", this, this.searchProductFromInfo);
        });

        onWillUnmount(() => {
            this.env.posbus.off("search-product-from-info-popup", this);
        });
    }
    toggleMobileSearchBar() {
        this.state.mobileSearchBarIsShown = !this.state.mobileSearchBarIsShown;
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
        const result = await this.loadProductFromDB();
        this.showNotification(
            _.str.sprintf(
                this.env._t('%s product(s) found for "%s".'),
                result.length,
                this.state.searchInput
            ),
            3000
        );
    }
    searchProductFromInfo(productName) {
        this.state.searchInput = productName;
        this.trigger("switch-category", 0);
        this.trigger("update-search", productName);
    }
    async loadProductFromDB() {
        if (!this.state.searchInput) {
            return;
        }

        const ProductIds = await this.rpc({
            model: "product.product",
            method: "search",
            args: [
                [
                    "&",
                    ["available_in_pos", "=", true],
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
            await this.env.pos._addProducts(ProductIds, false);
        }
        this.trigger("update-product-list");
        return ProductIds;
    }
}
