odoo.define('point_of_sale.ProductsWidgetControlPanel', function(require) {
    'use strict';

    const { identifyError } = require('point_of_sale.utils');
    const { ConnectionLostError, ConnectionAbortedError } = require('@web/core/network/rpc_service');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { debounce } = require("@web/core/utils/timing");

    const { onMounted, onWillUnmount, useRef } = owl;

    class ProductsWidgetControlPanel extends PosComponent {
        setup() {
            super.setup();
            this.searchWordInput = useRef('search-word-input-product');
            this.updateSearch = debounce(this.updateSearch, 100);

            onMounted(() => {
                this.env.posbus.on('search-product-from-info-popup', this, this.searchProductFromInfo)
                if(!this.env.pos.config.limited_products_loading)
                    this.env.pos.isEveryProductLoaded = true;
            });

            onWillUnmount(() => {
                this.env.posbus.off('search-product-from-info-popup', this);
            });
        }
        _clearSearch() {
            this.searchWordInput.el.value = '';
            this.trigger('clear-search');
        }
        get displayCategImages() {
            return Object.values(this.env.pos.db.category_by_id).some(categ => categ.has_image) && !this.env.isMobile;
        }
        updateSearch(event) {
            this.trigger('update-search', event.target.value);
            if (event.key === 'Enter') {
                this._onPressEnterKey()
            }
        }
        async _onPressEnterKey() {
            if (!this.searchWordInput.el.value) return;
            if (!this.env.pos.isEveryProductLoaded) {
                const result = await this.loadProductFromDB();
                this.showNotification(
                    _.str.sprintf(this.env._t('%s product(s) found for "%s".'),
                        result.length,
                        this.searchWordInput.el.value)
                    , 3000);
                if (!result.length) this._clearSearch();
            }
        }
        searchProductFromInfo(productName) {
            this.searchWordInput.el.value = productName;
            this.trigger('switch-category', 0);
            this.trigger('update-search', productName);
        }
        _toggleMobileSearchbar() {
            this.trigger('toggle-mobile-searchbar');
        }
        async loadProductFromDB() {
            if(!this.searchWordInput.el.value)
                return;

            try {
                let ProductIds = await this.rpc({
                    model: 'product.product',
                    method: 'search',
                    args: [['&',['available_in_pos', '=', true], '|','|',
                     ['name', 'ilike', this.searchWordInput.el.value],
                     ['default_code', 'ilike', this.searchWordInput.el.value],
                     ['barcode', 'ilike', this.searchWordInput.el.value]]],
                    context: this.env.session.user_context,
                });
                if(ProductIds.length) {
                    if (!this.env.pos.isEveryProductLoaded) await this.env.pos.updateIsEveryProductLoaded();
                    await this.env.pos._addProducts(ProductIds, false);
                }
                this.trigger('update-product-list');
                return ProductIds;
            } catch (error) {
                const identifiedError = identifyError(error)
                if (identifiedError instanceof ConnectionLostError || identifiedError instanceof ConnectionAbortedError) {
                    return this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t("Product is not loaded. Tried loading the product from the server but there is a network error."),
                    });
                } else {
                    throw error;
                }
            }
        }
    }
    ProductsWidgetControlPanel.template = 'ProductsWidgetControlPanel';

    Registries.Component.add(ProductsWidgetControlPanel);

    return ProductsWidgetControlPanel;
});
