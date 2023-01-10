odoo.define('website_sale.s_dynamic_snippet_products', function (require) {
'use strict';

const config = require('web.config');
const core = require('web.core');
const publicWidget = require('web.public.widget');
const DynamicSnippetCarousel = require('website.s_dynamic_snippet_carousel');
var wSaleUtils = require('website_sale.utils');

const DynamicSnippetProducts = DynamicSnippetCarousel.extend({
    selector: '.s_dynamic_snippet_products',
    read_events: {
        'click .js_add_cart': '_onAddToCart',
        'click .js_remove': '_onRemoveFromRecentlyViewed',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @override
     * @private
     */
    _getSearchDomain: function () {
        const searchDomain = this._super.apply(this, arguments);
        let productCategoryId = this.$el.get(0).dataset.productCategoryId;
        if (productCategoryId && productCategoryId !== 'all') {
            if (productCategoryId === 'current') {
                productCategoryId = undefined;
                const productCategoryField = $("#product_details").find(".product_category_id");
                if (productCategoryField && productCategoryField.length) {
                    productCategoryId = parseInt(productCategoryField[0].value);
                }
                if (!productCategoryId) {
                    this.trigger_up('main_object_request', {
                        callback: function (value) {
                            if (value.model === "product.public.category") {
                                productCategoryId = value.id;
                            }
                        },
                    });
                }
                if (!productCategoryId) {
                    // Try with categories from product, unfortunately the category hierarchy is not matched with this approach
                    const productTemplateId = $("#product_details").find(".product_template_id");
                    if (productTemplateId && productTemplateId.length) {
                        searchDomain.push(['public_categ_ids.product_tmpl_ids', '=', parseInt(productTemplateId[0].value)]);
                    }
                }
            }
            if (productCategoryId) {
                searchDomain.push(['public_categ_ids', 'child_of', parseInt(productCategoryId)]);
            }
        }
        const productNames = this.$el.get(0).dataset.productNames;
        if (productNames) {
            const nameDomain = [];
            for (const productName of productNames.split(',')) {
                if (nameDomain.length) {
                    nameDomain.unshift('|');
                }
                nameDomain.push(['name', 'ilike', productName]);
            }
            searchDomain.push(...nameDomain);
        }
        return searchDomain;
    },
    /**
     * @override
     */
    _getRpcParameters: function () {
        const productTemplateId = $("#product_details").find(".product_template_id");
        return Object.assign(this._super.apply(this, arguments), {
            productTemplateId: productTemplateId && productTemplateId.length ? productTemplateId[0].value : undefined,
        });
    },
    /**
     * Add product to cart and reload the carousel.
     * @private
     * @param {Event} ev
     */
    _onAddToCart: function (ev) {
        var self = this;
        var $card = $(ev.currentTarget).closest('.card');
        this._rpc({
            route: "/shop/cart/update_json",
            params: {
                product_id: $card.find('input[data-product-id]').data('product-id'),
                add_qty: 1
            },
        }).then(function (data) {
            var $navButton = $('header .o_wsale_my_cart').first();
            var fetch = self._fetchData();
            var animation = wSaleUtils.animateClone($navButton, $(ev.currentTarget).parents('.card'), 25, 40);
            Promise.all([fetch, animation]).then(function (values) {
                wSaleUtils.updateCartNavBar(data);
                if (self.add2cartRerender) {
                     self._render();
                }
            });
        });
    },
    /**
     * @override 
     * @private
     */
    _renderContent() {
        this._super(...arguments);
        this.add2cartRerender = !!this.el.querySelector('[data-add2cart-rerender="True"]');
    },
    /**
     * Remove product from recently viewed products.
     * @private
     * @param {Event} ev
     */
    _onRemoveFromRecentlyViewed: function (ev) {
        var self = this;
        var $card = $(ev.currentTarget).closest('.card');
        this._rpc({
            route: "/shop/products/recently_viewed_delete",
            params: {
                product_id: $card.find('input[data-product-id]').data('product-id'),
            },
        }).then(function (data) {
            self._fetchData().then(() => self._render());
        });
    },

});
publicWidget.registry.dynamic_snippet_products = DynamicSnippetProducts;

return DynamicSnippetProducts;
});
