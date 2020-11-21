odoo.define('website_sale.s_dynamic_snippet_products_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');
const s_dynamic_snippet_carousel_options = require('website.s_dynamic_snippet_carousel_options');

const dynamicSnippetProductsOptions = s_dynamic_snippet_carousel_options.extend({

    /**
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.productCategories = {};
    },
    /**
     *
     * @override
     */
    onBuilt: function () {
        this._super.apply(this, arguments);
        this._rpc({
            model: 'ir.model.data',
            method: 'search_read',
            kwargs: {
                domain: [['module', '=', 'website_sale'], ['model', '=', 'website.snippet.filter']],
                fields: ['id', 'res_id'],
            }
        }).then((data) => {
            if (data) {
                this.$target.get(0).dataset.filterId = data[0].res_id;
                this.$target.get(0).dataset.numberOfRecords = this.dynamicFilters[data[0].res_id].limit;
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     *
     * @override
     * @private
     */
    _computeWidgetVisibility: function (widgetName, params) {
        if (widgetName === 'filter_opt') {
            return false;
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Fetches product categories.
     * @private
     * @returns {Promise}
     */
    _fetchProductCategories: function () {
        return this._rpc({
            model: 'product.public.category',
            method: 'search_read',
            kwargs: {
                domain: [],
                fields: ['id', 'name'],
            }
        });
    },
    /**
     *
     * @override
     * @private
     */
    _renderCustomXML: async function (uiFragment) {
        await this._super.apply(this, arguments);
        await this._renderProductCategorySelector(uiFragment);
    },
    /**
     * Renders the product categories option selector content into the provided uiFragment.
     * @private
     * @param {HTMLElement} uiFragment
     */
    _renderProductCategorySelector: async function (uiFragment) {
        const productCategories = await this._fetchProductCategories();
        for (let index in productCategories) {
            this.productCategories[productCategories[index].id] = productCategories[index];
        }
        const productCategoriesSelectorEl = uiFragment.querySelector('[data-name="product_category_opt"]');
        return this._renderSelectUserValueWidgetButtons(productCategoriesSelectorEl, this.productCategories);
    },

});

options.registry.dynamic_snippet_products = dynamicSnippetProductsOptions;

return dynamicSnippetProductsOptions;
});
