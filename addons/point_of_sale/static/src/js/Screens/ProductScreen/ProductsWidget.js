odoo.define('point_of_sale.ProductsWidget', function(require) {
    'use strict';

    const { useState } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class ProductsWidget extends PosComponent {
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
        mounted() {
            this.env.pos.on('change:selectedCategoryId', this.render, this);
        }
        willUnmount() {
            this.env.pos.off('change:selectedCategoryId', null, this);
        }
        get selectedCategoryId() {
            return this.env.pos.get('selectedCategoryId');
        }
        get searchWord() {
            return this.state.searchWord.trim();
        }
        get productsToDisplay() {
            if (this.searchWord !== '') {
                return this.env.pos.db.search_product_in_category(
                    this.selectedCategoryId,
                    this.searchWord
                );
            } else {
                return this.env.pos.db.get_product_by_category(this.selectedCategoryId);
            }
        }
        get subcategories() {
            return this.env.pos.db
                .get_category_childs_ids(this.selectedCategoryId)
                .map(id => this.env.pos.db.get_category_by_id(id));
        }
        get breadcrumbs() {
            if (this.selectedCategoryId === this.env.pos.db.root_category_id) return [];
            return [
                ...this.env.pos.db
                    .get_category_ancestors_ids(this.selectedCategoryId)
                    .slice(1),
                this.selectedCategoryId,
            ].map(id => this.env.pos.db.get_category_by_id(id));
        }
        get hasNoCategories() {
            return this.env.pos.db.get_category_childs_ids(0).length === 0;
        }
        _switchCategory(event) {
            this.env.pos.set('selectedCategoryId', event.detail);
        }
        _updateSearch(event) {
            this.state.searchWord = event.detail;
        }
        _clearSearch() {
            this.state.searchWord = '';
        }
    }
    ProductsWidget.template = 'ProductsWidget';

    Registries.Component.add(ProductsWidget);

    return ProductsWidget;
});
