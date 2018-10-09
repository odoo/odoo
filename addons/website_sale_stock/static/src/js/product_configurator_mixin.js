odoo.define('website_sale_stock.ProductConfiguratorMixin', function (require) {
'use strict';

var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var sAnimations = require('website.content.snippets.animation');
var ajax = require('web.ajax');
var core = require('web.core');
var QWeb = core.qweb;
var xml_load = ajax.loadXML(
    '/website_sale_stock/static/src/xml/website_sale_stock_product_availability.xml',
    QWeb
);

/**
 * Addition to the product_configurator_mixin._onChangeCombination
 *
 * This will prevent the user from selecting a quantity that is not available in the
 * stock for that product.
 *
 * It will also display various info/warning messages regarding the select product's stock.
 *
 * This behavior is only applied for the web shop (and not on the SO form)
 * and only for the main product.
 *
 * @param {MouseEvent} ev
 * @param {$.Element} $parent
 * @param {Array} combination
 */
ProductConfiguratorMixin._onChangeCombinationStock = function (ev, $parent, combination) {
    var isMainProduct = combination.product_id &&
        ($parent.is('.js_main_product') || $parent.is('.main_product')) &&
        combination.product_id === parseInt($parent.find('.product_id').val());

    if (!this.isWebsite || !isMainProduct){
        return;
    }

    var qty = $parent.find('input[name="add_qty"]').val();

    $parent.find('#add_to_cart').removeClass('out_of_stock');
    if (_.contains(['always', 'threshold'], combination.inventory_availability)) {
        combination.virtual_available -= parseInt(combination.cart_qty);
        if (combination.virtual_available < 0) {
            combination.virtual_available = 0;
        }
        // Handle case when manually write in input
        if (qty > combination.virtual_available) {
            var $input_add_qty = $parent.find('input[name="add_qty"]');
            qty = combination.virtual_available || 1;
            $input_add_qty.val(qty);
        }
        if (qty > combination.virtual_available
            || combination.virtual_available < 1 || qty < 1) {
            $parent.find('#add_to_cart').addClass('disabled out_of_stock');
        }
    }

    xml_load.then(function () {
        $('.oe_website_sale')
            .find('.availability_message_' + combination.product_template)
            .remove();

        var $message = $(QWeb.render(
            'website_sale_stock.product_availability',
            combination
        ));
        $('div.availability_messages').html($message);
    });
};

sAnimations.registry.WebsiteSale.include({
    /**
     * Adds the stock checking to the regular _onChangeCombination method
     * @override
     */
    _onChangeCombination: function (){
        this._super.apply(this, arguments);
        ProductConfiguratorMixin._onChangeCombinationStock.apply(this, arguments);
    }
});

return ProductConfiguratorMixin;

});