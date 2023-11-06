odoo.define('point_of_sale.ProductsWidget', function(require) {
    'use strict';

    const { identifyError } = require('point_of_sale.utils');
    const { ConnectionLostError, ConnectionAbortedError } = require('@web/core/network/rpc_service');
    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    const { onWillUnmount, useState } = owl;

    class ProductsWidget extends PosComponent {
        /**
         * @param {Object} props
         * @param {number?} props.startCategoryId
         */
        setup() {
            super.setup();
            useListener('switch-category', this._switchCategory);
            useListener('update-search', this._updateSearch);
            useListener('clear-search', this._clearSearch);
            useListener('load-products-from-server', this._onPressEnterKey);
            this.state = useState({ searchWord: '', previousSearchWord: "", currentOffset: 0 });
            onWillUnmount(this.onWillUnmount);
        }
        onWillUnmount() {
            this.trigger('toggle-mobile-searchbar', false);
        }
        get selectedCategoryId() {
            return this.env.pos.selectedCategoryId;
        }
        get searchWord() {
            return this.state.searchWord.trim();
        }
        get productsToDisplay() {
            let list = [];
            if (this.searchWord !== '') {
                list = this.env.pos.db.search_product_in_category(
                    this.selectedCategoryId,
                    this.searchWord
                );
            } else {
                list = this.env.pos.db.get_product_by_category(this.selectedCategoryId);
            }
            return list.sort(function (a, b) { return a.display_name.localeCompare(b.display_name) });
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
        get shouldShowButton() {
            return this.productsToDisplay.length === 0 && this.searchWord;
        }
        _switchCategory(event) {
            this.env.pos.setSelectedCategoryId(event.detail);
        }
        _updateSearch(event) {
            this.state.searchWord = event.detail;
        }
        _clearSearch() {
            this.state.searchWord = '';
        }
        _updateProductList(event) {
            this.render(true);
            this.trigger('switch-category', 0);
        }
        async _onPressEnterKey() {
            if (!this.state.searchWord) return;
            if (this.state.previousSearchWord != this.state.searchWord) {
                this.state.currentOffset = 0;
            }
            const result = await this.loadProductFromDB();
            if (result.length > 0) {
                this.showNotification(
                    _.str.sprintf(
                        this.env._t('%s product(s) found for "%s".'),
                        result.length,
                        this.state.searchWord
                    ),
                    3000
                );
            } else {
                this.showNotification(
                    _.str.sprintf(
                        this.env._t('No more product found for "%s".'),
                        this.state.searchWord
                    ),
                    3000
                );
            }
            if (this.state.previousSearchWord == this.state.searchWord) {
                this.state.currentOffset += result.length;
            } else {
                this.state.previousSearchWord = this.state.searchWord;
                this.state.currentOffset = result.length;
            }
        }
        async loadProductFromDB() {
            if(!this.state.searchWord)
                return;

            try {
                const limit = 30;
                let ProductIds = await this.rpc({
                    model: 'product.product',
                    method: 'search',
                    args: [['&',['available_in_pos', '=', true], '|','|',
                     ['name', 'ilike', this.state.searchWord],
                     ['default_code', 'ilike', this.state.searchWord],
                     ['barcode', 'ilike', this.state.searchWord]]],
                    context: this.env.session.user_context,
                    kwargs: {
                        offset: this.state.currentOffset,
                        limit: limit,
                    }
                });
                if(ProductIds.length) {
                    await this.env.pos._addProducts(ProductIds, false);
                }
                this._updateProductList();
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
    ProductsWidget.template = 'ProductsWidget';

    Registries.Component.add(ProductsWidget);

    return ProductsWidget;
});
