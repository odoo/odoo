odoo.define('event_booth_sale.product_configurator', function (require) {
var ProductConfiguratorWidget = require('sale.product_configurator');

/**
 * Extension of the ProductConfiguratorWidget to support event booth configuration.
 * It opens when an event booth product_product is set.
 *
 * The event booth information include:
 * - event_id
 * - event_booth_id
 * - event_booth_slot_ids
 *
 */
ProductConfiguratorWidget.include({

    /**
     * @returns {boolean}
     *
     * @override
     * @private
     */
    _isConfigurableLine: function () {
        return this.recordData.is_event_booth || this._super.apply(this, arguments);
    },

    /**
     * Opens the event booth configurator in 'edit' mode
     *
     * @override
     * @private
     */
    _onEditLineConfiguration: function () {
        if (this.recordData.is_event_booth) {
            var defaultValues = {
                default_product_id: this.recordData.product_id.data.id,
                default_sale_order_line_id: this.recordData.id || null
            };
            if (this.recordData.event_id) {
                defaultValues.default_event_id = this.recordData.event_id.data.id;
            }
            if (this.recordData.event_booth_id) {
                defaultValues.default_event_booth_id = this.recordData.event_booth_id.data.id;
            }
            if (this.recordData.event_booth_slot_ids) {
                defaultValues.default_event_booth_slot_ids = this.recordData.event_booth_slot_ids.res_ids;
            }
            this._openEventBoothConfigurator(defaultValues, this.dataPointID);
        } else {
            this._super.apply(this, arguments);
        }
    },

    /**
     * @param {integer} productId
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
                return this._checkForEventBooth(productId, dataPointId);
            }
        });
    },

    /**
     * This method will check if the productId needs a configuration or not.
     *
     * @param {integer} productId
     * @param {String} dataPointId
     * @returns {Promise<Boolean>} stopPropagation true if the product is an event booth.
     *
     * @private
     */
    _checkForEventBooth: function (productId, dataPointId) {
        var self = this;
        return this._rpc({
            model: 'product.product',
            method: 'read',
            args: [productId, ['is_event_booth']],
        }).then(function (result) {
            if (result && result[0].is_event_booth) {
                self._openEventBoothConfigurator({
                    default_product_id: productId
                }, dataPointId);
                return Promise.resolve(true);
            }
            return Promise.resolve(false);
        });
    },

    /**
     * Opens the event booth configurator allowing to configure the SO line with the
     * booth slots informations.
     *
     * When the window is closed, configured values are used to trigger a 'field_changed'
     * event to modify the current SO line.
     *
     * If the window is closed without providing the required values 'event_id', 'event_booth_id'
     * and 'event_booth_slot_ids', the product_id field is cleaned.
     *
     * @param {Object} data various "default_" values
     * @param dataPointId
     *
     * @private
     */
    _openEventBoothConfigurator: function (data, dataPointId) {
        var self = this;
        this.do_action('event_booth_sale.event_booth_configurator_action', {
            additional_context: data,
            on_close: function (result) {
                if (result && !result.special) {
                    self.trigger_up('field_changed', {
                        dataPointID: dataPointId,
                        changes: result.eventBoothConfiguration,
                        onSuccess: function () {
                            self._onLineConfigured();
                        }
                    });
                } else {
                    if (!self.recordData.event_id || !self.recordData.event_booth_id) {
                        self.trigger_up('field_changed', {
                            dataPointID: dataPointId,
                            changes: {
                                product_id: false,
                                name: ''
                            },
                        });
                    }
                }
            }
        });
    },
});

return ProductConfiguratorWidget;

});
