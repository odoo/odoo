odoo.define('website_sale.s_dynamic_snippet_products', function (require) {
'use strict';

const config = require('web.config');
const core = require('web.core');
const publicWidget = require('web.public.widget');
const DynamicSnippetCarousel = require('website.s_dynamic_snippet_carousel');

const DynamicSnippetProducts = DynamicSnippetCarousel.extend({
    selector: '.s_dynamic_snippet_products',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Check product category exist.
     * @private
     * @returns {Promise}
     */
    _checkCategoryExist: async function (productCategoryId) {
        return this._rpc({
            model: 'product.public.category',
            method: 'search_count',
            args: [[['id', '=', productCategoryId]]],
        }).then(nb => nb > 0);
    },
    /**
     * Method to be overridden in child components if additional configuration elements
     * are required in order to fetch data.
     * @override
     * @private
     */
    _isConfigComplete: function () {
        return this._super.apply(this, arguments) && this.$el.get(0).dataset.productCategoryId !== undefined;
    },
    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @override
     * @private
     */
    _getSearchDomain: async function () {
        const searchDomain = await this._super.apply(this, arguments);
        const productCategoryId = parseInt(this.$el.get(0).dataset.productCategoryId);
        const categoryExist = await this._checkCategoryExist(productCategoryId);
        if (categoryExist) {
            searchDomain.push(['public_categ_ids', 'child_of', productCategoryId]);
        } else {
            searchDomain.push([0, '=', 1]);
        }
        return searchDomain;
    },

});
publicWidget.registry.dynamic_snippet_products = DynamicSnippetProducts;

return DynamicSnippetProducts;
});
