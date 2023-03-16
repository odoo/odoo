/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";
import { debounce } from "@web/core/utils/timing";
import { usePos } from "@point_of_sale/app/pos_store";

import { onMounted, onWillUnmount, useState } from "@odoo/owl";

class ProductsWidgetControlPanel extends PosComponent {
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
    }
    async _onPressEnterKey() {
        if (!this.state.searchInput) {
            return;
        }
        this.trigger('load-products-from-server');
    }
    searchProductFromInfo(productName) {
        this.state.searchInput = productName;
        this.trigger("switch-category", 0);
        this.trigger("update-search", productName);
    }
}
ProductsWidgetControlPanel.template = "ProductsWidgetControlPanel";

Registries.Component.add(ProductsWidgetControlPanel);

export default ProductsWidgetControlPanel;
