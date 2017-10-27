odoo.define('website_sale_comparison.product_catalog', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var ProductCatalog = require('website_sale.product_catalog');
var ProductComparison = require('website_sale_comparison.comparison');
var WebsiteSaleUtils = require('website_sale.utils');
var website = require('web_editor.base');

var QWeb = core.qweb;

ajax.loadXML('/website_sale_comparison/static/src/xml/website_sale_product_catalog.xml', QWeb);

website.ready().done(function () {

    if ($('.s_catalog').length) {

        var Comparison = new ProductComparison.ProductComparison();
        Comparison.appendTo('body');

        ProductCatalog.ProductCatalog.include({
            events: _.extend({}, ProductCatalog.ProductCatalog.prototype.events, {
                'click .add_to_compare': '_onClickAddToCompare',
            }),

            //--------------------------------------------------------------------------
            // Handlers
            //--------------------------------------------------------------------------

            /**
             * Called when the add to compare button is clicked.
             * Add product into compare list.
             *
             * @private
             * @param {MouseEvent} event
             */
            _onClickAddToCompare: function (event) {
                var variantID = $(event.currentTarget).data('product-variant-id');
                if (Comparison.comparelist_product_ids.length < Comparison.product_compare_limit) {
                    Comparison.add_new_products(variantID);
                    WebsiteSaleUtils.animate_clone($('#comparelist .o_product_panel_header'), $(event.currentTarget).parents('[class^="col-"]'), -50, 10);
                } else {
                    Comparison.$el.find('.o_comparelist_limit_warning').show();
                    Comparison.show_panel(true);
                }
            },
        });
    }

});

});
