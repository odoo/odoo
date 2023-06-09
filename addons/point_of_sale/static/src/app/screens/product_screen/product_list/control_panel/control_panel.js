/** @odoo-module */

import { debounce } from "@web/core/utils/timing";
import { usePos } from "@point_of_sale/app/store/pos_hook";

import { CategoryButton } from "@point_of_sale/app/screens/product_screen/category_button/category_button";

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ProductsWidgetControlPanel extends Component {
    static components = { CategoryButton };
    static template = "point_of_sale.ProductsWidgetControlPanel";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.notification = useService("pos_notification");
        this.orm = useService("orm");
        this.updateSearch = debounce(this.updateSearch, 100);
        this.state = useState({ mobileSearchBarIsShown: false, isMobile: false });
        this.productsWidgetControl = useRef("products-widget-control");
        this.ui = useService("ui");

        const toggleIsMobile = () => this.toggleIsMobile();
        onMounted(() => {
            toggleIsMobile();
            window.addEventListener("resize", toggleIsMobile);
        });
        onWillUnmount(() => {
            window.removeEventListener("resize", toggleIsMobile);
        });
    }
    toggleIsMobile() {
        // In addition to the UI service we need to check the width of the window
        // because the search bar glitches on a specific width between when the
        // UI is considered small and not.
        const element = this.productsWidgetControl.el;
        this.state.isMobile = (element && element.offsetWidth < 350) || this.ui.isSmall;
    }
    toggleMobileSearchBar() {
        this.state.mobileSearchBarIsShown = !this.state.mobileSearchBarIsShown;
    }
    _clearSearch() {
        this.pos.searchProductWord = "";
        this.props.clearSearch();
    }
    get displayCategImages() {
        return (
            !this.ui.isSmall &&
            Object.values(this.pos.db.category_by_id).some((categ) => categ.has_image)
        );
    }
    updateSearch(event) {
        this.props.updateSearch(this.pos.searchProductWord);
    }
    async _onPressEnterKey() {
        if (!this.pos.searchProductWord) {
            return;
        }
        this.props.loadProductFromServer();
    }
    searchProductFromInfo(productName) {
        this.pos.searchProductWord = productName;
        this.props.switchCategory(0);
        this.props.updateSearch(productName);
    }
}
