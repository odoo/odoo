odoo.define('sale.ProductConfiguratorFormController', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;
var FormController = require('web.FormController');
var OptionalProductsModal = require('sale.OptionalProductsModal');

var ProductConfiguratorFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        field_changed: '_onFieldChanged'
    }),
    className: 'o_product_configurator',
    /**
     * @override
     */
    init: function (){
        this._super.apply(this, arguments);
    },
    /**
     * We need to override the default click behavior for our "Add" button
     * because there is a possibility that this product has optional products.
     * If so, we need to display an extra modal to choose the options
     *
     * @override
     */
    _onButtonClicked: function (event) {
        if (event.stopPropagation){
            event.stopPropagation();
        }
        var attrs = event.data.attrs;
        if (attrs.special === 'cancel') {
            this._super.apply(this, arguments);
        } else {
            if (!this.$el
                    .parents('.modal')
                    .find('.o_sale_product_configurator_add')
                    .hasClass('disabled')){
                this._handleAdd(this.$el);
            }
        }
    },
    /**
     * This is overridden to allow catching the "select" event on our product template select field.
     * This will not work anymore if more fields are added to the form.
     * TODO: Find a better way to catch that event.
     *
     * @override
     */
    _onFieldChanged: function (event) {
        var self = this;

        this.$el.parents('.modal').find('.o_sale_product_configurator_add').removeClass('disabled');

        this._rpc({
            route: '/product_configurator/configure',
            params: {
                product_id: event.data.changes.product_template_id.id,
                pricelist_id: $('.js_sale_order_pricelist_id').html()
            }
        }).then(function (configurator) {
            self.renderer.renderConfigurator(configurator);
        });

        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
    * When the user adds a product that has optional products, we need to display
    * a window to allow the user to choose these extra options
    *
    * @private
    */
    _handleAdd: function ($modal) {
        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];

        this.rootProduct = {
            product_id: parseInt($modal.find(productSelector.join(', ')).first().val(), 10),
            quantity: parseFloat($modal.find('input[name="add_qty"]').val() || 1),
            product_custom_variant_values: this.renderer.getCustomVariantValues($modal.find('.js_product'))
        };

        this.optionalProductsModal = new OptionalProductsModal($('body'), {
            rootProduct: this.rootProduct,
            pricelistId: $('.js_sale_order_pricelist_id').html(),
            okButtonText: _t('Confirm'),
            cancelButtonText: _t('Back'),
            title: _t('Configure')
        }).open();

        this.optionalProductsModal.on('options_empty', null, this._onModalOptionsEmpty.bind(this));
        this.optionalProductsModal.on('confirm', null, this._onModalConfirm.bind(this));
    },

    /**
     * No optional products found for this product, only add the root product
     *
     * @private
     */
    _onModalOptionsEmpty: function () {
        this._addProducts([this.rootProduct]);
    },

    /**
     * Add all selected products
     *
     * @private
     */
    _onModalConfirm: function () {
        this._addProducts(this.optionalProductsModal.getSelectedProducts());
    },

    /**
    * This triggers the close action for the window and
    * adds the product as the "infos" parameter.
    * It will allow the caller of this window to handle the added products.
    *
    * @private
    * @param {Array} products the list of added products
    *   {integer} products.product_id: the id of the product
    *   {integer} products.quantity: the added quantity for this product
    */
    _addProducts: function (products) {
        this.do_action({type: 'ir.actions.act_window_close', infos: products});
    }
});

return ProductConfiguratorFormController;

});