odoo.define('point_of_sale.ProductsWidget', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductsWidgetControlPanel } = require('point_of_sale.ProductsWidgetControlPanel');
    const { ProductsList } = require('point_of_sale.ProductsList');

    class ProductsWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.clickProductHandler = this.props.clickProductHandler;
            const startCategoryId = this.pos.config.iface_start_categ_id
                ? this.pos.config.iface_start_categ_id[0]
                : 0;
            this.state = useState({ searchWord: '', selectedCategoryId: startCategoryId });
        }
        get searchWord() {
            return this.state.searchWord.trim();
        }
        get productsToDisplay() {
            if (this.searchWord !== '') {
                return this.pos.db.search_product_in_category(
                    this.state.selectedCategoryId,
                    this.searchWord
                );
            } else {
                return this.pos.db.get_product_by_category(this.state.selectedCategoryId);
            }
        }
        get subcategories() {
            return this.pos.db
                .get_category_childs_ids(this.state.selectedCategoryId)
                .map(id => this.pos.db.get_category_by_id(id));
        }
        get breadcrumbs() {
            if (this.state.selectedCategoryId === this.pos.db.root_category_id) return [];
            return [
                ...this.pos.db.get_category_ancestors_ids(this.state.selectedCategoryId).slice(1),
                this.state.selectedCategoryId,
            ].map(id => this.pos.db.get_category_by_id(id));
        }
        switchCategory(event) {
            // event detail is the id of the selected category
            this.state.selectedCategoryId = event.detail;
        }
        updateSearch(event) {
            this.state.searchWord = event.detail;
        }
        clearSearch() {
            this.state.searchWord = '';
        }
    }
    ProductsWidget.components = { ProductsWidgetControlPanel, ProductsList };

    return { ProductsWidget };
});
