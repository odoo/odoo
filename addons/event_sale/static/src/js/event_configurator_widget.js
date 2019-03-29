odoo.define('event.configurator', function (require) {

var relationalFields = require('web.relational_fields');
var FieldsRegistry = require('web.field_registry');
var EventConfiguratorWidgetMixin = require('event_sale.EventConfiguratorWidgetMixin');

/**
 * The event configurator widget is a simple FieldMany2One that adds the capability
 * to configure a product_id with event information using the event configurator wizard.
 *
 * The event information include:
 * - event_id
 * - event_ticket_id
 *
 * !!! It should only be used on a product_id field !!!
 */
var EventConfiguratorWidget = relationalFields.FieldMany2One.extend(EventConfiguratorWidgetMixin, {
    events: _.extend({},
        relationalFields.FieldMany2One.prototype.events,
        EventConfiguratorWidgetMixin.events
    ),

    /**
     * @see _addEventConfigurationEditButton for more info
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._addEventConfigurationEditButton();
        });
    },

    /**
     * This method is overridden to check if the product_id needs configuration or not:
     *
     * @override
     * @param {OdooEvent} event
     *
     * @private
     */
    _onFieldChanged: function (event) {
        var self = this;

        this._super.apply(this, arguments);
        if (!event.data.changes.product_id){
            return;
        }

        var productId = event.data.changes.product_id.id;
        self._checkForEvent(productId, event.data.dataPointID);
    }
});

FieldsRegistry.add('event_configurator', EventConfiguratorWidget);

return EventConfiguratorWidget;

});
