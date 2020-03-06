odoo.define('point_of_sale.ProductsWidgetControlPanel', function(require) {
    'use strict';

    const { useRef } = owl.hooks;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { HomeCategoryBreadcrumb } = require('point_of_sale.HomeCategoryBreadcrumb');
    const { CategoryBreadcrumb } = require('point_of_sale.CategoryBreadcrumb');
    const { CategorySimpleButton } = require('point_of_sale.CategorySimpleButton');
    const { CategoryButton } = require('point_of_sale.CategoryButton');

    class ProductsWidgetControlPanel extends PosComponent {
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
    ProductsWidgetControlPanel.components = {
        HomeCategoryBreadcrumb,
        CategoryBreadcrumb,
        CategorySimpleButton,
        CategoryButton,
    };

    return { ProductsWidgetControlPanel };
});
