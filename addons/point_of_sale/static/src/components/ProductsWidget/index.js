odoo.define('point_of_sale.ProductsWidget', function(require) {
    'use strict';

    const { Component } = owl;
    const { useState, useRef } = owl.hooks;

    class HomeCategoryBreadcrumb extends Component {}
    class CategoryBreadcrumb extends Component {}
    class CategorySimpleButton extends Component {}
    class CategoryButton extends Component {
        get imageUrl() {
            return `${window.location.origin}/web/image?model=pos.category&field=image_128&id=${this.props.category.id}`;
        }
    }
    class ProductsWidgetControl extends Component {
        constructor() {
            super(...arguments);
            this.searchTimeout = null;
            this.searchWordInput = useRef('search-word-input');
        }
        clearSearch() {
            this.searchWordInput.el.value = '';
            this.trigger('clear-search');
        }
        updateSearch(event) {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.trigger('update-search', event.target.value);
            }, 70);
        }
    }
    ProductsWidgetControl.components = {
        HomeCategoryBreadcrumb,
        CategoryBreadcrumb,
        CategorySimpleButton,
        CategoryButton,
    };

    class ProductDisplay extends Component {
        /**
         * For accessibility, pressing <space> should be like clicking the product.
         * <enter> is not considered because it conflicts with the barcode.
         *
         * @param {KeyPressEvent} event
         */
        spaceClickProduct(event) {
            if (event.which === 32) {
                this.trigger('click-product', this.props.product);
            }
        }
        get imageUrl() {
            return `${window.location.origin}/web/image?model=product.product&field=image_128&id=${this.props.product.id}`;
        }
        get pricelist() {
            const current_order = this.props.pos.get_order();
            if (current_order) {
                return current_order.pricelist;
            }
            return this.props.pos.default_pricelist;
        }
        get price() {
            const formattedUnitPrice = this.props.pos.format_currency(
                this.props.product.get_price(this.pricelist, 1),
                'Product Price'
            );
            if (this.props.product.to_weight) {
                return `${formattedUnitPrice}/${
                    this.props.pos.units_by_id[this.props.product.uom_id[0]].name
                }`;
            } else {
                return formattedUnitPrice;
            }
        }
    }
    class ProductsList extends Component {}
    ProductsList.components = { ProductDisplay };

    class ProductsWidget extends Component {
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
        clickProduct(event) {
            // event detail is the product
            const product = event.detail;
            this.clickProductHandler(product);
        }
        updateSearch(event) {
            this.state.searchWord = event.detail;
        }
        clearSearch() {
            this.state.searchWord = '';
        }
    }
    ProductsWidget.components = { ProductsWidgetControl, ProductsList };

    return {
        HomeCategoryBreadcrumb,
        CategoryBreadcrumb,
        CategorySimpleButton,
        CategoryButton,
        ProductsWidgetControl,
        ProductDisplay,
        ProductsList,
        ProductsWidget,
    };
});
