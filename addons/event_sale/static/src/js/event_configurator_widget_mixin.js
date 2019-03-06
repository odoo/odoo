odoo.define('event_sale.EventConfiguratorWidgetMixin', function (require) {
'use strict';

var core = require('web.core');
var _t = core._t;

/**
 * This mixin intends to gather methods that will be used by the event configurator.
 * They're extracted here to be used by other widgets if necessary (namely the product_configurator_widget)
 */
var EventConfiguratorWidgetMixin = {
    events: {
        'click .o_event_sale_js_event_configurator_edit': '_onEditEventConfiguration'
    },
    /**
     * This method will check if the current product set on the SO line is a configurable event.
     * -> If so, we add a 'Edit Configuration' button next to the dropdown.
     *
     */
    _addEventConfigurationEditButton: function () {
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
    },

    /**
     * This method will check if the productId needs configuration or not:
     *
     * @param {integer} productId
     * @param {string} dataPointID
     */
    _checkForEvent: function (productId, dataPointID) {
        var self = this;
        if (productId){
            this._rpc({
                model: 'product.product',
                method: 'read',
                args: [productId, ['event_ok']],
            }).then(function (result) {
                if (result && result[0].event_ok){
                    self._openEventConfigurator({
                            default_product_id: productId
                        },
                        dataPointID
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
};

return EventConfiguratorWidgetMixin;

});
