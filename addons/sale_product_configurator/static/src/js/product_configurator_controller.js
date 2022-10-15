odoo.define('sale_product_configurator.ProductConfiguratorFormController', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;
var FormController = require('web.FormController');
var OptionalProductsModal = require('sale_product_configurator.OptionalProductsModal');

var ProductConfiguratorFormController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        field_changed: '_onFieldChanged',
        handle_add: '_handleAdd'
    }),
    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.addClass('o_product_configurator');
        });
    },
    /**
     * We need to first load the template of the selected product and then render the content
     * to avoid a flicker when the modal is opened.
     *
     * @override
     */
    willStart: function () {
        var def = this._super.apply(this, arguments);
        if (this.initialState.data.product_template_id) {
            return this._configureProduct(
                this.initialState.data.product_template_id.data.id
            ).then(function () {
                return def;
            });
        }

        return def;
    },
    /**
     * Showing this window is useless for configuratorMode 'options' as this form view
     * is used as a bridge between SO lines and optional products.
     *
     * Placed here because it's the only method that is called after the modal is rendered.
     *
     * @override
     */
    renderButtons: function () {
        this._super.apply(this, arguments);

        if (this.renderer.state.context.configuratorMode === 'options') {
            this.$el.closest('.modal').addClass('d-none');
        }

        const renderSecondOnly = this.renderer.state.context.configuratorMode !== 'edit';
        this.$el.closest('.o_dialog_container').toggleClass('d-none', renderSecondOnly);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
    * We need to override the default click behavior for our "Add" button
    * because there is a possibility that this product has optional products.
    * If so, we need to display an extra modal to choose the options.
    *
    * @override
    */
    _onButtonClicked: function (event) {
        if (event.stopPropagation) {
            event.stopPropagation();
        }
        var attrs = event.data.attrs;
        if (attrs.special === 'cancel') {
            this._super.apply(this, arguments);
        } else {
            if (!this.$el
                    .parents('.modal')
                    .find('.o_sale_product_configurator_add')
                    .hasClass('disabled')) {
                this._handleAdd();
            }
        }
    },
    /**
     * This is overridden to allow catching the "select" event on our product template select field.
     *
     * @override
     * @private
     */
    _onFieldChanged: function (event) {
        this._super.apply(this, arguments);

        var self = this;
        var productId = event.data.changes.product_template_id.id;

        // check to prevent traceback when emptying the field
        if (!productId) {
            return;
        }

        this._configureProduct(event.data.changes.product_template_id.id)
            .then(function () {
                self.renderer.renderConfigurator(self.renderer.configuratorHtml);
            });
    },

    /**
     * Renders the "variants" part of the wizard
     *
     * @param {integer} productTemplateId
     */
    _configureProduct: function (productTemplateId) {
        var self = this;
        var initialProduct = this.initialState.data.product_template_id;
        var changed = initialProduct && initialProduct.data.id !== productTemplateId;
        var data = this.renderer.state.data;
        var quantity = initialProduct.context && initialProduct.context.default_quantity ? initialProduct.context.default_quantity : data.quantity;
        return this._rpc({
            route: '/sale_product_configurator/configure',
            params: {
                product_template_id: productTemplateId,
                pricelist_id: this.renderer.pricelistId,
                add_qty: quantity,
                product_template_attribute_value_ids: changed ? [] : this._getAttributeValueIds(
                    data.product_template_attribute_value_ids
                ),
                product_no_variant_attribute_value_ids: changed ? [] : this._getAttributeValueIds(
                    data.product_no_variant_attribute_value_ids
                )
            }
        }).then(function (configurator) {
            self.renderer.configuratorHtml = configurator;
        });
    },
    /**
    * When the user adds a product that has optional products, we need to display
    * a window to allow the user to choose these extra options.
    *
    * This will also create the product if it's in "dynamic" mode
    * (see product_attribute.create_variant)
    *
    * If "self.renderer.state.context.configuratorMode" is 'edit', this will only send
    * the main product with its changes.
    *
    * As opposed to the 'add' mode that will add the main product AND all the configured optional products.
    *
    * A third mode, 'options', is available for products that don't have a configuration but have
    * optional products to select. This will bypass the configuration step and open the
    * options modal directly.
    *
    * @private
    */
    _handleAdd: function () {
        var self = this;
        var $modal = this.$el;
        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];

        var productId = parseInt($modal.find(productSelector.join(', ')).first().val(), 10);
        var productTemplateId = $modal.find('.product_template_id').val();
        this.renderer.selectOrCreateProduct(
            $modal,
            productId,
            productTemplateId,
            false
        ).then(function (productId) {
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
                product_template_id: parseInt(productTemplateId),
                quantity: parseFloat($modal.find('input[name="add_qty"]').val() || 1),
                variant_values: variantValues,
                product_custom_attribute_values: productCustomVariantValues,
                no_variant_attribute_values: noVariantAttributeValues
            };

            if (self.renderer.state.context.configuratorMode === 'edit') {
                // edit mode only takes care of main product
                self._onAddRootProductOnly();
                return;
            }

            self.optionalProductsModal = new OptionalProductsModal($('body'), {
                rootProduct: self.rootProduct,
                pricelistId: self.renderer.pricelistId,
                okButtonText: _t('Confirm'),
                cancelButtonText: _t('Back'),
                title: _t('Configure'),
                context: self.initialState.context,
                previousModalHeight: self.$el.closest('.modal-content').height()
            }).open();

            self.optionalProductsModal.on('options_empty', null,
                // no optional products found for this product, only add the root product
                self._onAddRootProductOnly.bind(self));

            self.optionalProductsModal.on('update_quantity', null,
                self._onOptionsUpdateQuantity.bind(self));

            self.optionalProductsModal.on('confirm', null,
                self._onModalConfirm.bind(self));

            self.optionalProductsModal.on('closed', null,
                self._onModalClose.bind(self));
        });
    },

    /**
     * Add root product only and forget optional products.
     * Used when product has no optional products and in 'edit' mode.
     *
     * @private
     */
    _onAddRootProductOnly: function () {
        this._addProducts([this.rootProduct]);
    },

    /**
     * Add all selected products
     *
     * @private
     */
    _onModalConfirm: function () {
        this._wasConfirmed = true;
        this.optionalProductsModal.getAndCreateSelectedProducts().then((products) => {
            this._addProducts(products);
        });
    },

    /**
     * When the optional products modal is closed (and not confirmed) on 'options' mode,
     * this window should also be closed immediately.
     *
     * @private
     */
    _onModalClose: function () {
        if (['options', 'add'].includes(this.renderer.state.context.configuratorMode)
            && this._wasConfirmed !== true) {
            this.do_action({type: 'ir.actions.act_window_close'});
        }
    },

    /**
     * Remove "d-none" to allow other modals to display
     *
     * @override
     */
    destroy: function () {
        $('.o_dialog_container').removeClass('d-none');
        this._super.apply(this, arguments);
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
    * It will allow the caller (typically the product_configurator widget) of this window
    * to handle the added products.
    *
    * @private
    * @param {Array} products the list of added products
    *   {integer} products.product_id: the id of the product
    *   {integer} products.quantity: the added quantity for this product
    *   {Array} products.product_custom_attribute_values:
    *     see variant_mixin.getCustomVariantValues
    *   {Array} products.no_variant_attribute_values:
    *     see variant_mixin.getNoVariantAttributeValues
    */
    _addProducts: function (products) {
        this.do_action({type: 'ir.actions.act_window_close', infos: {
            mainProduct: products[0],
            options: products.slice(1)
        }});
    },
    /**
     * Extracts the ids from the passed attributeValueIds and returns them
     * as a plain array.
     *
     * @param {Array} attributeValueIds
     */
    _getAttributeValueIds: function (attributeValueIds) {
        if (!attributeValueIds || attributeValueIds.length === 0) {
            return false;
        }

        var result = [];
        _.each(attributeValueIds.data, function (attributeValue) {
            result.push(attributeValue.data.id);
        });

        return result;
    }
});

return ProductConfiguratorFormController;

});
