odoo.define('sale.ProductConfiguratorFormRenderer', function (require) {
"use strict";

var FormRenderer = require('web.FormRenderer');
var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');

var ProductConfiguratorFormRenderer = FormRenderer.extend(ProductConfiguratorMixin ,{

    events: _.extend({}, FormRenderer.prototype.events, ProductConfiguratorMixin.events, {
        'click button.js_add_cart_json': 'onClickAddCartJSON',
    }),
    /**
     * @override
     */
    init: function (){
        this._super.apply(this, arguments);
        this.pricelistId = this.state.context.default_pricelist_id || 0;
    },
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.$el.append($('<div>', {class: 'configurator_container'}));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Renders the product configurator within the form
     *
     * Will also:
     *
     * - add events handling for variant changes
     * - trigger variant change to compute the price and other
     *   variant specific changes
     *
     * @param {string} configuratorHtml the evaluated template of
     *   the product configurator
     */
    renderConfigurator: function (configuratorHtml) {
        var $configuratorContainer = this.$('.configurator_container');
        $configuratorContainer.empty();

        var $configuratorHtml = $(configuratorHtml);
        $configuratorHtml.appendTo($configuratorContainer);

        this.triggerVariantChange($configuratorContainer);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Toggles the add button depending on the possibility of the current
     * combination.
     *
     * @override
     */
    _toggleDisable: function ($parent, isCombinationPossible) {
        ProductConfiguratorMixin._toggleDisable.apply(this, arguments);
        $parent.parents('.modal').find('.o_sale_product_configurator_add').toggleClass('disabled', !isCombinationPossible);
    },
});

return ProductConfiguratorFormRenderer;

});
