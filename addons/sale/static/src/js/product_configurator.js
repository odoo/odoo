odoo.define('sale.ProductConfiguratorFormRenderer', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');
    var ProductConfiguratorUtils = require('sale.product_configurator_utils');

    var ProductConfiguratorFormRenderer = FormRenderer.extend({
        /**
         * @override
         */
        start: function () {
            this._super.apply(this, arguments);
            this.$el.append('<div class="configurator_container"></div>');
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @public
         * Renders the product configurator within the form
         */
        render_configurator: function (configurator) {
            var $configurator_container = this.$el.find('.configurator_container');
            $configurator_container.empty();

            var $configurator = $(configurator);
            $configurator.appendTo($configurator_container);

            ProductConfiguratorUtils.addConfiguratorEvents($configurator_container, "", false, $('.js_sale_order_pricelist_id').html());
            
            $('.js_add_cart_variants', $configurator_container).each(function () {
                $('input.js_variant_change, select.js_variant_change', this).first().trigger('change');
            });
        }
    });

    return ProductConfiguratorFormRenderer;
});

odoo.define('sale.ProductConfiguratorFormController', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var ajax = require('web.ajax');
    var FormController = require('web.FormController');
    var OptionalProductsModal = require('sale.OptionalProductsModal');

    var ProductConfiguratorFormController = FormController.extend({
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            field_changed: '_onFieldChanged'
        }),
        className: 'o_product_configurator',
        /**
         * @override
         * We need to override the default click behavior for our "Add" button
         * because there is a possibility that this product has optional products.
         * If so, we need to display an extra modal to choose the options
         */
        _onButtonClicked: function (event) {
            if(event.stopPropagation){
                event.stopPropagation();
            }
            var attrs = event.data.attrs;
            if (attrs.special === 'cancel') {
                this._super.apply(this, arguments);
            } else {
                if(!this.$el.parents('.modal').find('.o_sale_product_configurator_add').hasClass('disabled')){
                    this._handleAdd(this.$el);
                }
            }
        },
        /**
         * @override
         * This is overriden to allow catching the "select" event on our product template select field.
         * This will not work anymore if more fields are added to the form.
         * TODO: Find a better way to catch that event.
         */
        _onFieldChanged: function (event) {
            var self = this;

            self.$el.parents('.modal').find('.o_sale_product_configurator_add').removeClass('disabled');

            ajax.jsonRpc("/product_configurator/configure", 'call', {
                'product_id': event.data.changes.product_template_id.id,
                'pricelist_id': $('.js_sale_order_pricelist_id').html()
            }).then(function (configurator) {
                self.renderer.render_configurator(configurator);
            });

            this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
        * @private
        * When the user adds a product that has optional products, we need to display
        * a window to allow the user to choose these extra options
        */
       _handleAdd: function ($modal) {
            var self = this;
            var quantity = parseFloat($modal.find('input[name="add_qty"]').val() || 1);
            var product_id = parseInt($modal.find('input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked').first().val(), 10);

            var modal = new OptionalProductsModal(quantity, product_id, $('body'), $('.js_sale_order_pricelist_id').html());

            // No optional products found for this product, 
            // only add the root product
            modal.on('options_empty', null, function () {
                self._addProducts([{
                    product_id: product_id,
                    quantity: quantity
                }]);
            });

            // Add all the selected products
            modal.on('confirm', null, function () {
                self._addProducts(modal.getSelectedProducts());
            });

            // Change the buttons translation when the modal is ready
            modal.on('modal_ready', null, function ($modal) {
                $modal.find('a.go-back').attr('title', _t('Back'));
                $modal.find('a.go-back .d-md-inline').html(_t('Back'));
                $modal.find('a.confirm').attr('title', _t('Confirm'));
                $modal.find('a.confirm .d-md-inline').html(_t('Confirm'));
            });

            modal.appendTo($('body'));
        },

        /**
        * @private
        * This triggers the close action for the window and adds the product as the "infos" parameter.
        * It will allow the caller of this window to handle the added products.
        */
        _addProducts: function(products) {
            this.do_action({type: 'ir.actions.act_window_close', infos: products});
        }
    });

    return ProductConfiguratorFormController;
});

odoo.define('sale.ProductConfiguratorFormView', function (require) {
    "use strict";

    var ProductConfiguratorFormController = require('sale.ProductConfiguratorFormController');
    var ProductConfiguratorFormRenderer = require('sale.ProductConfiguratorFormRenderer');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var ProductConfiguratorFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: ProductConfiguratorFormController,
            Renderer: ProductConfiguratorFormRenderer,
        }),
    });

    viewRegistry.add('product_configurator_form', ProductConfiguratorFormView);

    return ProductConfiguratorFormView;
});