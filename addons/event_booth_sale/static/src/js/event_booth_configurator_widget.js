odoo.define('event_booth_sale.product_configurator', function (require) {
const ProductConfiguratorWidget = require('sale.product_configurator');

/**
 * Extension of the ProductConfiguratorWidget to support event booth configuration.
 * It opens when an event booth product_product is set.
 *
 * The event booth information include:
 * - event_id
 * - event_booth_category_id
 * - event_booth_ids
 *
 */
ProductConfiguratorWidget.include({

    //--------------------------------------------------------------------------
    // Overrides
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean}
     *
     * @override
     * @private
     */
    _isConfigurableLine: function () {
        return this.recordData.detailed_type === 'event_booth' || this._super.apply(this, arguments);
    },

    /**
     * Opens the event booth configurator in 'edit' mode
     *
     * @override
     * @private
     */
    _onEditLineConfiguration: function () {
        if (this.recordData.detailed_type === 'event_booth') {
            const defaultValues = {
                default_product_id: this.recordData.product_id.data.id,
                default_sale_order_line_id: this.recordData.id || null
            };
            if (this.recordData.event_id) {
                defaultValues.default_event_id = this.recordData.event_id.data.id;
            }
            if (this.recordData.event_booth_category_id) {
                defaultValues.default_event_booth_category_id = this.recordData.event_booth_category_id.data.id;
            }
            if (this.recordData.event_booth_pending_ids) {
                defaultValues.default_event_booth_ids = this.recordData.event_booth_pending_ids.res_ids;
            }
            this._openEventBoothConfigurator(defaultValues, this.dataPointID);
        } else {
            this._super.apply(this, arguments);
        }
    },

    /**
     * @param {integer} productId: product.product ID
     * @param {String} dataPointId
     * @returns {Promise<Boolean>} stopPropagation true if a suitable configurator has been found.
     *
     * @override
     * @private
     */
    _onProductChange: function (productId, dataPointId) {
        return this._super.apply(this, arguments).then((stopPropagation) => {
            if (stopPropagation) {
                return Promise.resolve(true);
            } else {
                return this._isProductEventBooth(productId, dataPointId);
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //-------------------------------------------------------------------------

    /**
     * This method will check if the productId needs a configuration or not.
     *
     * @param {integer} productId: product.product ID
     * @param {String} dataPointId
     * @returns {Promise<Boolean>} stopPropagation true if the product is an event booth.
     *
     * @private
     */
    _isProductEventBooth: function (productId, dataPointId) {
        const self = this;
        return this._rpc({
            model: 'product.product',
            method: 'read',
            args: [productId, ['detailed_type']],
        }).then(function (result) {
            if (result && result[0].detailed_type === 'event_booth') {
                self._openEventBoothConfigurator({
                    default_product_id: productId
                }, dataPointId);
                return Promise.resolve(true);
            }
            return Promise.resolve(false);
        });
    },

    /**
     * Opens the event booth configurator allowing to configure the SO line with its informations.
     *
     * When the window is closed, configured values are used to trigger a 'field_changed'
     * event to modify the current SO line.
     *
     * If the window is closed without providing the required values 'event_id', 'event_booth_category_id'
     * and 'event_booth_pending_ids', the product_id field is cleaned.
     *
     * @param {Object} additionalContext: various "default_" values added to context when calling
     *  configuration wizard model;
     * @param dataPointId
     *
     * @private
     */
    _openEventBoothConfigurator: function (additionalContext, dataPointId) {
        const self = this;
        this.do_action('event_booth_sale.event_booth_configurator_action', {
            additional_context: additionalContext,
            on_close: function (result) {
                if (result && !result.special) {
                    self.trigger_up('field_changed', {
                        changes: result.eventBoothConfiguration,
                        dataPointID: dataPointId,
                        onSuccess: function () {
                            self._onLineConfigured();
                        }
                    });
                } else if (!self.recordData.event_id || !self.recordData.event_booth_pending_ids) {
                    self.trigger_up('field_changed', {
                        changes: {
                            product_id: false,
                            name: '',
                        },
                        dataPointID: dataPointId,
                    });
                }
            }
        });
    },
});

return ProductConfiguratorWidget;

});
