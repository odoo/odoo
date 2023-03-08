/** @odoo-module */

import { debounce } from "@web/core/utils/timing";
import { usePos } from "@point_of_sale/app/pos_hook";

import { CategoryButton } from "./CategoryButton";

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ProductsWidgetControlPanel extends Component {
    static components = { CategoryButton };
    static template = "ProductsWidgetControlPanel";

    setup() {
        super.setup();
        this.pos = usePos();
        this.notification = useService("pos_notification");
        this.orm = useService("orm");
        this.updateSearch = debounce(this.updateSearch, 100);
        this.state = useState({ mobileSearchBarIsShown: false });
    }
    toggleMobileSearchBar() {
        this.state.mobileSearchBarIsShown = !this.state.mobileSearchBarIsShown;
    }
    _clearSearch() {
        this.env.pos.searchProductWord = "";
        this.props.clearSearch();
    }
    get displayCategImages() {
        return (
            Object.values(this.env.pos.db.category_by_id).some((categ) => categ.has_image) &&
            !this.env.isMobile
        );
    }
    updateSearch(event) {
        this.props.updateSearch(this.env.pos.searchProductWord);
        if (event.key === "Enter") {
            this._onPressEnterKey();
        }
    }
    async _onPressEnterKey() {
        if (!this.env.pos.searchProductWord) {
            return;
        }
        const result = await this.loadProductFromDB();
        this.notification.add(
            _.str.sprintf(
                this.env._t('%s product(s) found for "%s".'),
                result.length,
                this.env.pos.searchProductWord
            ),
            3000
        );
    }
    searchProductFromInfo(productName) {
        this.env.pos.searchProductWord = productName;
        this.props.switchCategory(0);
        this.props.updateSearch(productName);
    }
    async loadProductFromDB() {
        if (!this.env.pos.searchProductWord) {
            return;
        }

        const ProductIds = await this.orm.search("product.product", [
            "&",
            ["available_in_pos", "=", true],
            "|",
            "|",
            ["name", "ilike", this.env.pos.searchProductWord],
            ["default_code", "ilike", this.env.pos.searchProductWord],
            ["barcode", "ilike", this.env.pos.searchProductWord],
        ]);
        if (ProductIds.length) {
            await this.env.pos._addProducts(ProductIds, false);
        }
        this.props.updateProductList();
        return ProductIds;
    }
}
