odoo.define('website_sale_.ProductConfiguratorMixin', function (require) {
'use strict';

var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');

/**
 * Website behavior is slightly different from backend so we append
 * "_website" to URLs to lead to a different route
 *
 * @private
 * @param {string} uri The uri to adapt
 */
ProductConfiguratorMixin._getUri = function (uri) {
    if (this.isWebsite){
        return uri + '_website';
    } else {
        return uri;
    }
};

return ProductConfiguratorMixin;

});
