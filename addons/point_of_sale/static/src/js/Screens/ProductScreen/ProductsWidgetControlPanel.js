odoo.define('point_of_sale.ProductsWidgetControlPanel', function(require) {
    'use strict';

    const { useRef } = owl.hooks;
    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { posbus } = require('point_of_sale.utils');

    class ProductsWidgetControlPanel extends PosComponent {
        constructor() {
            super(...arguments);
            this.searchWordInput = useRef('search-word-input');
            this.updateSearch = debounce(this.updateSearch, 100);
        }
        mounted() {
            posbus.on('search-product-from-info-popup', this, this.searchProductFromInfo)
        }
        willUnmount() {
            posbus.off('search-product-from-info-popup', this);
        }

        clearSearch() {
            this.searchWordInput.el.value = '';
            this.trigger('clear-search');
        }
        updateSearch(event) {
            this.trigger('update-search', event.target.value);
            if (event.key === 'Enter') {
                // We are passing the searchWordInput ref so that when necessary,
                // it can be modified by the parent.
                this.trigger('try-add-product', { searchWordInput: this.searchWordInput });
            }
        }
        searchProductFromInfo(productName) {
            this.searchWordInput.el.value = productName;
            this.trigger('switch-category', 0);
            this.trigger('update-search', productName);
        }
    }
    ProductsWidgetControlPanel.template = 'ProductsWidgetControlPanel';

    Registries.Component.add(ProductsWidgetControlPanel);

    return ProductsWidgetControlPanel;
});
