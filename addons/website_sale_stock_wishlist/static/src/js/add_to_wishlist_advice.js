odoo.define('website_sale_stock_wishlist.VariantMixin', function (require) {
    'use strict';

    let xmlFiles = require('website_sale_stock.VariantMixin').xmlFiles;
    xmlFiles.push('/website_sale_stock_wishlist/static/src/xml/add_to_wishlist_advice.xml');
});
