odoo.define('event_sale.product_configurator', function (require) {
var ProductConfiguratorWidget = require('sale.product_configurator');

/**
 * Extension of the ProductConfiguratorWidget to support event product configuration.
 * It opens when an event product_product is set.
 *
 * The event information include:
 * - event_id
 * - event_ticket_id
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
        return this.recordData.event_ok || this._super.apply(this, arguments);
    },

    /**
     * @param {integer} productId
     * @param {String} dataPointID
     * @returns {Promise<Boolean>} stopPropagation true if a suitable configurator has been found.
     *
     * @override
     * @private
     */
    _onProductChange: function (productId, dataPointId) {
      var self = this;
      return this._super.apply(this, arguments).then(function (stopPropagation) {
          if (stopPropagation || productId === undefined) {
              return Promise.resolve(true);
          } else {
              return self._checkForEvent(productId, dataPointId);
          }
      });
    },

    /**
     * This method will check if the productId needs configuration or not:
     *
     * @param {integer} productId
     * @param {string} dataPointID
     * @returns {Promise<Boolean>} stopPropagation true if the product is an event ticket.
     *
     * @private
     */
    _checkForEvent: function (productId, dataPointId) {
        var self = this;
        return this._rpc({
            model: 'product.product',
            method: 'read',
            args: [productId, ['event_ok']],
        }).then(function (result) {
            if (Array.isArray(result) && result.length && result[0].event_ok) {
                self._openEventConfigurator({
                        default_product_id: productId
                    },
                    dataPointId
                );
                return Promise.resolve(true);
            }
            return Promise.resolve(false);
        });
    },

    /**
     * Opens the event configurator in 'edit' mode.
     *
     * @override
     * @private
     */
    _onEditLineConfiguration: function () {
        if (this.recordData.event_ok) {
            var defaultValues = {
                default_product_id: this.recordData.product_id.data.id
            };

            if (this.recordData.event_id) {
                defaultValues.default_event_id = this.recordData.event_id.data.id;
            }

            if (this.recordData.event_ticket_id) {
                defaultValues.default_event_ticket_id = this.recordData.event_ticket_id.data.id;
            }

            this._openEventConfigurator(defaultValues, this.dataPointID);
        } else {
            this._super.apply(this, arguments);
        }
    },

    /**
     * Opens the event configurator to allow configuring the SO line with events information.
     *
     * When the window is closed, configured values are used to trigger a 'field_changed'
     * event to modify the current SO line.
     *
     * If the window is closed without providing the required values 'event_id' and
     * 'event_ticket_id', the product_id field is cleaned.
     *
     * @param {Object} data various "default_" values
     * @param {string} dataPointId
     *
     * @private
     */
    _openEventConfigurator: function (data, dataPointId) {
        var self = this;
        this.do_action('event_sale.event_configurator_action', {
            additional_context: data,
            on_close: function (result) {
                if (result && !result.special) {
                    self.trigger_up('field_changed', {
                        dataPointID: dataPointId,
                        changes: result.eventConfiguration,
                        onSuccess: function () {
                            // Call post-init function.
                            self._onLineConfigured();
                        }
                    });
                } else {
                    if (!self.recordData.event_id || !self.recordData.event_ticket_id) {
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
    }
});


return ProductConfiguratorWidget;

});
