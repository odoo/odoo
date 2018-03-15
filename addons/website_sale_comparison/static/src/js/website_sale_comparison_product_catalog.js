odoo.define('website_sale_comparison.product_catalog', function (require) {
'use strict';

var ProductCatalog = require('website_sale.product_catalog');
var ProductComparison = require('website_sale_comparison.comparison');
var WebsiteSaleUtils = require('website_sale.utils');

var Comparison = new ProductComparison();
Comparison.appendTo('body');

ProductCatalog.include({
    xmlDependencies: ProductCatalog.prototype.xmlDependencies.concat(
        '/website_sale_comparison/static/src/xml/website_sale_comparison_product_catalog.xml'
    ),
    events: _.extend({}, ProductCatalog.prototype.events, {
        'click .o-add-to-compare-btn [data-product-variant-id]': '_onClickAddToCompare',
    }),

    /**
     * On page reload disable compare button for those products which are already in comparison list
     *
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            _.each(Comparison.comparelist_product_ids, function (id) {
                self.$('.o-add-to-compare-btn [data-product-variant-id="' + id + '"]').prop('disabled', true);
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add product into comparison list
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddToCompare: function (ev) {
        var variantID = $(ev.currentTarget).data('product-variant-id');
        if (Comparison.comparelist_product_ids.length < Comparison.product_compare_limit) {
            Comparison.add_new_products(variantID);
            WebsiteSaleUtils.animate_clone($('#comparelist .o_product_panel_header'), $(ev.currentTarget).closest('.o-product-item'), -50, 10);
            $(ev.currentTarget).prop('disabled', true);
        } else {
            Comparison.$el.find('.o_comparelist_limit_warning').show();
            Comparison.show_panel(true);
        }
    },
});

});
