odoo.define('point_of_sale.ProductsWidget', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { ProductsWidgetControlPanel } = require('point_of_sale.ProductsWidgetControlPanel');
    const { ProductsList } = require('point_of_sale.ProductsList');
    const { useListener } = require('web.custom_hooks');

    class ProductsWidget extends PosComponent {
        static template = 'ProductsWidget';
        /**
         * @param {Object} props
         * @param {number?} props.startCategoryId
         */
        constructor() {
            super(...arguments);
            useListener('switch-category', this._switchCategory);
            useListener('update-search', this._updateSearch);
            useListener('clear-search', this._clearSearch);
            this.state = useState({ searchWord: '' });
        }
        get searchWord() {
            return this.state.searchWord.trim();
        }
        get productsToDisplay() {
            if (this.searchWord !== '') {
                return this.env.pos.db.search_product_in_category(
                    this.props.selectedCategoryId.value,
                    this.searchWord
                );
            } else {
                return this.env.pos.db.get_product_by_category(this.props.selectedCategoryId.value);
            }
        }
        get subcategories() {
            return this.env.pos.db
                .get_category_childs_ids(this.props.selectedCategoryId.value)
                .map(id => this.env.pos.db.get_category_by_id(id));
        }
        get breadcrumbs() {
            if (this.props.selectedCategoryId.value === this.env.pos.db.root_category_id) return [];
            return [
                ...this.env.pos.db
                    .get_category_ancestors_ids(this.props.selectedCategoryId.value)
                    .slice(1),
                this.props.selectedCategoryId.value,
            ].map(id => this.env.pos.db.get_category_by_id(id));
        }
        _switchCategory(event) {
            // event detail is the id of the selected category
            this.props.selectedCategoryId.value = event.detail;
            this.trigger('set-selected-category-id', event.detail);
        }
        _updateSearch(event) {
            this.state.searchWord = event.detail;
        }
        _clearSearch() {
            this.state.searchWord = '';
        }
    }
    ProductsWidget.components = { ProductsWidgetControlPanel, ProductsList };

    return { ProductsWidget };
});
