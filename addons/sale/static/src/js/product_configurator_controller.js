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
     * If so, we need to display an extra modal to choose the options.
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
     * TODO awa: Find a better way to catch that event.
     *
     * @override
     */
    _onFieldChanged: function (event) {
        this._super.apply(this, arguments);

        var self = this;
        var product_id = event.data.changes.product_template_id.id;

        // check to prevent traceback when emptying the field
        if (!product_id) {
            return;
        }

        this.$el.parents('.modal').find('.o_sale_product_configurator_add').removeClass('disabled');

        this._rpc({
            route: '/product_configurator/configure',
            params: {
                product_id: product_id,
                pricelist_id: this.renderer.pricelistId
            }
        }).then(function (configurator) {
            self.renderer.renderConfigurator(configurator);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
    * When the user adds a product that has optional products, we need to display
    * a window to allow the user to choose these extra options.
    *
    * This will also create the product if it's in "dynamic" mode
    * (see product_attribute.create_variant)
    *
    * @private
    * @param {$.Element} $modal
    */
    _handleAdd: function ($modal) {
        var self = this;
        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];

        var productId = parseInt($modal.find(productSelector.join(', ')).first().val(), 10);
        var productReady = this.renderer.selectOrCreateProduct(
            $modal,
            productId,
            $modal.find('.product_template_id').val(),
            false
        );

        productReady.done(function (productId) {
            $modal.find(productSelector.join(', ')).val(productId);

            var variantValues = self
                .renderer
                .getSelectedVariantValues($modal.find('.js_product'));

            var productCustomVariantValues = self
                .renderer
                .getCustomVariantValues($modal.find('.js_product'));

            var noVariantAttributeValues = self
                .renderer
                .getNoVariantAttributeValues($modal.find('.js_product'));

            self.rootProduct = {
                product_id: productId,
                quantity: parseFloat($modal.find('input[name="add_qty"]').val() || 1),
                variant_values: variantValues,
                product_custom_attribute_values: productCustomVariantValues,
                no_variant_attribute_values: noVariantAttributeValues
            };

            self.optionalProductsModal = new OptionalProductsModal($('body'), {
                rootProduct: self.rootProduct,
                pricelistId: self.renderer.pricelistId,
                okButtonText: _t('Confirm'),
                cancelButtonText: _t('Back'),
                title: _t('Configure')
            }).open();

            self.optionalProductsModal.on('options_empty', null,
                self._onModalOptionsEmpty.bind(self));

            self.optionalProductsModal.on('update_quantity', null,
                self._onOptionsUpdateQuantity.bind(self));

            self.optionalProductsModal.on('confirm', null,
                self._onModalConfirm.bind(self));
        });
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
     * Update product configurator form
     * when quantity is updated in the optional products window
     *
     * @private
     * @param {integer} quantity
     */
    _onOptionsUpdateQuantity: function (quantity) {
        this.$el
            .find('input[name="add_qty"]')
            .val(quantity)
            .trigger('change');
    },

    /**
    * This triggers the close action for the window and
    * adds the product as the "infos" parameter.
    * It will allow the caller (typically the SO line form) of this window
    * to handle the added products.
    *
    * @private
    * @param {Array} products the list of added products
    *   {integer} products.product_id: the id of the product
    *   {integer} products.quantity: the added quantity for this product
    *   {Array} products.product_custom_attribute_values:
    *     see product_configurator_mixin.getCustomVariantValues
    *   {Array} products.no_variant_attribute_values:
    *     see product_configurator_mixin.getNoVariantAttributeValues
    */
    _addProducts: function (products) {
        this.do_action({type: 'ir.actions.act_window_close', infos: products});
    }
});

return ProductConfiguratorFormController;

});