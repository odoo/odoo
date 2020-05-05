odoo.define('point_of_sale.ProductsWidgetControlPanel', function(require) {
    'use strict';

    const { useRef } = owl.hooks;
    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ProductsWidgetControlPanel extends PosComponent {
        constructor() {
            super(...arguments);
            this.searchTimeout = null;
            this.searchWordInput = useRef('search-word-input');
            this.updateSearch = debounce(this.updateSearch, 100);
        }
        clearSearch() {
            this.searchWordInput.el.value = '';
            this.trigger('clear-search');
        }
        updateSearch(event) {
            this.trigger('update-search', event.target.value);
        }
    }
    ProductsWidgetControlPanel.template = 'ProductsWidgetControlPanel';

    Registries.Component.add(ProductsWidgetControlPanel);

    return ProductsWidgetControlPanel;
});
