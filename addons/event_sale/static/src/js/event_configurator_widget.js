odoo.define('event.configurator', function (require) {

var relationalFields = require('web.relational_fields');
var FieldsRegistry = require('web.field_registry');
var core = require('web.core');
var _t = core._t;

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
var EventConfiguratorWidget = relationalFields.FieldMany2One.extend({
    events: _.extend({}, relationalFields.FieldMany2One.prototype.events, {
        'click .o_event_sale_js_event_configurator_edit': '_onEditEventConfiguration'
    }),

    /**
     * This method will check if the current product set on the SO line is a configurable event.
     * -> If so, we add a 'Edit Configuration' button next to the dropdown.
     *
     * @override
     */
    start: function () {
        var prom = this._super.apply(this, arguments);

        var $inputDropdown = this.$('.o_input_dropdown');

        if (this.recordData.event_ok &&
            $inputDropdown.length !== 0 &&
            this.$('.o_event_sale_js_event_configurator_edit').length === 0) {
            var $editConfigurationButton = $('<button>', {
                type: 'button',
                class: 'fa fa-pencil btn btn-secondary o_event_sale_js_event_configurator_edit',
                tabindex: '-1',
                draggable: false,
                'aria-label': _t('Edit Configuration'),
                title: _t('Edit Configuration')
            });

            $inputDropdown.after($editConfigurationButton);
        }

        return prom;
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

        var product_id = event.data.changes.product_id.id;
        if (product_id){
            this._rpc({
                model: 'product.product',
                method: 'read',
                args: [product_id, ['event_ok']],
            }).then(function (result) {
                if (result && result[0].event_ok){
                    self._openEventConfigurator({
                        default_product_id: product_id
                    },
                    event.data.dataPointID
                );
                }
            });
        }
    },

    /**
     * Opens the event configurator in 'edit' mode.
     *
     * @private
     */
    _onEditEventConfiguration: function () {
        var defaultValues = {
            default_product_id: this.recordData.product_id.data.id
        };

        if (this.recordData.event_id) {
            defaultValues['default_event_id'] = this.recordData.event_id.data.id;
        }

        if (this.recordData.event_ticket_id) {
            defaultValues['default_event_ticket_id'] = this.recordData.event_ticket_id.data.id;
        }

        this._openEventConfigurator(defaultValues, this.dataPointID);
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
                if (result && result !== 'special'){
                    self.trigger_up('field_changed', {
                        dataPointID: dataPointId,
                        changes: result.eventConfiguration
                    });
                } else {
                    if (!self.recordData.event_id || !self.recordData.event_ticket_id) {
                        self.trigger_up('field_changed', {
                            dataPointID: dataPointId,
                            changes: {product_id: {operation: 'DELETE_ALL'}}
                        });
                    }
                }
            }
        });
    }
});

FieldsRegistry.add('event_configurator', EventConfiguratorWidget);

return EventConfiguratorWidget;

});
