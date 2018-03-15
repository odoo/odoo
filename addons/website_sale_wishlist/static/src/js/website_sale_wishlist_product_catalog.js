odoo.define('website_sale_wishlist.product_catalog', function (require) {
'use strict';

var ProductCatalog = require('website_sale.product_catalog');
var ProductWishlist = require('website_sale_wishlist.wishlist');
var WebsiteSaleUtils = require('website_sale.utils');

var Wishlist = new ProductWishlist();

ProductCatalog.include({
    xmlDependencies: ProductCatalog.prototype.xmlDependencies.concat(
        '/website_sale_wishlist/static/src/xml/website_sale_wishlist_product_catalog.xml'
    ),
    events: _.extend({}, ProductCatalog.prototype.events, {
        'click .o-add-to-wishlist-btn [data-product-product-id]': '_onClickAddToWishlist',
    }),

    /**
     * On page reload disable whishlist button for those products which are already in whishlist
     *
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            _.each(Wishlist.wishlist_product_ids, function (id) {
                self.$('.o-add-to-wishlist-btn [data-product-product-id="' + id + '"]').prop('disabled', true);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add product into wishlist
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddToWishlist: function (ev) {
        $('#my_wish').show();
        Wishlist.add_new_products($(ev.currentTarget), ev);
        WebsiteSaleUtils.animate_clone($('#my_wish'), $(ev.currentTarget).closest('.o-product-item'), 25, 40);
        $(ev.currentTarget).prop('disabled', true);
    },
});

});
