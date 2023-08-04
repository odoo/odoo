/** @odoo-module */

import { debounce } from "@web/core/utils/timing";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CategorySelector } from "@point_of_sale/app/generic_components/category_selector/category_selector";

export class ProductsWidgetControlPanel extends Component {
    static components = { CategorySelector };
    static template = "point_of_sale.ProductsWidgetControlPanel";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.notification = useService("pos_notification");
        this.orm = useService("orm");
        this.updateSearch = debounce(this.updateSearch, 100);
        this.state = useState({ mobileSearchBarIsShown: false, isMobile: false });
        this.productsWidgetControl = useRef("products-widget-control");

        const toggleIsMobile = () => this.toggleIsMobile();
        onMounted(() => {
            toggleIsMobile();
            window.addEventListener("resize", toggleIsMobile);
        });
        onWillUnmount(() => {
            window.removeEventListener("resize", toggleIsMobile);
        });
    }

    getCategoryImageUrl(category) {
        return `/web/image?model=pos.category&field=image_128&id=${category.id}&unique=${category.write_date}`;
    }
    /**
     * @param {Object} category - the object from `this.pos.db.category_by_id`
     * @returns {import("@point_of_sale/app/generic_components/category_selector/category_selector").Category}
     */
    formatCategoryObject(category) {
        const isRootCategory = category.id === this.pos.db.root_category_id;
        const hasSeparator =
            !isRootCategory &&
            [
                ...this.pos.db.get_category_ancestors_ids(this.pos.selectedCategoryId),
                this.pos.selectedCategoryId,
            ].includes(category.id);
        return {
            id: category.id,
            name: !isRootCategory ? category.name : "",
            icon: isRootCategory ? "fa-home fa-2x" : "",
            separator: hasSeparator ? "fa-caret-right" : "",
            imageUrl: category?.has_image && this.getCategoryImageUrl(category),
        };
    }
    /**
     * @returns {import("@point_of_sale/app/generic_components/category_selector/category_selector").Category[]}
     */
    getCategories() {
        return [
            ...this.pos.db.get_category_ancestors_ids(this.pos.selectedCategoryId),
            this.pos.selectedCategoryId,
            ...this.pos.db.get_category_childs_ids(this.pos.selectedCategoryId),
        ]
            .map((id) => this.pos.db.category_by_id[id])
            .map((category) => this.formatCategoryObject(category));
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
