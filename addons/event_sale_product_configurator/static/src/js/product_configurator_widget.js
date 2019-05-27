odoo.define('event_sale.event_sale_product_configurator', function (require) {

var relationalFields = require('web.relational_fields');
var ProductConfiguratorWidget = require('sale_product_configurator.product_configurator');
var EventConfiguratorWidgetMixin = require('event_sale.EventConfiguratorWidgetMixin');

/**
 * The ProductConfiguratorWidget is overridden to add the features of the EventConfiguratorWidget.
 */
var productConfiguratorEvents = ProductConfiguratorWidget.prototype.events;
ProductConfiguratorWidget.include(EventConfiguratorWidgetMixin);

ProductConfiguratorWidget.include({
    events: _.extend({},
        relationalFields.FieldMany2One.prototype.events,
        productConfiguratorEvents,
        EventConfiguratorWidgetMixin.events
    ),

    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._addEventConfigurationEditButton();
        });
    },

    /**
     * @param {integer} productId
     * @param {string} dataPointID
     *
     * @private
     */
    _onSimpleProductFound: function (productId, dataPointID) {
        this._checkForEvent(productId, dataPointID);
    }
});

return ProductConfiguratorWidget;

});
