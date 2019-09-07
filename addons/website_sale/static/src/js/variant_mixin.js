odoo.define('website_sale.VariantMixin', function (require) {
'use strict';

var VariantMixin = require('sale.VariantMixin');

/**
 * Website behavior is slightly different from backend so we append
 * "_website" to URLs to lead to a different route
 *
 * @private
 * @param {string} uri The uri to adapt
 */
VariantMixin._getUri = function (uri) {
    if (this.isWebsite){
        return uri + '_website';
    } else {
        return uri;
    }
};

return VariantMixin;

});
