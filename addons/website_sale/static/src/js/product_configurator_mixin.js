odoo.define('website_sale.ProductConfiguratorMixin', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.WebsiteSale.include({
    /**
     * This is overridden to handle the "List View of Variants" of the web shop.
     * That feature allows directly selecting the variant from a list instead of selecting the
     * attribute values.
     *
     * Since the layout is completely different, we need to fetch the product_id directly
     * from the selected variant.
     *
     */
    _getProductId: function ($parent){
        if ($parent.find('input.js_product_change').length !== 0) {
            return parseInt($parent.find('input.js_product_change:checked').val());
        } else {
            return this._super.apply(this, arguments);
        }
    }
});

});
